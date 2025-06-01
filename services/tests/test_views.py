from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from services.models import ServicePost, ServiceImage

class ServicePostCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.create_url = reverse('services:create_post')

    def test_create_service_post_with_images(self):
        # Create a service post
        post_data = {
            'title': 'Test Service',
            'description': 'Test description',
            'price': 100,
            'location': 'Test location',
        }

        # Simulate image upload
        image_data = {
            'serviceimage_set-0-image': open('path/to/test_image.jpg', 'rb'),
            'serviceimage_set-TOTAL_FORMS': 1,
            'serviceimage_set-INITIAL_FORMS': 0,
        }

        response = self.client.post(self.create_url, {**post_data, **image_data})

        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        self.assertTrue(ServicePost.objects.filter(title='Test Service').exists())
        self.assertTrue(ServiceImage.objects.filter(post__title='Test Service').exists())

    def test_create_service_post_invalid_image(self):
        # Create a service post with invalid image
        post_data = {
            'title': 'Test Service',
            'description': 'Test description',
            'price': 100,
            'location': 'Test location',
        }

        image_data = {
            'serviceimage_set-0-image': 'invalid_image_data',
            'serviceimage_set-TOTAL_FORMS': 1,
            'serviceimage_set-INITIAL_FORMS': 0,
        }

        response = self.client.post(self.create_url, {**post_data, **image_data})

        self.assertEqual(response.status_code, 200)  # Stay on the same page due to validation error
        self.assertFalse(ServicePost.objects.filter(title='Test Service').exists())