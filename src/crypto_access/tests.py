"""
Tests for crypto_access app.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile


class HealthCheckTestCase(TestCase):
    """Test health check endpoints"""
    
    def setUp(self):
        self.client = Client()
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get(reverse('crypto_access:health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'healthy')


class UserProfileTestCase(TestCase):
    """Test UserProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_user_profile(self):
        """Test creating a user profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            phone='1234567890',
            bio='Test bio'
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.phone, '1234567890')
        self.assertIsNotNone(profile.created_at)
    
    def test_user_profile_str(self):
        """Test string representation of user profile"""
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(str(profile), f"{self.user.username}'s profile")
