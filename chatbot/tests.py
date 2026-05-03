from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from .models import Conversation, ChatMessage
from .services import LLMReply


class ChatbotModelTests(TestCase):
    def setUp(self):
        # Testler için sahte bir sohbet oluştur
        self.conversation = Conversation.objects.create(session_key="test_session_123")

    def test_conversation_and_message_creation(self):
        """Modellerin düzgün oluşturulup oluşturulmadığını test et."""
        msg_user = ChatMessage.objects.create(
            conversation=self.conversation, role="user", text="Merhaba ACUBOT"
        )
        msg_bot = ChatMessage.objects.create(
            conversation=self.conversation, role="assistant", text="Size nasıl yardımcı olabilirim?"
        )

        # Veritabanına kayıt atıldığını doğrula
        self.assertEqual(self.conversation.messages.count(), 2)
        # String (__str__) metodunun doğru formatta döndüğünü test et
        self.assertTrue("[Kullanıcı]" in str(msg_user))
        self.assertTrue("Merhaba ACUBOT" in str(msg_user))


class ChatbotAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('chatbot.views.ask')
    def test_quick_ask_api(self, mock_ask):
        """
        Yapay zekayı (Ollama) meşgul etmeden, API'ın doğru çalışıp çalışmadığını
        (Mocking yöntemi ile) test eder.
        """
        # Yapay zekadan geliyormuş gibi sahte bir cevap oluşturuyoruz
        mock_ask.return_value = LLMReply(
            text="Bu bir test cevabıdır.",
            language="tr",
            context_size=3,
            error=False
        )

        # API'a istek at
        url = reverse('quick_ask')
        response = self.client.post(url, {'message': 'Bölüm başkanı kim?'}, format='json')

        # Başarı durumlarını kontrol et
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['answer'], "Bu bir test cevabıdır.")
        self.assertFalse(response.data['error'])

    def test_quick_ask_empty_message(self):
        """Boş mesaj gönderildiğinde API'ın 400 Bad Request döndüğünü test et."""
        url = reverse('quick_ask')
        response = self.client.post(url, {'message': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class ChatbotViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_chat_ui_loads_properly(self):
        """Ana sohbet sayfasının 200 HTTP kodu ile çöksüz açıldığını test et."""
        url = reverse('acubot_chat')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chatbot/chat.html')