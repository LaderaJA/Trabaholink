from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('search/users/', views.search_users, name='search_users'),
    path('search/jobs/', views.search_jobs, name='search_jobs'),
]
