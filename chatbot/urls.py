from django.urls import path
from .views import chat_with_acubot

urlpatterns = [
    path('ask/', chat_with_acubot, name='ask_acubot'),
]