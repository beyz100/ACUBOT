import requests
from courses.models import Course
from courses.retrieval import get_retrieval_context, format_context_for_llm

OLLAMA_API_URL = "http://llm:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"

def ask_acubot(user_message):
    try:
        context = get_retrieval_context(user_message, search_method='hybrid')
    except Exception:
        courses = Course.objects.select_related('department').all()[:15]
        context = {
            'courses': courses,
            'departments': [],
            'university_info': [],
            'faculties': []
        }
    
    context_text = format_context_for_llm(context)

    prompt = f"""You are ACUBOT, a polite, energetic, and informal assistant bot helping Acibadem University students.
Below is the course information retrieved from the database. Answer the student's question using ONLY this information.
If the answer is not available in this information, honestly say 'Sorry, I cannot find this information in my database right now.' Do not make up answers.

{context_text}

Student's Question: {user_message}

Your response as ACUBOT:"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "").strip()
        else:
            return f"The AI server returned an error. Status Code: {response.status_code}"
            
    except requests.exceptions.RequestException:
        return "I cannot connect to my brain (the Qwen model) right now. The download might not be finished, or there is a Docker network issue."