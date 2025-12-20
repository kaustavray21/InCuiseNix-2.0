from django.contrib import admin
from .models import Course, Video, Enrollment, Note, OCRTranscript

admin.site.register(Course)
admin.site.register(Video)
admin.site.register(Enrollment)
admin.site.register(Note)

@admin.register(OCRTranscript)
class OCRTranscriptAdmin(admin.ModelAdmin):
    list_display = ('video', 'start', 'content_snippet')
    search_fields = ('video__title', 'content')
    list_filter = ('video__course',)

    def content_snippet(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content