import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
class TestCustomUserModel:
    def test_auth_user_model_setting(self):
        assert settings.AUTH_USER_MODEL == "accounts.User"
        assert User._meta.label == "accounts.User"

    def test_create_user_successful(self):
        user = User.objects.create_user(email="test@example.com", password="securepassword123")
        assert user.email == "test@example.com"
        assert user.check_password("securepassword123")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert str(user) == "test@example.com"
        assert not hasattr(user, "username") or user.username is None

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(email="User@EXAMPLE.COM", password="securepassword123")
        assert user.email == "user@example.com"

    def test_create_user_stores_email_lowercased(self):
        user = User.objects.create_user(email="Anna@Test.COM", password="securepassword123")
        assert user.email == "anna@test.com"

    def test_user_save_lowercases_email(self):
        user = User(email="MixedCase@Example.COM")
        user.save()
        assert user.email == "mixedcase@example.com"

    def test_get_by_natural_key_case_insensitive(self):
        User.objects.create_user(email="anna@test.com", password="securepassword123")
        found = User.objects.get_by_natural_key("Anna@Test.COM")
        assert found.email == "anna@test.com"

    def test_create_user_without_email_raises_value_error(self):
        with pytest.raises(ValueError, match="The Email field must be set"):
            User.objects.create_user(email="", password="securepassword123")

    def test_user_email_must_be_unique(self):
        User.objects.create_user(email="unique@example.com", password="securepassword123")
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="unique@example.com", password="anotherpassword")

    def test_create_superuser_successful(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="adminpassword123"
        )
        assert admin.email == "admin@example.com"
        assert admin.check_password("adminpassword123")
        assert admin.is_active is True
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_create_superuser_without_is_staff_raises_value_error(self):
        with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
            User.objects.create_superuser(
                email="admin@example.com", password="adminpassword123", is_staff=False
            )

    def test_create_superuser_without_is_superuser_raises_value_error(self):
        with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
            User.objects.create_superuser(
                email="admin@example.com", password="adminpassword123", is_superuser=False
            )

    def test_user_timezone_default_is_kyiv(self):
        user = User.objects.create_user(email="tz@example.com", password="password123")
        assert user.timezone == "Europe/Kyiv"
        assert hasattr(user, "get_today")

    def test_user_invalid_timezone_raises_validation_error(self):
        from django.core.exceptions import ValidationError

        user = User(email="invalidtz@example.com", timezone="Invalid/Timezone")
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_user_kiev_normalized_to_kyiv_on_clean_and_save(self):
        user = User.objects.create_user(
            email="kievuser@example.com", password="password123", timezone="Europe/Kiev"
        )
        assert user.timezone == "Europe/Kyiv"

        user.timezone = "Europe/Kiev"
        user.clean()
        assert user.timezone == "Europe/Kyiv"

        user.timezone = "Europe/Kiev"
        user.save()
        assert user.timezone == "Europe/Kyiv"
        user.refresh_from_db()
        assert user.timezone == "Europe/Kyiv"

    def test_timezone_validation_when_system_tzpath_is_missing(self, monkeypatch, tmp_path):
        import zoneinfo

        empty_dir = str(tmp_path / "empty_tzpath")
        import os

        os.makedirs(empty_dir, exist_ok=True)
        orig_tzpath = zoneinfo.TZPATH
        zoneinfo.reset_tzpath(to=(empty_dir,))
        try:
            # Should still validate successfully using python tzdata
            user = User.objects.create_user(
                email="tzpath@example.com", password="password123", timezone="Europe/Kiev"
            )
            assert user.timezone == "Europe/Kyiv"

            # Should also accept standard IANA zone
            user.timezone = "America/New_York"
            user.clean()
            assert user.timezone == "America/New_York"
        finally:
            zoneinfo.reset_tzpath(to=orig_tzpath)
