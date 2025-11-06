import httpx
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import ChatMessage

@csrf_exempt
@login_required
def chatbot_response(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User not authenticated'}, status=401)
        try:
            data = json.loads(request.body)
            user_message = data.get('message')

            if not user_message:
                return JsonResponse({'error': 'No message provided'}, status=400)

            # Retrieve past messages for context
            chat_history = ChatMessage.objects.filter(user=request.user).order_by('timestamp')
            messages = [{"role": "system", "content": "You are a helpful assistant for vehicle breakdown assistance."}]
            for chat in chat_history:
                messages.append({"role": "user", "content": chat.message})
                messages.append({"role": "assistant", "content": chat.response})
            
            messages.append({"role": "user", "content": user_message})

            # OpenRouter API configuration
            OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
            OPENROUTER_MODEL = settings.CHATBOT_MODEL # Use model from settings
            OPENROUTER_API_BASE = "https://openrouter.ai/api/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "temperature": 0.7, # Add temperature for more creative responses
                "max_tokens": 500 # Limit response length
            }

            with httpx.Client() as client:
                response = client.post(OPENROUTER_API_BASE, headers=headers, json=payload)
                response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
                ai_response = response.json()["choices"][0]["message"]["content"]

            ChatMessage.objects.create(
                user=request.user,
                message=user_message,
                response=ai_response
            )

            return JsonResponse({'response': ai_response})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except httpx.HTTPStatusError as e:
            return JsonResponse({'error': f"HTTP error: {e.response.status_code} - {e.response.text}"}, status=500)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)
