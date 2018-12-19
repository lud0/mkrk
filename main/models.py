import hashlib

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver


class Article(models.Model):
    url = models.URLField(max_length=1024)
    title = models.CharField(max_length=1024)
    snippet = models.TextField(null=True)
    source = models.CharField(max_length=1024)
    published_at = models.DateTimeField()

    uid = models.CharField(max_length=256, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    """
    sentiment_data structure:
    { 'reports': [{
                  'created_at': 2018-12-15T14:45:55.448043,  # ISO-8601 UTC
                  'target_keyword': 'Google',
                  'target_keyword_score': 0.35,
                  'global_score': 0.67,
                  'article_keywords_scores': [('keyword1', 0.45),
                                              ('keyword2', 0.23)..]
                  },
                  ...
                 ]
    }
    """
    sentiment_data = JSONField(null=True)

    class Meta:
        ordering = ('-published_at',)

    def __str__(self):
        return 'ART%d:%s' % (self.id, self.uid)

    def __init__(self, *args, **kwargs):
        """
        Ensures that the article has the UID set.
        The UID is an hash of the url+title+published_at so it is easy
        to prevent duplicates
        """
        super(Article, self).__init__(*args, **kwargs)
        if not self.uid:
            signature = str(self.url) + str(self.title) + str(self.published_at)
            self.uid = hashlib.sha256(signature.encode('utf-8')).hexdigest()

    @property
    def sentiment_last_report(self):
        if self.sentiment_data:
            return self.sentiment_data['reports'][0]
        return {}

    @property
    def sentiment_keywords(self):
        kw = []
        if self.sentiment_data:
            for rep in self.sentiment_data['reports']:
                kw.extend(rep.get('article_keywords_scores', []))
        return kw

    @staticmethod
    def get_score_data(queryset):
        """
        Returns a dict of keyword targets and their (date, score) list of
        data points using the first report of the queryset
        """
        scores = queryset.values_list('published_at',
                                      'sentiment_data__reports__0__target_keyword',
                                      'sentiment_data__reports__0__target_keyword_score')

        data = {}
        for pubdate, kw, score in scores:
            if score is None:
                continue
            if kw not in data:
                data[kw] = [(pubdate, score)]
            else:
                data[kw].append((pubdate, score))
        return data

    @classmethod
    def get_score_averages(cls, queryset):
        """
        Returns the (average score, number of data points) for each
        target keyword
        """

        scores = cls.get_score_data(queryset)
        averages = {}
        for kw, values in scores.items():
            averages[kw] = (sum([score for _, score in values]) / len(values),
                            len(values))

        return averages


class Target(models.Model):
    keyword = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    refresh_frequency = models.IntegerField(default=2,
                                            help_text='minimum number of hours '
                                                      'between refreshes')
    expired_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'KW%d:%s' % (self.id, self.keyword)


class UserTarget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='my_targets')
    target_keyword = models.ForeignKey(Target, on_delete=models.CASCADE,
                                       related_name='users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'target_keyword')


@receiver(post_save, sender=Target)
def submit_scraper_for_new_target(sender, instance, created, *args, **kwargs):
    """
    Signal to automatically submit a scrape task for the new keyword and
    fetch the historic articles
    """
    from main.tasks import scrape_historic_news_task

    if created:
        # submit the target keyword for scraping
        scrape_historic_news_task.delay(keyword=instance.keyword)


@receiver(post_delete, sender=UserTarget)
def delete_target_with_no_users(sender, instance, *args, **kwargs):
    """
    Signal to remove a keyword if no users use it
    """
    if instance.target_keyword.users.count() == 0:
        instance.target_keyword.delete()
