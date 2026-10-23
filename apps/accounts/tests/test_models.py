import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.conf import settings

User = get_user_model()


@pytest.mark.django_db
class TestCustomUserModel:
    def test_auth_user_model_setting(self):
        assert settings.AUTH_USER_MODEL == 'accounts.User'
        assert User._meta.label == 'accounts.User'

    def test_create_user_successful(self):
        user = User.objects.create_user(email='test@example.com', password='securepassword123')
        assert user.email == 'test@example.com'
        assert user.check_password('securepassword123')
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert str(user) == 'test@example.com'
        assert not hasattr(user, 'username') or user.username is None

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(email='User@EXAMPLE.COM', password='securepassword123')
        assert user.email == 'User@example.com'

    def test_create_user_without_email_raises_value_error(self):
        with pytest.raises(ValueError, match="The Email field must be set"):
            User.objects.create_user(email='', password='securepassword123')

    def test_user_email_must_be_unique(self):
        User.objects.create_user(email='unique@example.com', password='securepassword123')
        with pytest.raises(IntegrityError):
            User.objects.create_user(email='unique@example.com', password='anotherpassword')

    def test_create_superuser_successful(self):
        admin = User.objects.create_superuser(email='admin@example.com', password='adminpassword123')
        assert admin.email == 'admin@example.com'
        assert admin.check_password('adminpassword123')
        assert admin.is_active is True
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_create_superuser_without_is_staff_raises_value_error(self):
        with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
            User.objects.create_superuser(
                email='admin@example.com',
                password='adminpassword123',
                is_staff=False
            )

    def test_create_superuser_without_is_superuser_raises_value_error(self):
        with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
            User.objects.create_superuser(
                email='admin@example.com',
                password='adminpassword123',
                is_superuser=False
            )
