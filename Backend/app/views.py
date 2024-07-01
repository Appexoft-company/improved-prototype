from django.http import JsonResponse, HttpResponse
from rest_framework.views import APIView
from .serializers import TextToSpeechSerializer
import os
from langdetect import detect
from dotenv import load_dotenv
import base64
from openai import OpenAI
load_dotenv()

class TextToSpeechView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = TextToSpeechSerializer(data=request.data)
        if serializer.is_valid():
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            text = serializer.validated_data['text']

            language = detect(text)
            language_goal = "English" if language in ['en'] else "Arabic" if language in [
                'ar'] else "English"

            if language_goal == "English":
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo-0125",
                    messages=[
                        {"role": "system",
                         "content": f"You are my Arabic teacher, I am here to improve my spoken arabic skills, answer in {language_goal} language. Answer like a real person, without long answers, only 1 sentence"},
                        {"role": "user", "content": text}
                    ]
                )
            else:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo-0125",
                    messages=[
                        {"role": "system",
                         "content": f"You are my English teacher, I am here to improve my spoken english skills, combine and answer in 2 languages: {language_goal} and English. Answer like a real person, without long answers, only 1 sentence"},
                        {"role": "user", "content": text}
                    ]
                )

            chat_response_text = response.choices[0].message.content

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
