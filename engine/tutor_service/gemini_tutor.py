import google.generativeai as genai
import json
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def generate_tutor_questions(course_name: str, level: str, num_questions: int) -> list:
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    Generate {num_questions} questions for a {level} level course on {course_name}.
    Return ONLY a valid JSON array of objects with keys "question" and "expected_answer".
    """
    response = model.generate_content(prompt)
    raw_text = response.text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:-3]
    return json.loads(raw_text)