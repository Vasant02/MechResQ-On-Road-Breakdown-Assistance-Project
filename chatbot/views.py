from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
import google.generativeai as genai
from .models import ChatMessage
from core.models import ServiceRequest, Mechanic

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(
    model_name=settings.GEMINI_MODEL,
    safety_settings=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ],
    system_instruction=(
        "You are 'ResQAssist', the virtual assistant for MechResQ, an on-road vehicle breakdown "
        "assistance platform. You must follow ALL of these rules strictly:\n"
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
)


def _build_context_message(request, role, mechanic_obj, recent_requests):
    sr_summaries = [
        f"#{sr.id} | status={sr.status} | vehicle={sr.vehicle_type} | issue={sr.issue_description[:80]}"
        for sr in recent_requests
    ]

    context_lines = [
        f"Current user role: {role}",
        f"Username: {request.user.username}",
        f"Full name: {request.user.get_full_name() or request.user.username}",
    ]

    if role == "mechanic" and mechanic_obj:
        context_lines.append(
            "Mechanic details: specialization={specialization}, experience_years={experience_years}, rating={rating}".format(
                specialization=mechanic_obj.specialization,
                experience_years=mechanic_obj.experience_years,
                rating=mechanic_obj.rating,
            )
        )

    if sr_summaries:
        context_lines.append("Recent related service requests (max 5):")
        context_lines.extend(f"- {line}" for line in sr_summaries)

    return "Context about this signed-in account:\n" + "\n".join(context_lines)


def _fallback_ai_message(user, user_message: str, detail: str | None = None):
    """
    Fallback when Gemini fails.

    IMPORTANT:
    - Does NOT generate any chatbot-style text.
    - Just returns an HTTP error so the frontend can show its own generic message.
    - This ensures that ANY normal 'response' text the user sees always comes from Gemini.
    """
    if detail:
        print(f"Chatbot fallback triggered: {detail}")

    return JsonResponse(
        {
            "error": "GEMINI_UNAVAILABLE",
            "detail": "AI service temporarily unavailable. Please try again.",
        },
        status=503,
    )


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

            role = "mechanic" if getattr(request.user, "is_mechanic", False) else "user"

            mechanic_obj = None
            if role == "mechanic":
                mechanic_obj = Mechanic.objects.filter(user=request.user).first()

            if role == "mechanic":
                recent_requests = ServiceRequest.objects.filter(
                    mechanic__user=request.user
                ).order_by('-created_at')[:3]
            else:
                recent_requests = ServiceRequest.objects.filter(
                    user=request.user
                ).order_by('-created_at')[:3]

            context_message = _build_context_message(request, role, mechanic_obj, recent_requests)

            # Retrieve a small recent history for continuity (limit to last 4)
            chat_history_qs = ChatMessage.objects.filter(
                user=request.user
            ).order_by('-timestamp')[:4]
            chat_history = list(chat_history_qs)[::-1]  # chronological order

            # Build messages for Gemini API
            messages_for_gemini = [
                {"role": "user", "parts": [context_message]},
            ]

            for chat in chat_history:
                messages_for_gemini.append({"role": "user", "parts": [chat.message]})
                messages_for_gemini.append({"role": "model", "parts": [chat.response]})

            messages_for_gemini.append({"role": "user", "parts": [user_message]})

            try:
                response = gemini_model.generate_content(
                    messages_for_gemini,
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        stop_sequences=[],
                        temperature=0.15,
                        max_output_tokens=800,
                    ),
                    safety_settings=[
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ],
                )

                raw_content = ""
                if getattr(response, "candidates", None):
                    first_candidate = response.candidates[0]
                    if getattr(first_candidate, "content", None) and getattr(first_candidate.content, "parts", None):
                        for part in first_candidate.content.parts:
                            if getattr(part, "text", None):
                                raw_content += part.text

                ai_response = (raw_content or "").strip()

            except Exception as e:
                detail = f"Gemini API exception: {str(e)}"
                return _fallback_ai_message(request.user, user_message, detail=detail)

            # Store exactly what Gemini said
            ChatMessage.objects.create(
                user=request.user,
                message=user_message,
                response=ai_response
            )

            return JsonResponse({'response': ai_response})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            detail = f"Generic chatbot exception: {str(e)}"
            return _fallback_ai_message(request.user, "UNKNOWN", detail=detail)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def chat_history(request):
    limit = int(request.GET.get('limit', 10))
    limit = max(1, min(limit, 25))
    chats = ChatMessage.objects.filter(user=request.user).order_by('-timestamp')[:limit]
    history = [
        {
            'message': chat.message,
            'response': chat.response,
            'timestamp': chat.timestamp.isoformat()
        }
        for chat in reversed(list(chats))
    ]
    return JsonResponse({'history': history})
