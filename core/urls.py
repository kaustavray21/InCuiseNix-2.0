from django.urls import path
from . import views

urlpatterns = [
    # Existing URL patterns
    path('', views.home, name='home'),
    path('about/', views.about_view, name='about'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('courses/', views.courses_list_view, name='courses_list'),
    path('enroll/<int:course_id>/', views.enroll_view, name='enroll'),
    path('roadmap/<int:course_id>/', views.roadmap_view, name='roadmap'),
    path('course/<int:course_id>/', views.video_player_view, name='video_player'),

    # Note URLs
    path('notes/add/<int:video_id>/', views.add_note_view, name='add_note'),
    path('notes/edit/<int:note_id>/', views.edit_note_view, name='edit_note'),
    path('notes/delete/<int:note_id>/', views.delete_note_view, name='delete_note'),

    # --- NEW: Assistant API URL ---
    path('api/assistant/', views.AssistantAPIView.as_view(), name='assistant_api'),
]
handler404 = 'core.views.custom_404_view'