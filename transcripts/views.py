import os
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from core.models import Video
from .services import sanitize_filename