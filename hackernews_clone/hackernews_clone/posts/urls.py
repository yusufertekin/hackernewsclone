from django.urls import path

from hackernews_clone.posts import views


urlpatterns = [
    path('', views.PostList.as_view()),
    path('get-scrapper-info/', views.get_scrapper_info),
    path('update-using-scrapper/', views.update_using_scrapper),
    path('get-fetch-api-info/', views.get_fetch_api_info),
    path('update-using-api/', views.update_using_api),
]
