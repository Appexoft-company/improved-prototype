from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from user.models import User
from user.serializers import UserSerializer, UserDifficultySerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


class UserDifficultyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = UserDifficultySerializer(user)
        return Response(serializer.data)