from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import TextToSpeechSerializer, ChatMessageSerializer
from .models import ChatMessage
from .utils import get_message_with_according_difficulty
from dotenv import load_dotenv
from openai import OpenAI
from openai import OpenAIError
import httpx
import os
import base64

# Load environment variables
load_dotenv()

# Set OpenAI API key


class TextToSpeechView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = TextToSpeechSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Initialize httpx client without proxy
                http_client = httpx.Client()
                
                # Initialize OpenAI client with custom http client
                client = OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    http_client=http_client
                )
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
                messages = [{"role": "system", "content": message}]
                for msg in previous_messages:
                    messages.append({"role": "user", "content": msg.message})
                    messages.append({"role": "assistant", "content": msg.response})

                messages.append({"role": "user", "content": text})

                # Updated chat completion call
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    max_tokens=250
                )
                chat_response_text = response.choices[0].message.content
                ChatMessage.objects.create(user=user, message=text, response=chat_response_text)

                # Updated speech generation
                speech_response = client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=chat_response_text
                )

                # Convert audio to base64
                base64_audio = base64.b64encode(speech_response.content).decode('utf-8')

                return JsonResponse({
                    "text_response": chat_response_text,
                    "audio_base64": base64_audio
                })
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
            finally:
                if 'http_client' in locals():
                    http_client.close()

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


class TextToSpeechViewImproved(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = TextToSpeechSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Initialize httpx client without proxy
                http_client = httpx.Client()
                
                # Initialize OpenAI client with custom http client
                client = OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    http_client=http_client
                )
                text = serializer.validated_data['text']
                difficulty = serializer.validated_data.get('difficulty', '')
                user = request.user

                if difficulty:
                    user.difficulty = difficulty
                    user.save()
                else:
                    difficulty = user.difficulty

                message = get_message_with_according_difficulty(difficulty)

                # Create messages array with system message first
                messages = [
                    {"role": "system", "content": message},
                    {"role": "user", "content": text}
                ]

                # Updated chat completion call
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    max_tokens=250,
                    temperature=0.7  # Add some creativity while staying on topic
                )

                def generate():
                    chat_response_text = ""

                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            part = chunk.choices[0].delta.content
                            if part.strip():
                                chat_response_text += part

                                # Generate audio for the chunk
                                speech_response = client.audio.speech.create(
                                    model="tts-1",
                                    voice="alloy",
                                    input=part
                                )

                                # Convert to base64
                                audio_chunk_base64 = base64.b64encode(speech_response.content).decode('utf-8')

                                yield f"data: {{\"text\": \"{part}\", \"audio_base64\": \"{audio_chunk_base64}\"}}\n\n"

                    ChatMessage.objects.create(user=user, message=text, response=chat_response_text)

                return StreamingHttpResponse(generate(), content_type='text/event-stream')
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
            finally:
                if 'http_client' in locals():
                    http_client.close()

        return HttpResponse("Invalid data", status=400)
