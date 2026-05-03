from django.urls import path
from .views import chat_with_acubot, quick_ask, list_conversations, get_conversation

urlpatterns = [
    path('', quick_ask, name='quick_ask'),
    path('ask/', chat_with_acubot, name='ask_acubot'),
    path('conversations/', list_conversations, name='list_conversations'),
    path('conversations/<int:conversation_id>/', get_conversation, name='get_conversation'),
]
