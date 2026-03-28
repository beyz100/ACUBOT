from django.urls import path

from .views import chat_ui

urlpatterns = [
    path("", chat_ui, name="acubot_chat"),
]
