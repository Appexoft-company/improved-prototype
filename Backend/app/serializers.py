from rest_framework import serializers

from app.models import ChatMessage


class TextToSpeechSerializer(serializers.Serializer):
    text = serializers.CharField()
    difficulty = serializers.CharField(required=False, allow_blank=True)


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'user', 'message', 'response', 'created_at']