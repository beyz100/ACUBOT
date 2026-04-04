# ACUBOT - Acibadem University AI Chatbot

Django tabanlı AI sohbet uygulaması. Acibadem Üniversitesi hakkında sorular sorabileceğiniz bir chatbot.

## Özellikler

- Sohbet geçmişi yönetimi
- Kalıcı sohbet saklama (veritabanında)
- RESTful API
- Frontend-Backend Entegrasyonu
- Kullanıcı kimlik doğrulaması
- CSRF Koruması

## Belgeler

- **SETUP.md** - Kurulum ve temel kullanım
- **MODELS.md** - Veritabanı modelleri (Conversation, Message)
- **ENDPOINTS.md** - API endpoints detaylı belgesi
- **INTEGRATION.md** - Frontend-API entegrasyonu
- **USAGE.md** - Kod örnekleri (JavaScript, Python, cURL)

## Hızlı Başlangıç

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Tarayıcıda açın: http://localhost:8000/chat/

## API Endpoints

### Sohbet Yönetimi
- `GET /api/chat/conversations/` - Sohbetleri listele
- `POST /api/chat/conversations/` - Yeni sohbet oluştur
- `GET /api/chat/conversations/<id>/` - Sohbet detayları
- `PATCH /api/chat/conversations/<id>/` - Sohbet güncelle
- `DELETE /api/chat/conversations/<id>/` - Sohbet sil

### Mesajlar
- `GET /api/chat/conversations/<id>/messages/` - Mesajları getir
- `POST /api/chat/conversations/<id>/send/` - Mesaj gönder

### Hızlı Sorular
- `POST /api/chat/ask/` - Session tabanlı sorular

## Mimari

**Frontend:** `/chat/` - JavaScript + HTML + CSS (Single Page App)
**Backend:** `/api/chat/` - Django REST API
**Database:** Conversation ve Message modelleri

## Teknolojiler

- Django 5.0+
- Django REST Framework
- PostgreSQL (Docker)
- Ollama LLM (Docker)
- JavaScript (Frontend)

## Dosya Yapısı

```
ACUBOT/
├── chatbot/
│   ├── models.py (Conversation, Message)
│   ├── views.py (API endpoints)
│   ├── serializers.py (JSON dönüşüm)
│   ├── urls.py (API routing)
│   ├── templates/
│   │   └── chat.html (Frontend)
│   └── migrations/
├── config/
│   ├── settings.py
│   └── urls.py
├── requirements.txt
├── manage.py
└── README.md
```

## Veritabanı Tabloları

- `chatbot_conversation` - Sohbetler
- `chatbot_message` - Mesajlar

## Kullanıcı Akışı

1. /chat/ adresine gidilir
2. Sidebar'da sohbetler görünür
3. "New Chat" butonuyla yeni sohbet oluşturulur
4. Sohbet seçilir
5. Mesaj yazılır ve gönderilir
6. AI yanıt verir
7. Geçmiş otomatik kaydedilir

## Güvenlik

- CSRF Token Koruması
- Kullanıcı Kimlik Doğrulaması (Django Session)
- IsAuthenticated Permission
- Veritabanı Isolation (Her kullanıcı sadece kendi sohbetlerini görebilir)

## Katkılar

Konuyla ilgili sorunlar için burada bildirin veya pull request gönderin.

## Lisans

MIT

