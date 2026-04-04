from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

from .services import ask_acubot
from .models import Conversation, Message
from .serializers import ConversationSerializer, ConversationListSerializer, MessageSerializer

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

    bot_response = ask_acubot(user_message, conversation_history=conversation_history)

    return Response({
        "response": bot_response
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conversations_list(request):
    if request.method == 'GET':
        conversations = Conversation.objects.filter(user=request.user)
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        title = request.data.get('title', 'New Conversation')
        conversation = Conversation.objects.create(user=request.user, title=title)
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def conversation_detail(request, conversation_id):
    try:
        conversation = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return Response(
            {"error": "Conversation not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data)

    if request.method == 'DELETE':
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == 'PATCH':
        title = request.data.get('title')
        if title:
            conversation.title = title
            conversation.save()
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_messages(request, conversation_id):
    try:
        conversation = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return Response(
            {"error": "Conversation not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    messages = conversation.messages.all()
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, conversation_id):
    try:
        conversation = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return Response(
            {"error": "Conversation not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    user_message = request.data.get('message', '').strip()
    if not user_message:
        return Response(
            {"error": "Message cannot be empty."},
            status=status.HTTP_400_BAD_REQUEST
        )

    Message.objects.create(conversation=conversation, role='user', content=user_message)

    history = [
        {"role": msg.role, "text": msg.content}
        for msg in conversation.messages.all()
    ]

    bot_response = ask_acubot(user_message, conversation_history=history)

    Message.objects.create(conversation=conversation, role='assistant', content=bot_response)

    messages = conversation.messages.all()
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


