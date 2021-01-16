from django.conf import settings

from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator


def get_sentiment(url):
    authenticator = IAMAuthenticator(settings.IBM_API_KEY)
    natural_language_understanding = NaturalLanguageUnderstandingV1(
        version=settings.IBM_VERSION,
        authenticator=authenticator
    )
    natural_language_understanding.set_service_url(settings.IBM_SERVICE_URL)
    response = natural_language_understanding.analyze(
        url=url,
        features={
            "sentiment": {},
        },
    ).get_result()['sentiment']['document']

    return response['score'], response['label']
