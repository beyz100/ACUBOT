from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import ask
from .models import Conversation, ChatMessage
from .serializers import ConversationSerializer, ConversationListSerializer

CHAT_HISTORY_SESSION_KEY = "acubot_chat_history"
CONVERSATION_ID_SESSION_KEY = "acubot_conversation_id"
MAX_CHAT_TURNS = 25


def _get_or_create_conversation(request):
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
    ChatMessage.objects.create(
        conversation=conversation, role='user', text=user_text
    )
    ChatMessage.objects.create(
        conversation=conversation, role='assistant', text=bot_text
    )
    conversation.save()  


def _history_for_llm(history):
    return [(item["role"], item["text"]) for item in history if "role" in item]


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def chat_ui(request):
    if request.method == "POST" and request.POST.get("clear_history"):
        request.session[CHAT_HISTORY_SESSION_KEY] = []
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
            reply = ask(message, history=_history_for_llm(history))
            history.extend(
                [
                    {"role": "user", "text": message},
                    {"role": "assistant", "text": reply.text},
                ]
            )
            if len(history) > MAX_CHAT_TURNS * 2:
                history = history[-(MAX_CHAT_TURNS * 2) :]
            request.session[CHAT_HISTORY_SESSION_KEY] = history
            request.session.modified = True

            conversation = _get_or_create_conversation(request)
            _save_messages_to_db(conversation, message, reply.text)

            return redirect(reverse("acubot_chat"))

    history = request.session.get(CHAT_HISTORY_SESSION_KEY, [])
    return render(
        request,
        "chatbot/chat.html",
        {"history": history, "error": error},
    )


@api_view(['POST'])
def quick_ask(request):
    user_message = (request.data.get('message') or '').strip()
    if not user_message:
        return Response(
            {"error": "Please provide a non-empty 'message' in your request."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    reply = ask(user_message)
    return Response(
        {
            "answer": reply.text,
            "language": reply.language,
            "context_size": reply.context_size,
            "error": reply.error,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
def chat_with_acubot(request):
    # Ensure session is created before any session operations
    if not request.session.session_key:
        request.session.create()

    user_message = (request.data.get('message') or '').strip()
    client_history = request.data.get('history', [])
    new_conversation_raw = request.data.get('new_conversation', False)
    new_conversation = str(new_conversation_raw).lower() == 'true' or new_conversation_raw is True

    if not user_message:
        return Response(
            {"error": "Please provide a 'message' in your request."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if new_conversation:
        if CONVERSATION_ID_SESSION_KEY in request.session:
            del request.session[CONVERSATION_ID_SESSION_KEY]
        request.session.modified = True

    conversation = _get_or_create_conversation(request)

    if client_history:
        history_tuples = _history_for_llm(client_history)
    else:
        history_tuples = [
            (m.role, m.text) for m in conversation.messages.all()
        ]

    from django.http import StreamingHttpResponse
    import json
    from .services import ask_stream

    def generate():
        full_text = ""
        for chunk in ask_stream(user_message, history=history_tuples):
            if chunk["type"] == "chunk":
                full_text += chunk["text"]
                yield json.dumps({"type": "chunk", "text": chunk["text"]}) + "\n"
            elif chunk["type"] == "done":
                _save_messages_to_db(conversation, user_message, chunk["text"])
                yield json.dumps({
                    "type": "done",
                    "text": chunk["text"],
                    "language": chunk["language"],
                    "context_size": chunk["context_size"],
                    "error": chunk["error"]
                }) + "\n"

    return StreamingHttpResponse(generate(), content_type="application/x-ndjson")


@api_view(['GET'])
def list_conversations(request):
    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key
    conversations = Conversation.objects.filter(
        session_key=session_key
    ).order_by('-updated_at')

    serializer = ConversationListSerializer(conversations, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_conversation(request, conversation_id):
    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key

    try:
        conversation = Conversation.objects.get(
            pk=conversation_id,
            session_key=session_key
        )
    except Conversation.DoesNotExist:
        return Response(
            {"error": "Conversation not found or access denied."},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = ConversationSerializer(conversation)
    return Response(serializer.data, status=status.HTTP_200_OK)

