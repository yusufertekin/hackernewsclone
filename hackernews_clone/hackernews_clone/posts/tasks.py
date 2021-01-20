import random
import requests
import time

from datetime import datetime
from typing import Dict, Tuple, List

import timeago

from celery import group
from celery.exceptions import MaxRetriesExceededError
from celery.result import allow_join_result, AsyncResult, GroupResult
from celery.utils.log import get_task_logger
from django.conf import settings
from ibm_cloud_sdk_core.api_exception import ApiException

from hackernews_clone.celery import app
from hackernews_clone.posts.models import Post, ScrapperTracker, APIFetcherTracker
from hackernews_clone.posts.utils import get_sentiment, scrap_posts

logger = get_task_logger(__name__)


@app.task(bind=True, queue="sentiment_queue")
def fetch_sentiment(self, post: Dict) -> None:
    """Checks post with a given id already persisted with sentiment if not, gets sentiment
    for given url and update sentiment_score and sentiment_label of the post with given id.
    """
    post_query = Post.objects.filter(id=post["id"], sentiment_score__isnull=False)
    url = post["url"]
    if not post_query.exists():
        logger.info(f"Getting sentiment for {url}")
        try:
            sentiment_score, sentiment_label = get_sentiment(url)
        except ApiException as exc:
            try:
                logger.info(f"Retrying to get sentiment for {url}")
                # Random jitter added to prevent a Thundering Herd Problem
                self.retry(countdown=int(random.uniform(3, 4) ** self.request.retries))
            except MaxRetriesExceededError:
                sentiment_score = None
                sentiment_label = exc.message

        # Just to get slight better performance use update only sentiment fields instead of
        # directly calling update or create. Almost in all cases post creation should
        # happen before sentiment call is done
        if Post.objects.filter(id=post["id"]).exists():
            Post.objects.filter(id=post["id"]).update(
                sentiment_score=sentiment_score, sentiment_label=sentiment_label
            )
        else:
            Post.objects.update_or_create(
                id=post["id"],
                defaults={
                    "url": post["url"],
                    "subject": post["subject"],
                    "submitted_by": post["submitted_by"],
                    "rank": post["rank"],
                    "score": post["score"],
                    "age": post["age"],
                    "num_of_comments": post["num_of_comments"],
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                },
            )


@app.task(bind=True, queue="persist_queue")
def persist(self, post_info: Dict) -> None:
    """Creates or updates post.
    Edge case race condition: Hackernews post grabbed by persist worker and change its page
    on hackernews and regrabbed by another persist worker.

    Hackernews may contain duplicated posts with different ranks, in this case we only keep
    the latter post.
    """
    post, created = Post.objects.update_or_create(
        id=post_info["id"],
        defaults={
            "url": post_info["url"],
            "subject": post_info["subject"],
            "submitted_by": post_info["submitted_by"],
            "rank": post_info["rank"],
            "score": post_info["score"],
            "age": post_info["age"],
            "num_of_comments": post_info["num_of_comments"],
        },
    )
    if created:
        logger.info(f"Post {post.id} created")
    else:
        logger.info(f"Post {post.id} updated")


@app.task(queue="main_queue", ignore_result=True)
def scrap_from_web() -> None:
    """Orchestrate scrapping hackernews pages.
    Fires MAX_PAGE_TO_SCRAP_IN_PARALEL number of scrap_page tasks in a group,
    waits for group results. Repeats this until hackernews doesn't have any more page to scrap.
    Then waits for all persist tasks fired by scrap_page task to finish.
    """
    ScrapperTracker.activate()
    page_index = 1
    page_end = settings.MAX_PAGE_TO_SCRAP_IN_PARALEL + 1
    post_ids = []
    persist_results = []
    next_page_exists = True
    while next_page_exists:
        pages_result = (
            group(scrap_page.s(page) for page in range(page_index, page_end))
        ).delay()

        try:
            # Although it's not recommended to wait for result in a tasks, we should wait
            # for results of MAX_PAGE_TO_SCRAP_IN_PARALEL number of page;
            # 1. To distinguish whether or not hackernews next page exists to scrap
            # 2. To distinguish whether or not all persist tasks are finished processing
            #    (Release block on UI, record finish time, update periodic task)
            # 3. To collect scrapped post_ids and delete all others from our db
            with allow_join_result():
                pages_result_list = pages_result.get()

            for page_post_ids, persist_result in pages_result_list:
                if page_post_ids == []:
                    next_page_exists = False

                post_ids += page_post_ids
                if persist_result:
                    persist_results.append(persist_result)

            if not next_page_exists:
                is_all_posts_processed = False
                max_retries = 10
                wait_time = 1
                while not is_all_posts_processed:
                    if max_retries >= wait_time:
                        is_all_posts_processed = all(r.ready() for r in persist_results)
                        logger.info(
                            f"Waiting all persist tasks to finish for {wait_time} seconds."
                        )
                        time.sleep(wait_time)
                        wait_time += 1
                    else:
                        ScrapperTracker.fail()
                        raise Exception(
                            "Maximum retry exceeded while waiting all persist tasks to finish."
                            "Backing off."
                        )

                logger.info(f"Number of posts processed: {len(post_ids)}")
                Post.objects.exclude(id__in=list(post_ids)).delete()
                ScrapperTracker.finish()
            else:
                page_index, page_end = (
                    page_end,
                    page_end + settings.MAX_PAGE_TO_SCRAP_IN_PARALEL,
                )
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as err:
            ScrapperTracker.fail()
            raise err


@app.task(queue="scrap_page_queue")
def scrap_page(page_number: int) -> Tuple[List[int], GroupResult]:
    """Makes a request to Hackernews webpage to get the content of the page with given number.
    Parse list of posts on the page content. Fires asynchronous group of tasks to persist
    and fetch sentiment for each post.
    """
    logger.info(f"Scrapping page {page_number}")
    r = requests.get(f"{settings.HACKERNEWS_URL}news?p={page_number}")
    r.raise_for_status()

    post_ids = []
    persist_tasks = []
    sentiment_tasks = []
    for post in scrap_posts(r.content):
        post_ids.append(post["id"])
        persist_tasks.append(persist.s(post))
        sentiment_tasks.append(fetch_sentiment.s(post))

    persist_result = group(persist_tasks).delay() if persist_tasks else None

    if sentiment_tasks:
        group(sentiment_tasks).delay()

    return post_ids, persist_result


@app.task(queue="api_post_queue")
def fetch_post_from_api(post_id: int, rank: int) -> AsyncResult:
    """Makes a request to Hackernews API to get post information. Fires tasks to persist it
    in db, and fetch sentiment for it. This don't traverse all kids to find num of comment. It's
    so heavy operation. However, if we really need to; we can do it by firing async tasks to
    traverse all kids and count number of kids using cache with lock.
    """
    r = requests.get(f"{settings.HACKERNEWS_API_URL}item/{post_id}.json")
    r.raise_for_status()

    post_res = r.json()
    url = post_res.get("url", f"{settings.HACKERNEWS_URL}item?id={post_id}")
    post = {
        "id": post_id,
        "url": url,
        "subject": post_res.get("title"),
        "rank": rank,
        "age": timeago.format(
            datetime.fromtimestamp(post_res.get("time")), datetime.now()
        ),
        "score": post_res.get("score"),
        "submitted_by": post_res.get("by"),
        "num_of_comments": len(post_res.get("kids", [])),
    }

    persist_result = persist.delay(post)
    fetch_sentiment.delay(post)
    return persist_result


@app.task(queue="main_queue", ignore_results=True)
def fetch_from_api() -> None:
    """Makes a request to Hackernews API to get list of post ids of at most 500 top posts.
    Fires group of tasks to fetch information for each post. Collect all persist task
    AsyncResult returned by fetch_post_from_api group of tasks ind wait until all is
    done executing to mark APIFetcherTracker finished.
    """
    APIFetcherTracker.activate()
    logger.info("Fetching from api")
    try:
        post_ids = requests.get(f"{settings.HACKERNEWS_API_URL}topstories.json").json()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
    ) as err:
        APIFetcherTracker.fail()
        raise err

    group_result = group(
        fetch_post_from_api.s(post_id, rank) for rank, post_id in enumerate(post_ids, 1)
    ).delay()

    max_retries = 10
    wait_time = 1
    with allow_join_result():
        while not all([task_result.ready() for task_result in group_result.get()]):
            if max_retries >= wait_time:
                logger.info(
                    "Waiting {wait_time} seconds for all persist tasks to finish"
                )
                time.sleep(wait_time)
                wait_time += 1
            else:
                APIFetcherTracker.fail()
                raise Exception(
                    "Maximum retry exceeded while waiting all persist tasks to finish."
                    "Backing off."
                )

    logger.info(f"Number of posts processed: {len(post_ids)}")
    APIFetcherTracker.finish()
    Post.objects.exclude(id__in=post_ids).delete()
