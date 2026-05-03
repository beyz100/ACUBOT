# ACUBOT

ACUBOT is an AI Assistant built for Acıbadem University. It uses RAG (Retrieval-Augmented Generation) to answer questions about campus details, faculties, departments, and courses based on the official university information.

## Features
- **Local LLM Integration:** Uses `llama3.2:3b` via Ollama to respond to user queries.
- **Chat History:** Persistent conversations via PostgreSQL and Django.
- **Zero-Config Setup:** Setup can be achieved by a single command `docker-compose up --build`.
- **Automated Data Seeding:** The database populates itself with courses and university info on the first run.
- **RESTful API:** Clean API endpoints for frontend usage.

## Architecture
1. **Frontend:** Vanilla JS/HTML SPA-like interface (served via `/chat/`).
2. **Backend:** Django & Django REST Framework.
3. **Data & AI:** PostgreSQL for data persistence and Ollama for the LLM engine.

```mermaid
graph LR
    User -->|HTTP (80)| Nginx[Nginx Reverse Proxy]
    Nginx -->|Proxy| Web[Django Web Service]
    Web -->|SQL| DB[(PostgreSQL)]
    Web -->|API Request| LLM[Ollama llama3.2:3b]
    
    subgraph Docker Network
        Nginx
        Web
        DB
        LLM
    end
```

## Quick Start
You just need Docker and Docker Compose installed.

```bash
docker-compose up --build
```
This command:
- Starts the Postgres and Ollama containers.
- The `llm-init` service automatically pulls the `llama3.2:3b` model.
- Django runs its migrations and seeds the database using `seed.py`.
- Starts the development server behind an Nginx reverse proxy.

Once the terminal settles down, you can visit `http://localhost/chat/`.

## API Endpoints
If you're building a separate frontend or a mobile app, these are the core endpoints you'll want to hit:

**Conversations:**
- `GET /api/chat/conversations/` - List your chats
- `POST /api/chat/conversations/` - Create a new chat session
- `GET /api/chat/conversations/<id>/` - Get chat details
- `PATCH /api/chat/conversations/<id>/` - Update the chat title
- `DELETE /api/chat/conversations/<id>/` - Delete a chat and its messages

**Messages:**
- `GET /api/chat/conversations/<id>/messages/` - See the chat history
- `POST /api/chat/conversations/<id>/send/` - Send a message to the AI

**Anonymous/Session-Based Chat:**
- `POST /api/chat/ask/` - Quick response without saving into a chat session.

## Working with the Frontend
Make sure you include the CSRF token when making POST, PATCH, or DELETE requests. Here's an example using the Fetch API:

```javascript
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

fetch('/api/chat/conversations/<uuid>/send/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({ message: "Where is the engineering faculty?" })
})
.then(res => res.json())
.then(data => console.log(data.response));
```

## Database Models
- **Conversation:** Represents an entire chat thread. Fields: `id` (UUID), `title`, `created_at`, `updated_at`.
- **Message:** Belongs to a conversation. Fields: `role` (user or assistant), `content`, `created_at`.

## Production & Cloud Deployment
Deploying this stack to AWS (EC2) or GCP has a few hardware constraints simply because running language models locally is heavy.

**Hardware Requirements:**
You'll need at least **8GB RAM** and **2 vCPUs**. 
`llama3.2:3b` will reserve about 3-4 GB of RAM right away.

**Steps:**
1. Spin up an Ubuntu 24.04 instance.
2. Open ports `22`, `80`, and `443` in your Security Group / Firewall.
3. Install Docker and clone the repository.
4. Run `sudo docker compose up --build -d`.

> [!NOTE]
> The first deploy will take a couple of minutes because the `llm-init` container needs to download the AI model. You can check what's going on by running `sudo docker compose logs -f llm-init`.

**CI/CD Ideas:**
You can easily automate deployments using GitHub Actions. Use `appleboy/ssh-action` to connect to your EC2 instance on push to the `main` branch, pull the latest code, and restart the containers. Make sure to put Nginx and Certbot in front to secure everything with HTTPS.

## Team
- **Beyza Yüz** ([@beyz100](https://github.com/beyz100)) — Backend, AI/RAG integration, DevOps
- **Ceren Yurdunol** ([@Mirket07](https://github.com/Mirket07)) — REST API, models, migrations
- **Armita Tavakolshoar** ([@armita-41](https://github.com/armita-41)) — Scraping, fixtures, LLM evaluation