from __future__ import annotations

from typing import Any

from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import (
    TokenBlacklistView as SimpleJWTTokenBlacklistView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView as SimpleJWTTokenObtainPairView,
)

from .serializers import RegisterSerializer, UserProfileSerializer
from .throttling import AuthRateThrottle


class RegisterView(generics.CreateAPIView):
    """View to handle new user registration."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    throttle_classes = [AuthRateThrottle]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Validate input and register user account."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "User registered successfully."},
            status=status.HTTP_201_CREATED,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """View to retrieve and update the authenticated user's profile."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self) -> Any:
        """Return the currently authenticated user."""
        return self.request.user


class TokenObtainPairView(SimpleJWTTokenObtainPairView):
    """View to obtain JWT token pair with throttling applied."""

    throttle_classes = [AuthRateThrottle]


class LogoutView(SimpleJWTTokenBlacklistView):
    """View to blacklist refresh token on logout with throttling applied."""

    throttle_classes = [AuthRateThrottle]
