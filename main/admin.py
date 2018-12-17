import json

from django.contrib import admin
from django.utils.safestring import mark_safe
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer

from main.models import Article, Target, UserTarget


class ArticleAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'title', 'published_at', 'url', 'created_at']
    readonly_fields = list_display + ['uid', 'snippet', 'sentiment_data_pretty']
    fieldsets = [
        ('Article info', {'fields': ['title', ('source', 'url'), 'snippet', 'published_at']}),
        ('Storage info', {'fields': [('id', 'uid', 'created_at')]}),
        ('Sentiment analysis', {'fields': ['sentiment_data_pretty']}),
        ]
    list_filter = ('source', )
    search_fields = ('uid',)

    def sentiment_data_pretty(self, instance):
        """Function to display pretty version of the sentiment data"""

        # Convert the data to sorted, indented JSON
        response = json.dumps(instance.sentiment_data, sort_keys=True, indent=2)
        response = response[:1000]

        # Get the Pygments formatter
        formatter = HtmlFormatter(style='colorful')

        # Highlight the data
        response = highlight(response, JsonLexer(), formatter)

        # Get the stylesheet
        style = "<style>" + formatter.get_style_defs() + "</style><br>"

        # Safe the output
        return mark_safe(style + response)

    sentiment_data_pretty.short_description = 'Sentiment data prettified'


class TargetAdmin(admin.ModelAdmin):
    list_display = ['active', 'keyword', 'refresh_frequency', 'expired_at', 'created_at']
    list_filter = ('active', )


class UserTargetAdmin(admin.ModelAdmin):
    list_display = ['user', 'target_keyword', 'created_at']


admin.site.register(Article, ArticleAdmin)
admin.site.register(Target, TargetAdmin)
admin.site.register(UserTarget, UserTargetAdmin)
