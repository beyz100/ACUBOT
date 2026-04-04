from django.urls import path
from .views import (
    chat_with_acubot,
    conversations_list,
    conversation_detail,
    conversation_messages,
    send_message,
)

urlpatterns = [
    path('ask/', chat_with_acubot, name='ask_acubot'),
    path('conversations/', conversations_list, name='conversations_list'),
    path('conversations/<int:conversation_id>/', conversation_detail, name='conversation_detail'),
    path('conversations/<int:conversation_id>/messages/', conversation_messages, name='conversation_messages'),
    path('conversations/<int:conversation_id>/send/', send_message, name='send_message'),
]

