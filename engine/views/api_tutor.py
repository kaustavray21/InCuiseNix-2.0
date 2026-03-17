import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from engine.tutor_service.gemini_tutor import generate_tutor_questions
from engine.tutor_service.sarvam_tutor import create_sarvam_tutor_call

@csrf_exempt
@require_POST
def start_tutor_session(request):
    try:
        data = json.loads(request.body)
        course = data.get('course')
        level = data.get('level')
        num_questions = int(data.get('num_questions', 5))
        phone_number = data.get('phone_number')

        qa_list = generate_tutor_questions(course, level, num_questions)
        call_info = create_sarvam_tutor_call(qa_list, phone_number)
        
        return JsonResponse({"status": "success", "call_info": call_info})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)