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
                         "content": f"You should act like my personal Arabic tutor to help me practice spoken Arabic, learn it effectively and expand my vocabulary. You should engage in constructive dialog and be a conversation starter (ask questions to keep the conversation going) to help me learn Arabic. Your answers should be as realistic as possible and not too long (NO MORE THAN 2 SENTENCES). You will also help me to carry on a conversation in Arabic, explaining the words in English.If user writing something in ARABIC - explain if the prononsiation is good or not and keep learning me. Structure of your messages must be: small greetings, arabic words with english thansctiptions, question to help with more words to continue conversations in the end"}]
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
