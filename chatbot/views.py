from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import ask_acubot

CHAT_HISTORY_SESSION_KEY = "acubot_chat_history"
MAX_CHAT_TURNS = 25


@require_http_methods(["GET", "POST"])
def chat_ui(request):
    if request.method == "POST" and request.POST.get("clear_history"):
        request.session[CHAT_HISTORY_SESSION_KEY] = []
        request.session.modified = True
        return redirect(reverse("acubot_chat"))

    error = None
    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        if not message:
            error = "Please enter a question."
        else:
            reply = ask_acubot(message)
            history = request.session.get(CHAT_HISTORY_SESSION_KEY, [])
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

    if not user_message:
        return Response(
            {"error": "Please provide a 'message' in your request."},
            status=status.HTTP_400_BAD_REQUEST
        )

    bot_response = ask_acubot(user_message)

    return Response({
        "response": bot_response
    }, status=status.HTTP_200_OK)
