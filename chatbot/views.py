from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import ask_acubot

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
