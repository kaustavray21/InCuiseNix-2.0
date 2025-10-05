from django.urls import path
from . import views

urlpatterns = [
    path('download/<int:video_id>/', views.download_transcript_view, name='download_transcript'),
]