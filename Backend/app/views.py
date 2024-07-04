from django.http import JsonResponse, HttpResponse
from rest_framework.views import APIView
from .serializers import TextToSpeechSerializer
import os
from langdetect import detect
from dotenv import load_dotenv
import base64
from openai import OpenAI
from .models import ChatMessage
from rest_framework.permissions import IsAuthenticated

load_dotenv()


class TextToSpeechView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        serializer = TextToSpeechSerializer(data=request.data)
        if serializer.is_valid():
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            text = serializer.validated_data['text']
            user = request.user

            previous_messages = ChatMessage.objects.filter(user=user).order_by('created_at')
            messages = [{"role": "system",
                         "content": f"You should behave like my personal tutor to help me practice spoken Arabic, learn it effectively and increase my vocabulary. You should engage in a constructive dialog to help me master the Arabic language. Your answers should be as realistic as possible and not too long (1 sentence maximum). You also help me to have a conversation in Arabic by explaining words in English."}]
            for msg in previous_messages:
                messages.append({"role": "user", "content": msg.message})
                messages.append({"role": "assistant", "content": msg.response})

            messages.append({"role": "user", "content": text})

            print(messages)

            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
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
