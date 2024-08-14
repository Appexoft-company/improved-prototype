from django.http import JsonResponse, HttpResponse
from .serializers import TextToSpeechSerializer, ChatMessageSerializer
import os
from dotenv import load_dotenv
import base64
from openai import OpenAI
from .models import ChatMessage
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .utils import get_message_with_according_difficulty

load_dotenv()


class TextToSpeechView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = TextToSpeechSerializer(data=request.data)
        if serializer.is_valid():
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            text = serializer.validated_data['text']
            difficulty = serializer.validated_data.get('difficulty', '')
            user = request.user

            if difficulty:
                user.difficulty = difficulty
                user.save()

            else:
                difficulty = user.difficulty

            message = get_message_with_according_difficulty(difficulty)

            previous_messages = ChatMessage.objects.filter(user=user).order_by('created_at')
            messages = [{"role": "system",
                         "content": message}]
            for msg in previous_messages:
                messages.append({"role": "user", "content": msg.message})
                messages.append({"role": "assistant", "content": msg.response})

            messages.append({"role": "user", "content": text})

            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )

            chat_response_text = response.choices[0].message.content
            ChatMessage.objects.create(user=user, message=text, response=chat_response_text)

            audio_buffer = bytearray()
            with client.audio.speech.with_streaming_response.create(
                    model="tts-1",
                    voice="alloy",
                    response_format="mp3",
                    input=chat_response_text
            ) as response:
                for chunk in response.iter_bytes(chunk_size=1024):
                    audio_buffer.extend(chunk)

            base64_audio = base64.b64encode(bytes(audio_buffer))
            base64_string = base64_audio.decode('utf-8')

            return JsonResponse({
                "text_response": chat_response_text,
                "audio_base64": base64_string
            })

        return HttpResponse("Invalid data", status=400)



class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        chat_history = ChatMessage.objects.filter(user=user).order_by('created_at')
        serializer = ChatMessageSerializer(chat_history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeleteChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        ChatMessage.objects.filter(user=user).delete()
        return Response({"message": "Chat history deleted successfully"}, status=status.HTTP_204_NO_CONTENT)