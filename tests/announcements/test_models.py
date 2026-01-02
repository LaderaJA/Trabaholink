"""Unit tests for announcements app"""
import pytest
from announcements.models import Announcement

pytestmark = pytest.mark.django_db


class TestAnnouncementModel:
    def test_create_announcement(self, create_user):
        announcement = Announcement.objects.create(
            title='Test Announcement',
            description='Short description',
            content='This is a test announcement',
            posted_by=create_user
        )
        assert announcement.title == 'Test Announcement'
        assert announcement.content == 'This is a test announcement'
        assert str(announcement) == 'Test Announcement'
