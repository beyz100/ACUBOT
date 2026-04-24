from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

from .services import ask_acubot
from .models import Conversation, ChatMessage

CHAT_HISTORY_SESSION_KEY = "acubot_chat_history"
CONVERSATION_ID_SESSION_KEY = "acubot_conversation_id"
MAX_CHAT_TURNS = 25


def _get_or_create_conversation(request):
    """Get existing conversation from session or create a new one."""
    if not request.session.session_key:
        request.session.create()

    conv_id = request.session.get(CONVERSATION_ID_SESSION_KEY)
    if conv_id:
        try:
            return Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            pass

    conversation = Conversation.objects.create(
        session_key=request.session.session_key or "anonymous"
    )
    request.session[CONVERSATION_ID_SESSION_KEY] = conversation.pk
    return conversation


def _save_messages_to_db(conversation, user_text, bot_text):
    """Persist a user+assistant message pair to PostgreSQL."""
    ChatMessage.objects.create(
        conversation=conversation, role='user', text=user_text
    )
    ChatMessage.objects.create(
        conversation=conversation, role='assistant', text=bot_text
    )
    conversation.save()  # updates updated_at


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def chat_ui(request):
    if request.method == "POST" and request.POST.get("clear_history"):
        request.session[CHAT_HISTORY_SESSION_KEY] = []
        # Start a fresh conversation for the next messages
        request.session.pop(CONVERSATION_ID_SESSION_KEY, None)
        request.session.modified = True
        return redirect(reverse("acubot_chat"))

    error = None
    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        if not message:
            error = "Please enter a question."
        else:
            history = request.session.get(CHAT_HISTORY_SESSION_KEY, [])
            reply = ask_acubot(message, conversation_history=history)
            history.extend(
                [
                    {"role": "user", "text": message},
                    {"role": "assistant", "text": reply},
                ]
            )
            if len(history) > MAX_CHAT_TURNS * 2:
                history = history[-(MAX_CHAT_TURNS * 2) :]
            request.session[CHAT_HISTORY_SESSION_KEY] = history
            request.session.modified = True

            # --- Persist to PostgreSQL ---
            conversation = _get_or_create_conversation(request)
            _save_messages_to_db(conversation, message, reply)

            return redirect(reverse("acubot_chat"))

    history = request.session.get(CHAT_HISTORY_SESSION_KEY, [])
    return render(
        request,
        "chatbot/chat.html",
        {"history": history, "error": error},
    )


@api_view(['POST'])
def chat_with_acubot(request):
    user_message = request.data.get('message')
    conversation_history = request.data.get('history', [])

    if not user_message:
        return Response(
            {"error": "Please provide a 'message' in your request."},
            status=status.HTTP_400_BAD_REQUEST
        )

    bot_response = ask_acubot(user_message, _conversation_history=conversation_history)

    # --- Persist to PostgreSQL ---
    conversation = _get_or_create_conversation(request)
    _save_messages_to_db(conversation, user_message, bot_response)

    return Response({
        "response": bot_response
    }, status=status.HTTP_200_OK)
