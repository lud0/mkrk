import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from main.fetchers import NewsAPIScraper, NewsNLUAnalyzer
from main.models import Article, Target

log = logging.getLogger(__name__)

news_scraper = NewsAPIScraper()
news_analyzer = NewsNLUAnalyzer()


@shared_task
def scrape_and_analyze_news_task():
    """
    Loop over all the target keywords that need to be refreshed and submit the scraping task
    """
    now = timezone.now()
    expired_targets = Target.objects.filter(Q(expired_at__isnull=True) | Q(expired_at__lte=now))
    log.debug("start scrape and analyze task for %d expired keywords" % len(expired_targets))

    for target in expired_targets:
        # submit the target keyword for scraping
        scrape_latest_news_task.delay(keyword=target.keyword)

        # set the new expiration time
        target.expired_at = now + timedelta(hours=target.refresh_frequency)
        target.save()


@shared_task
def scrape_latest_news_task(keyword):
    """
    Scrape for the latest articles containing the given keyword and submit the sentiment analysis task for each article
    """
    log.debug("start scraping news for target kw %s" % keyword)

    new_articles_uids = news_scraper.fetch_and_store(query=keyword)
    log.debug("scraped %s articles" % len(new_articles_uids))

    for uid in new_articles_uids:
        analyze_news_task.delay(uid, keyword)


@shared_task
def scrape_historic_news_task(keyword):
    """
    Scrape for articles containing the given keyword in the last 30 days
    and submit the sentiment analysis task for each article
    """
    log.debug("start scraping news for target kw %s" % keyword)

    upto_date = datetime.now() + timedelta(days=-30)
    new_articles_uids = news_scraper.fetch_and_store(query=keyword, upto_date=upto_date)
    log.debug("scraped %s articles" % len(new_articles_uids))

    for uid in new_articles_uids:
        analyze_news_task.delay(uid, keyword)


@shared_task
def analyze_news_task(article_uid, keyword):
    """
    Do the sentiment analysis on the given article for the given keyword
    """
    log.debug("start analyzing %s with kw %s" % (article_uid, keyword))

    try:
        article = Article.objects.get(uid=article_uid)
    except Article.DoesNotExist:
        return
    else:
        news_analyzer.process_and_store(article, query=keyword)
