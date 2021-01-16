import random
import re
import requests
import time

from datetime import datetime, timezone

import timeago

from bs4 import BeautifulSoup
from celery import group
from celery.exceptions import MaxRetriesExceededError
from celery.result import allow_join_result
from celery.utils.log import get_task_logger
from django.db import IntegrityError
from django.conf import settings
from django.core.cache import cache
from ibm_cloud_sdk_core.api_exception import ApiException

from hackernews_clone.celery import app
from hackernews_clone.posts.models import Post
from hackernews_clone.posts.utils import get_sentiment

logger = get_task_logger(__name__)


@app.task(
    bind=True,
    queue='create_or_update_post_queue',
    max_retries=2,
)
def create_or_update_post(self, post_id, url, subject, rank,
                          age, score, submitted_by, num_of_comments):
    try:
        post = Post.objects.get(id=post_id)
        post.rank = rank
        post.age = age
        post.score = score
        post.num_of_comments = num_of_comments
        post.save(update_fields=['rank', 'age', 'score', 'num_of_comments'])
        logger.info(f'Updated post: {post_id}')
    except Post.DoesNotExist:
        logger.info(f'Getting sentiment for {url}')
        try:
            sentiment_score, sentiment_label = get_sentiment(url)
        except ApiException as exc:
            try:
                logger.info(f'Retrying getting sentiment for {url}')
                self.retry(countdown=int(random.uniform(2, 4) ** self.request.retries))
            except MaxRetriesExceededError:
                sentiment_score = None
                sentiment_label = exc.message

        try:
            post = Post.objects.create(
                id=post_id,
                url=url,
                subject=subject,
                submitted_by=submitted_by,
                rank=rank,
                score=score,
                age=age,
                num_of_comments=num_of_comments,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
            )
            logger.info(f'Created post: {post_id}')
        except IntegrityError:
            # Edge case; in case a hackernews post grabbed by create_or_update_post worker
            # and change its page before creation of its model instance and regrabbed by
            # another create_or_update_post worker
            pass


@app.task(queue='api_post_queue')
def fetch_post_from_api(post_id, rank):
    post = requests.get(f'{settings.HACKERNEWS_API_URL}item/{post_id}.json').json()
    post_task_result = create_or_update_post.delay(
        post.get('id'),
        post.get('url', f'{settings.HACKERNEWS_URL}item?id={post_id}'),
        post.get('title'),
        rank,
        timeago.format(datetime.fromtimestamp(post.get('time')), datetime.now()),
        post.get('score'),
        post.get('by'),
        len(post.get('kids', [])),
    )
    return post_task_result


@app.task(queue='main_queue', ignore_results=True)
def fetch_from_api():
    cache.set('running', 1, None)
    cache.set('fetch_api_last_start_time', datetime.now(tz=timezone.utc), None)
    logger.info('Fetching from api')
    try:
        post_ids = requests.get(f'{settings.HACKERNEWS_API_URL}topstories.json').json()
    except requests.exceptions.ConnectionError as e:
        cache.set('running', 0, None)
        cache.set('fetch_api_last_finish_time', 'Failed', None)
        raise e
    result = group(
        fetch_post_from_api.s(post_id, rank) for rank, post_id in enumerate(post_ids, 1)
    )()

    with allow_join_result():
        while not all([task_result.ready() for task_result in result.get()]):
            time.sleep(5)
            logger.info('Waiting all tasks to finish')

    logger.info(f'Number of posts processed: {len(post_ids)}')
    Post.objects.exclude(id__in=post_ids).delete()
    cache.set('running', 0, None)
    cache.set('fetch_api_last_finish_time', datetime.now(tz=timezone.utc), None)


@app.task(queue='main_queue', ignore_result=True)
def scrap_from_web():
    cache.set('running', 1, None)
    cache.set('scrapper_last_start_time', datetime.now(tz=timezone.utc), None)
    next_page_exists = True
    is_all_posts_processed = False
    post_ids_set = set()
    page_index = 1
    page_end = page_index + settings.MAX_PAGE_TO_SCRAP_IN_PARALEL
    post_results = []
    while next_page_exists:
        result = group(page_scrapper.s(i) for i in range(page_index, page_end))()
        with allow_join_result():
            for result, post_ids in result.get():
                post_results.append(result)
                if len(post_ids) == 0:
                    next_page_exists = False
                else:
                    post_ids_set = post_ids_set.union(post_ids)
        page_index, page_end = page_end, page_end + settings.MAX_PAGE_TO_SCRAP_IN_PARALEL

    while not is_all_posts_processed:
        is_all_posts_processed = all([result.ready() for result in post_results])

    logger.info(f'Number of posts processed: {len(post_ids_set)}')
    Post.objects.exclude(id__in=list(post_ids_set)).delete()
    cache.set('running', 0, None)
    cache.set('scrapper_last_finish_time', datetime.now(tz=timezone.utc), None)


@app.task(queue='page_scrapper_queue')
def page_scrapper(page_number):
    def row_parser(row):
        score = None
        submitted_by = None
        num_of_comments = None
        post_id = row['id']
        rank = row.find(class_='rank').string[:-1]
        story_link = row.find(class_='storylink')
        url = story_link['href']
        url = url if url.startswith('http') else f'{settings.HACKERNEWS_URL}{url}'
        subject = story_link.string
        footer = row.next_sibling
        age = footer.select_one('.age > a').string
        score_el = footer.find(class_='score')
        # If score exists, parse score, submitted_by, num_of_comments
        if score_el:
            score = int(score_el.string.replace(' points', ''))
            footer_els = footer.select('.subtext > a')
            submitted_by = footer_els[0].string
            res = re.match(r'(\d+)\xa0comment', footer_els[2].string)
            if res:
                num_of_comments = int(res[1])

        return (post_id, url, subject, rank, age, score, submitted_by, num_of_comments)

    logger.info(f'Scrapping page {page_number}')
    try:
        response = requests.get(f'{settings.HACKERNEWS_URL}news?p={page_number}')
    except requests.exceptions.ConnectionError as e:
        cache.set('running', 0, None)
        cache.set('scrapper_last_finish_time', 'Failed', None)
        raise e

    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.find_all('tr', class_='athing')
    post_ids = []
    posts = []
    for row in rows:
        post = row_parser(row)
        post_ids.append(post[0])
        posts.append(post)

    result = group(create_or_update_post.s(*post) for post in posts)()
    return (result, post_ids)
