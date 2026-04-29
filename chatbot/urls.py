from django.urls import path
from .views import chat_with_acubot, quick_ask

urlpatterns = [
    # Stateless one-shot endpoint required by the assignment spec.
    path('', quick_ask, name='quick_ask'),
    # Stateful endpoint with DB-persisted conversation history.
    path('ask/', chat_with_acubot, name='ask_acubot'),
]
