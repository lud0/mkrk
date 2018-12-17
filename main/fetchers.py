import json
import logging
from datetime import datetime, timedelta

from django.conf import settings
from newsapi import NewsApiClient
from url_normalize import url_normalize
from watson_developer_cloud import NaturalLanguageUnderstandingV1
from watson_developer_cloud import WatsonApiException
from watson_developer_cloud.natural_language_understanding_v1 import Features, SentimentOptions, KeywordsOptions

from main.models import Article

log = logging.getLogger(__name__)


class NewsAPIScraper(object):
    """
    News API scraper class for the service https://newsapi.org/
    Check the documentation at https://newsapi.org/docs for all the parameters available
    """

    def __init__(self):
        self.api_client = NewsApiClient(api_key=settings.NEWSAPIORG_APIKEY)
        self.default_params = (('sources', 'cnn,bbc-news,business-insider,ars-technica,techcrunch'),
                               ('language', 'en'),
                               ('page_size', 100),
                               )

    def fetch_and_store(self, query=None, upto_date=None):
        """
        Method to call to fetch the news article and store them in the db.
        If upto_date is given, then fetch the articles up to that date, otherwise only fetches the latest headlines
        """
        if upto_date:
            raw_articles = self._get_all_news(upto_date, query=query)
        else:
            raw_articles = self._get_headline_news(query=query)

        parsed_articles = self._parse_results(raw_articles)
        return self._store_results(parsed_articles) or []

    def _get_headline_news(self, query=None):
        """
        Fetch the latest headlines news using the default params and the given query
        refer to https://newsapi.org/docs for the available parameters
        """
        params = dict(self.default_params)
        if query:
            params['q'] = query

        try:
            response = self.api_client.get_top_headlines(**params)
        except Exception as e:
            log.error('%s %s' % (e, params))
        else:
            # print(json.dumps(response, indent=2))
            return response

    def _get_all_news(self, upto_date, query=None):
        """
        Fetch the all the articles up to upto_date using the default params and the given query
        refer to https://newsapi.org/docs for the available parameters
        """
        params = dict(self.default_params)
        if query:
            params['q'] = query

        params['from_param'] = upto_date.strftime("%Y-%m-%d")

        try:
            response = self.api_client.get_everything(**params)
        except Exception as e:
            log.error('%s %s' % (e, params))
        else:
            # print(json.dumps(response, indent=2))
            return response

    @staticmethod
    def _parse_results(articles):
        if not articles or articles.get('status', None) != 'ok':
            return

        result = {}
        for entry in articles.get('articles', []):
            url = url_normalize(entry.get('url', None))
            title = entry.get('title', None)
            source = entry.get('source', {'name': None})['name']
            if not url or not title or not source:
                continue
            try:
                published_at = datetime.strptime(entry['publishedAt'][:19], '%Y-%m-%dT%H:%M:%S')
            except Exception as e:
                log.error(e)
                continue
            snippet = entry.get('content', None)

            article = Article(url=url, title=title, snippet=snippet, source=source, published_at=published_at)
            result[article.uid] = article

        return result

    @staticmethod
    def _store_results(parsed_articles):
        if not parsed_articles:
            return

        uids_to_check = parsed_articles.keys()
        uids_existing = Article.objects.filter(uid__in=uids_to_check).values_list('uid', flat=True)
        uids_new = set(uids_to_check) - set(uids_existing)

        new_articles = [parsed_articles[uid] for uid in uids_new]

        if new_articles:
            Article.objects.bulk_create(new_articles)
            # return the new articles uids
            return uids_new


class NewsNLUAnalyzer(object):
    """
    IBM Natural Language Understanding analayzer class
    Check the documentation at https://cloud.ibm.com/apidocs/natural-language-understanding
    for all the features and parameters available
    """

    def __init__(self):
        self.api_client = NaturalLanguageUnderstandingV1(version='2018-03-16',
                                                         url=settings.IBM_NLU_URL,
                                                         iam_apikey=settings.IBM_NLU_APIKEY)

    def process_and_store(self, article, query=None):
        """
        Method to call to process the given article and store the analysis in the db
        """

        response = self._analyze(article, query=query)
        if response:
            self._parse_and_store_response(response, article=article, target_kw=query)

    def _analyze(self, article, query=None):
        if article.url:
            params = {'url': article.url}
        else:
            return

        sentiment_params = {'document': True}
        if query:
            sentiment_params['targets'] = [query]

        params['features'] = Features(keywords=KeywordsOptions(sentiment=True, emotion=False, limit=5),
                                      sentiment=SentimentOptions(**sentiment_params))

        try:
            response = self.api_client.analyze(**params).get_result()
        except WatsonApiException as ex:
            log.error("Method failed with status code " + str(ex.code) + ": " + ex.message)
        except Exception as e:
            log.error(e)
        else:
            print(json.dumps(response, indent=2))
            return response

    @staticmethod
    def _parse_and_store_response(response, article, target_kw):
        """
        Documentation for the response:
        https://cloud.ibm.com/apidocs/natural-language-understanding?language=python#keywords
        Example of a response:
        {
          "usage": {
            "text_units": 1,
            "text_characters": 1188,
            "features": 1
          },
          "sentiment": {
            "targets": [
              {
                "text": "stocks",
                "score": 0.279964,
                "label": "positive"
              }
            ],
            "document": {
              "score": 0.127034,
              "label": "positive"
            }
          },
          "keywords": [
            {
              "text": "curated online courses",
              "sentiment": {
                "score": 0.792454
              },
              "relevance": 0.864624,
            },
            {
              "text": "free virtual server",
              "sentiment": {
                "score": 0.664726
              },
              "relevance": 0.864593,
            }
          "retrieved_url": "https://www.wsj.com/news/markets",
          "language": "en"
        }
        """
        sentiment_data = {}
        try:
            sentiment_data['global_score'] = float(response['sentiment']['document']['score'])
        except KeyError:
            pass
        except Exception as e:
            log.error('%s %s' % (e, response))

        try:
            sentiment_data['target_keyword_score'] = float(response['sentiment']['targets'][0]['score'])
        except KeyError:
            pass
        except Exception as e:
            log.error('%s %s' % (e, response))

        try:
            keyword_scores = []
            for kw in response.get('keywords', []):
                keyword = kw['text']
                score = float(kw['sentiment']['score'])
                keyword_scores += (keyword, score),
        except Exception as e:
            log.error('%s %s' % (e, response))
        else:
            sentiment_data['article_keywords_scores'] = keyword_scores

        if sentiment_data:
            sentiment_data['target_keyword'] = target_kw
            sentiment_data['created_at'] = datetime.utcnow().isoformat()

            if article.sentiment_data:
                # insert in this report in front of any preexisting one to keep the most recent at top
                article.sentiment_data['reports'] = [sentiment_data] + article.sentiment_data['reports']
            else:
                article.sentiment_data = {'reports': [sentiment_data]}

            article.save()
