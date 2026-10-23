from django.contrib import admin

from apps.accounts.admin import UserAdmin
from apps.accounts.models import User


def test_user_admin_is_registered():
    assert isinstance(admin.site._registry[User], UserAdmin)
    assert UserAdmin.ordering == ("email",)
