import requests
from django.conf import settings

def create_sarvam_tutor_call(qa_list: list, phone_number: str) -> dict:
    headers = {
        "api-subscription-key": settings.SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    qa_context = "\n".join([f"Q: {item['question']}\nA: {item['expected_answer']}" for item in qa_list])
    system_prompt = f"""
    You are an AI Tutor. You will ask the user the following questions one by one.
    Wait for their answer, evaluate it based on the expected answer, provide brief feedback, and move to the next question.
    
    Questions and Expected Answers:
    {qa_context}
    """
    agent_payload = {
        "agent_name": "InCuiseNix Tutor",
        "system_prompt": system_prompt,
        "llm_config": {"model": "sarvam-1"},
        "voice": "en-IN-Standard-A"
    }
    agent_res = requests.post(f"{settings.SARVAM_BASE_URL}/agents", json=agent_payload, headers=headers)
    agent_res.raise_for_status()
    agent_id = agent_res.json().get("agent_id")
    
    call_payload = {
        "agent_id": agent_id,
        "customer_number": phone_number
    }
    call_res = requests.post(f"{settings.SARVAM_BASE_URL}/calls", json=call_payload, headers=headers)
    call_res.raise_for_status()
    return call_res.json()