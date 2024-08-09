from django.urls import path
from .views import TextToSpeechView, ChatHistoryView, DeleteChatHistoryView

urlpatterns = [
    path('text-to-speech/', TextToSpeechView.as_view(), name='text-to-speech'),
    path('chat-history/', ChatHistoryView.as_view(), name='chat-history'),
    path('delete-chat-history/', DeleteChatHistoryView.as_view(), name='delete-chat-history'),
]


app_name = "app"