import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from .forms import SignUpForm, LoginForm, NoteForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Enrollment, Course, Video, Note, Transcript
from django.template.loader import render_to_string
import google.generativeai as genai
from django.conf import settings

def home(request):
    return render(request, 'core/home.html')

def about_view(request):
    return render(request, 'core/about.html')

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'core/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def dashboard_view(request):
    enrolled_courses = Enrollment.objects.filter(user=request.user).select_related('course')
    context = {
        'enrolled_courses': [enrollment.course for enrollment in enrolled_courses]
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def courses_list_view(request):
    enrolled_course_ids = Enrollment.objects.filter(user=request.user).values_list('course__id', flat=True)
    all_courses = Course.objects.all()
    context = {
        'all_courses': all_courses,
        'enrolled_course_ids': set(enrolled_course_ids),
    }
    return render(request, 'core/courses_list.html', context)

@login_required
@require_POST
def enroll_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.get_or_create(user=request.user, course=course)
    return redirect('dashboard')

@login_required
def roadmap_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        return JsonResponse({'error': 'You are not enrolled in this course.'}, status=403)
    course_data = {
        'title': course.title,
        'description': course.description
    }
    return JsonResponse(course_data)

@login_required
def video_player_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        return redirect('dashboard')
    
    all_videos = course.videos.all().order_by('id')
    video_obj = None 
    
    video_id_from_url = request.GET.get('vid')
    if video_id_from_url:
        video_obj = get_object_or_404(Video, id=video_id_from_url, course=course)
    elif all_videos.exists():
        video_obj = all_videos.first()

    notes = Note.objects.filter(user=request.user, video=video_obj) if video_obj else []
    form = NoteForm()

    context = {
        'course': course,
        'all_videos': all_videos,
        'video': video_obj,
        'notes': notes,
        'form': form,
    }
    return render(request, 'core/video_player.html', context)

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

@login_required
def gemini_assistant_view(request):
    if request.method == 'POST':
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return JsonResponse({'error': 'AI Assistant is not configured.'}, status=500)

        data = json.loads(request.body)
        prompt = data.get('prompt')

        if not prompt:
            return JsonResponse({'error': 'A prompt is required.'}, status=400)

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-pro')
            response = model.generate_content(prompt)
            return JsonResponse({'response': response.text})
        except Exception as e:
            return JsonResponse({'error': 'An error occurred with the AI service.'}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)

