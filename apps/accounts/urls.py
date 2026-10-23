from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LogoutView, RegisterView, TokenObtainPairView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]
