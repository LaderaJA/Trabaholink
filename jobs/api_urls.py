from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    JobViewSet, JobApplicationViewSet, JobOfferViewSet,
    ContractViewSet, ProgressLogViewSet, DashboardViewSet,
    JobCategoryViewSet, JobProgressViewSet, FeedbackViewSet,
    schedule_events_api
)

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'applications', JobApplicationViewSet, basename='application')
router.register(r'offers', JobOfferViewSet, basename='offer')
router.register(r'contracts', ContractViewSet, basename='contract')
router.register(r'progress-logs', ProgressLogViewSet, basename='progresslog')
router.register(r'progress-updates', JobProgressViewSet, basename='progress')
router.register(r'feedback', FeedbackViewSet, basename='feedback')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'categories', JobCategoryViewSet, basename='category')

app_name = 'jobs_api'

urlpatterns = [
    path('', include(router.urls)),
    path('schedule/events/', schedule_events_api, name='schedule_events'),
]
