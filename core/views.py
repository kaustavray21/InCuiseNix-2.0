import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from .forms import SignUpForm, LoginForm, NoteForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Enrollment, Course, Video, Note
from django.template.defaultfilters import date as _date
import google.generativeai as genai
from django.conf import settings


# --- User Authentication and Static Pages ---


def custom_404_view(request, exception):
    """
    Redirects any 404 error to the homepage.
    """
    return redirect('home')

def home(request):
    """Renders the homepage."""
    return render(request, 'core/home.html')

def about_view(request):
    """Renders the about us page."""
    return render(request, 'core/about.html')

def signup_view(request):
    """Handles user registration."""
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
    """Handles user login."""
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
    """Handles user logout."""
    logout(request)
    return redirect('home')

# --- Core Platform Views ---

@login_required
def dashboard_view(request):
    """Displays the user's dashboard with enrolled courses."""
    enrolled_courses = Enrollment.objects.filter(user=request.user).select_related('course')
    context = {
        'enrolled_courses': [enrollment.course for enrollment in enrolled_courses]
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def courses_list_view(request):
    """Displays the list of all available courses."""
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
    """Handles a user's enrollment in a course."""
    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.get_or_create(user=request.user, course=course)
    return redirect('dashboard')

@login_required
def video_player_view(request, course_id):
    """
    Renders the video player page. The form for adding notes is passed to the context,
    but the submission is now handled by a separate AJAX view.
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Ensure the user is enrolled in the course
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    if not is_enrolled:
        return redirect('dashboard')

    # Get all videos for the course playlist
    all_videos = course.videos.all().order_by('id')
    
    # Determine which video to display
    video_id_from_url = request.GET.get('vid')
    if video_id_from_url:
        current_video = get_object_or_404(Video, video_id=video_id_from_url, course=course)
    else:
        current_video = all_videos.first()

    # Get notes for the current video
    notes = Note.objects.filter(user=request.user, video=current_video)
    
    # Pass an empty form instance for the "Add Note" modal
    form = NoteForm()

    context = {
        'course': course,
        'all_videos': all_videos,
        'current_video': current_video,
        'notes': notes,
        'form': form,
    }
    return render(request, 'core/video_player.html', context)

# --- AJAX Views for Note Management ---

@login_required
@require_POST
def add_note_view(request, video_id):
    """
    Handles adding a new note via an AJAX request to prevent page reloads.
    Returns the new note's data as JSON.
    """
    video = get_object_or_404(Video, id=video_id)
    form = NoteForm(request.POST)

    if form.is_valid():
        note = form.save(commit=False)
        note.user = request.user
        note.video = video
        note.save()
        
        # Return a JSON response with the newly created note's details
        return JsonResponse({
            'status': 'success',
            'note': {
                'id': note.id,
                'content': note.content,
                'timestamp': note.video_timestamp,
                'created_at': _date(note.created_at, 'd M Y, H:i'), # Format the date
            }
        })
    
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@login_required
@require_POST
def edit_note_view(request, note_id):
    """Handles editing a note via an AJAX request."""
    note = get_object_or_404(Note, id=note_id, user=request.user)
    data = json.loads(request.body)
    new_content = data.get('content')

    if new_content:
        note.content = new_content
        note.save()
        return JsonResponse({'status': 'success', 'message': 'Note updated successfully.'})
    
    return JsonResponse({'status': 'error', 'message': 'Content cannot be empty.'}, status=400)

@login_required
@require_POST
def delete_note_view(request, note_id):
    """Handles deleting a note via an AJAX request."""
    note = get_object_or_404(Note, id=note_id, user=request.user)
    note.delete()
    return JsonResponse({'status': 'success', 'message': 'Note deleted successfully.'})


# --- AI Assistant View ---
@login_required
def gemini_assistant_view(request):
    if request.method == 'POST':
        # 1. Explicitly check if the API key is loaded from settings
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            # Log the error to your server console for debugging
            print("CRITICAL ERROR: GEMINI_API_KEY is not set in the environment.") 
            # Return a specific error to the frontend
            return JsonResponse({
                'error': 'The AI Assistant is not configured correctly. Please contact support.'
            }, status=500)

        data = json.loads(request.body)
        prompt = data.get('prompt')

        if not prompt:
            return JsonResponse({'error': 'A prompt is required.'}, status=400)

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(prompt)

            # The API can sometimes return an empty response, handle that here.
            if response.parts:
                return JsonResponse({'response': response.text})
            else:
                return JsonResponse({'response': "I'm not sure how to respond to that. Could you try rephrasing?"})


        except Exception as e:
            # Log the detailed error from the API to your server console
            print(f"An error occurred with the Gemini API: {e}") 
            # Return a generic but helpful error to the frontend
            return JsonResponse({'error': 'An error occurred while communicating with the AI service.'}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)


# THIS IS ROADMAP VIEW

@login_required
def roadmap_view(request, course_id):
    """
    Returns the course title and description as JSON for an AJAX request.
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Security check: Ensure the user is enrolled in the requested course
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        return JsonResponse({'error': 'You are not enrolled in this course.'}, status=403)

    # Prepare the simplified data payload
    course_data = {
        'title': course.title,
        'description': course.description
    }

    return JsonResponse(course_data)