from django.contrib import admin
from apps.accounts.models import User
from apps.accounts.admin import UserAdmin


def test_user_admin_is_registered():
    assert isinstance(admin.site._registry[User], UserAdmin)
    assert UserAdmin.ordering == ('email',)
