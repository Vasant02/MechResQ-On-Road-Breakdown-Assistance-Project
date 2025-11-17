import httpx
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import ChatMessage
from core.models import ServiceRequest, Mechanic

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

            # Build structured context from current user / mechanic and recent service requests
            role = "mechanic" if getattr(request.user, "is_mechanic", False) else "user"

            mechanic_obj = None
            if role == "mechanic":
                mechanic_obj = Mechanic.objects.filter(user=request.user).first()

            if role == "mechanic":
                recent_requests = ServiceRequest.objects.filter(mechanic__user=request.user).order_by('-created_at')[:3]
            else:
                recent_requests = ServiceRequest.objects.filter(user=request.user).order_by('-created_at')[:3]

            sr_summaries = []
            for sr in recent_requests:
                sr_summaries.append(
                    f"#{sr.id} | status={sr.status} | vehicle={sr.vehicle_type} | issue={sr.issue_description[:80]}"
                )

            context_lines = [
                f"Current user role: {role}",
                f"Username: {request.user.username}",
                f"Full name: {request.user.get_full_name() or request.user.username}",
            ]

            if role == "mechanic" and mechanic_obj:
                context_lines.append(
                    f"Mechanic details: specialization={mechanic_obj.specialization}, "
                    f"experience_years={mechanic_obj.experience_years}, rating={mechanic_obj.rating}"
                )

            if sr_summaries:
                context_lines.append("Recent related service requests (max 5):")
                context_lines.extend(f"- {line}" for line in sr_summaries)

            domain_system_prompt = (
                "You are 'ResQAssist', the virtual assistant for MechResQ, an on-road vehicle breakdown "
                "assistance platform. "
                "You must follow ALL of these rules strictly:\n"
                "1) Only answer questions related to MechResQ, vehicle breakdown assistance, this user's "
                "service requests, mechanics, payments, or app features.\n"
                "2) Do NOT suggest or mention external apps or sites (Google Maps, Apple Maps, Yelp, "
                "other garages, other companies, generic internet search, etc.). Always answer inside "
                "the MechResQ app context.\n"
                "3) If the question is outside this scope (for example general internet questions, "
                "unrelated personal topics, or other companies), reply exactly with: \n"
                "- I cannot answer this question because it is outside MechResQ's services.\n"
                "4) Do NOT greet, introduce yourself, or restate the question. No meta commentary.\n"
                "5) When you can answer, keep responses VERY SHORT and CLEAR. Use at most 5 bullet points, "
                "each under 20 words. No long paragraphs.\n"
                "6) Structure answers as markdown bullets under clear headings when helpful. Prefer this shape:\n"
                "- **For user**: ...\n"
                "- **For mechanic**: ...\n"
                "Add only the headings that make sense for the question and for this account's role.\n"
                "7) Anchor your answers on the context about this signed-in account and its service requests.\n"
                "8) Never invent data. If something is not in the context or clearly implied by the product, "
                "say that you don't know.\n"
            )

            full_system_message = domain_system_prompt + "\n\nContext about this signed-in account:\n" + "\n".join(context_lines)

            # Retrieve a small recent history for continuity (limit to last 4)
            chat_history_qs = ChatMessage.objects.filter(user=request.user).order_by('-timestamp')[:4]
            chat_history = list(chat_history_qs)[::-1]  # chronological order

            messages = [{"role": "system", "content": full_system_message}]
            for chat in chat_history:
                messages.append({"role": "user", "content": chat.message})
                messages.append({"role": "assistant", "content": chat.response})

            # Greeting fast-path: avoid API for trivial greetings
            if user_message.strip().lower() in {"hi", "hello", "hey", "hi!", "hello!", "hey!"}:
                if role == "mechanic":
                    quick = (
                        "- **For mechanic**: View pending requests in Service Requests.\n"
                        "- **For mechanic**: Update availability in Profile.\n"
                        "- **For mechanic**: Check earnings in Earnings.\n"
                        "- **For mechanic**: See reviews in Reviews."
                    )
                else:
                    quick = (
                        "- **For user**: Create a service request from Dashboard.\n"
                        "- **For user**: Use Nearby Mechanics on an active request.\n"
                        "- **For user**: Track status in Your Service Requests.\n"
                        "- **For user**: View payments in Payment/Receipt."
                    )
                ChatMessage.objects.create(user=request.user, message=user_message, response=quick)
                return JsonResponse({'response': quick})

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
                "temperature": 0.15,  # Very low temperature for stable, non-creative answers
                "max_tokens": 220     # Strict upper bound to keep answers compact
            }

            with httpx.Client() as client:
                response = client.post(OPENROUTER_API_BASE, headers=headers, json=payload, timeout=30.0) # Increased timeout to 30 seconds
                response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
                
                # Debugging: Print the full API response
                full_api_json = response.json()
                print("OpenRouter API Response:", full_api_json)

                try:
                    raw_content = full_api_json["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as e:
                    return JsonResponse({'error': f"Error parsing API response: {e}. Full response: {full_api_json}"}, status=500)

                # Basic sanitization: strip whitespace and known special tokens that some models may emit
                ai_response = (raw_content or "").strip()
                if ai_response in {"#*<｜begin▁of▁sentence｜>", "<｜begin▁of▁sentence｜>", "#*"}:
                    ai_response = ""

                # Format response: remove greetings/meta and enforce bullet style
                def format_bullets(text: str) -> str:
                    if not text:
                        return text
                    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                    filtered = []
                    for ln in lines:
                        low = ln.lower()
                        if low.startswith(("hi", "hello", "i am", "i'm", "the user is asking")):
                            continue
                        filtered.append(ln)

                    # Keep only headings and bullets
                    kept = []
                    bullet_count = 0
                    for ln in filtered:
                        if ln.startswith(('#', '##', '###')):
                            kept.append(ln)
                        elif ln.startswith(('-', '*')):
                            if bullet_count < 5:
                                # deduplicate consecutive repeats
                                if not kept or kept[-1] != ln:
                                    kept.append(ln)
                                bullet_count += 1
                    if kept:
                        return "\n".join(kept).strip()

                    # If no bullets, compress to a single short bullet
                    short = " ".join(filtered)
                    short = short[:200]
                    return f"- {short}".strip()

                ai_response = format_bullets(ai_response)

                # If after formatting it's still empty, use standard fallback
                if not ai_response:
                    ai_response = "- I cannot answer this question because it is outside MechResQ's services."

            ChatMessage.objects.create(
                user=request.user,
                message=user_message,
                response=ai_response
            )

            return JsonResponse({'response': ai_response})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except httpx.HTTPStatusError as e:
            # Log the full response text for debugging
            print(f"OpenRouter API HTTP Error: {e.response.status_code} - {e.response.text}")
            return JsonResponse({'error': f"HTTP error: {e.response.status_code} - {e.response.text}", 'api_response_detail': e.response.text}, status=500)
        except Exception as e:
            # Log the generic exception for debugging
            print(f"Generic Exception: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)
