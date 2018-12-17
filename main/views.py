from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from main.models import Article
from main.utils import resample_timeseries


def login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('news'))
        else:
            message = 'Invalid login'
    elif request.user.is_authenticated:
        return HttpResponseRedirect(reverse('news'))
    else:
        message = ''
    return render(request, 'login.html', {'message': message})


def logout_page(request):
    logout(request)
    return HttpResponseRedirect(reverse('login'))


@login_required(login_url='login')
def news_page(request):

    user_keywords = list(request.user.my_targets.all().values_list('target_keyword__keyword', flat=True))
    user_articles = Article.objects.filter(sentiment_data__reports__0__target_keyword__in=user_keywords)[:100]
    stats = Article.get_score_averages(user_articles)

    return render(request, 'news.html', {'articles': user_articles, 'stats': stats})


@login_required(login_url='login')
def trends_page(request):
    user_keywords = list(request.user.my_targets.all().values_list('target_keyword__keyword', flat=True))
    user_articles = Article.objects.filter(sentiment_data__reports__0__target_keyword__in=user_keywords)[:100]
    kw_score_timeseries = Article.get_score_data(user_articles)

    trends = {}
    for kw, score_timeseries in kw_score_timeseries.items():
        trends[kw] = resample_timeseries(score_timeseries)
    return render(request, 'trends.html', {'trends': trends})


@login_required(login_url='login')
def settings_page(request):

    return render(request, 'settings.html')

