import re

from bs4 import BeautifulSoup
from django.conf import settings
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator


def scrap_posts(content):
    posts = []
    soup = BeautifulSoup(content, "html.parser")
    rows = soup.find_all("tr", class_="athing")
    for row in rows:
        post_id = row["id"]
        rank = row.find(class_="rank").string[:-1]
        url = row.find(class_="storylink").get("href")
        url = (
            url
            if url.startswith("http")
            else f"{settings.HACKERNEWS_URL}{url}"
        )
        subject = row.find(class_="storylink").string

        footer = row.next_sibling
        age = footer.select_one(".age > a").string

        score, submitted_by, num_of_comments = None, None, None
        score_el = footer.find(class_="score")
        # If score element exists, parse score and submitted_by
        if score_el:
            score = int(score_el.string.replace(" points", ""))
            footer_els = footer.select(".subtext > a")
            submitted_by = footer_els[0].string
            # Check if comments exist, and parse it
            res = re.match(r"(\d+)\xa0comment", footer_els[2].string)
            if res:
                num_of_comments = int(res[1])

        posts.append({
            "id": post_id,
            "rank": rank,
            "url": url,
            "subject": subject,
            "age": age,
            "score": score,
            "submitted_by": submitted_by,
            "num_of_comments": num_of_comments,
        })

    return posts


def get_sentiment(url):
    authenticator = IAMAuthenticator(settings.IBM_API_KEY)
    natural_language_understanding = NaturalLanguageUnderstandingV1(
        version=settings.IBM_VERSION, authenticator=authenticator
    )
    natural_language_understanding.set_service_url(settings.IBM_SERVICE_URL)
    response = natural_language_understanding.analyze(
        url=url,
        features={
            "sentiment": {},
        },
    ).get_result()["sentiment"]["document"]

    return response["score"], response["label"]
