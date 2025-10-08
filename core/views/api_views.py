# core/views/api_views.py

import json
import logging
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

# DRF Imports for the Assistant API
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

# Relative imports from the same app
from ..models import Enrollment, Course, Video, Note
from ..forms import NoteForm
from ..rag_utils import query_router

logger = logging.getLogger(__name__)

@login_required
@require_POST
def enroll_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.get_or_create(user=request.user, course=course)
    # Redirecting to dashboard might be better handled on the frontend
    # but we'll keep it as is for now.
    return redirect('dashboard')

@login_required
def roadmap_view(request, course_id):
    # This is also an API-like view, so it fits here.
    course = get_object_or_404(Course, id=course_id)
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        return JsonResponse({'error': 'You are not enrolled in this course.'}, status=403)
    course_data = {
        'title': course.title,
        'description': course.description
    }
    return JsonResponse(course_data)

# --- Note API Views ---

@login_required
@require_POST
def add_note_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    form = NoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.user = request.user
        note.video = video
        note.save()
        note_card_html = render_to_string(
            'core/components/video_player/_note_card.html',
            {'note': note}
        )
        return JsonResponse({
            'status': 'success',
            'note_card_html': note_card_html,
        })
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@login_required
@require_POST
def edit_note_view(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    data = json.loads(request.body)
    new_title = data.get('title')
    new_content = data.get('content')

    if new_content and new_title:
        note.title = new_title
        note.content = new_content
        note.save()
        # --- FIXED: Return the updated note object in the response ---
        return JsonResponse({
            'status': 'success', 
            'message': 'Note updated successfully.',
            'note': {
                'id': note.id,
                'title': note.title,
                'content': note.content,
            }
        })
    
    return JsonResponse({'status': 'error', 'message': 'Title and content cannot be empty.'}, status=400)


@login_required
@require_POST
def delete_note_view(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    note.delete()
    return JsonResponse({'status': 'success', 'message': 'Note deleted successfully.'})

# ... (AssistantAPIView remains the same) ...
class AssistantAPIView(APIView):
    """
    API View to handle queries to the AI assistant.
    Passes all context to the query_router.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        query = request.data.get('query')
        video_id = request.data.get('video_id')
        video_title = request.data.get('video_title')
        timestamp = request.data.get('timestamp', 0)

        logger.info(f"API Request: query='{query}', video_id='{video_id}', timestamp='{timestamp}'")

        if not query:
            return Response(
                {'error': 'Query not provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            answer = query_router(
                query=query,
                video_id=video_id,
                video_title=video_title,
                timestamp=timestamp
            )
            return Response({'answer': answer}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"An error occurred in AssistantAPIView: {e}", exc_info=True)
            return Response(
                {'error': 'An error occurred while processing your request.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# --- AI Assistant API View ---

class AssistantAPIView(APIView):
    """
    API View to handle queries to the AI assistant.
    Passes all context to the query_router.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        query = request.data.get('query')
        video_id = request.data.get('video_id')
        video_title = request.data.get('video_title')
        timestamp = request.data.get('timestamp', 0)

        logger.info(f"API Request: query='{query}', video_id='{video_id}', timestamp='{timestamp}'")

        if not query:
            return Response(
                {'error': 'Query not provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            answer = query_router(
                query=query,
                video_id=video_id,
                video_title=video_title,
                timestamp=timestamp
            )
            return Response({'answer': answer}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"An error occurred in AssistantAPIView: {e}", exc_info=True)
            return Response(
                {'error': 'An error occurred while processing your request.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )