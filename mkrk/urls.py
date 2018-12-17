from django.contrib import admin
from django.urls import path
from main import views, api

urlpatterns = [
    # admin
    path('admin/', admin.site.urls),

    # user views
    path('', views.login_page, name='login'),
    path('logout', views.logout_page, name='logout'),
    path('dashboard/news', views.news_page, name='news'),
    path('dashboard/trends', views.trends_page, name='trends'),
    path('dashboard/settings', views.settings_page, name='settings'),

    # AJAX API endpoints
    path('api/v1/usertarget', api.APIUserTarget.as_view(), name='api_usertarget'),
    path('api/v1/article', api.APIArticle.as_view(), name='api_article'),
]
