from rest_framework import generics, permissions, status
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
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "User registered successfully."},
            status=status.HTTP_201_CREATED,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class TokenObtainPairView(SimpleJWTTokenObtainPairView):
    throttle_classes = [AuthRateThrottle]


class LogoutView(SimpleJWTTokenBlacklistView):
    throttle_classes = [AuthRateThrottle]
