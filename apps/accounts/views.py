from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView as SimpleJWTTokenObtainPairView
from .serializers import RegisterSerializer
from .throttling import AuthRateThrottle


class RegisterView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    throttle_classes = [AuthRateThrottle]


class TokenObtainPairView(SimpleJWTTokenObtainPairView):
    throttle_classes = [AuthRateThrottle]

