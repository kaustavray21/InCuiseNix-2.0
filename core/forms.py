from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Note

# 1. Create a Base Form or Mixin for styling
class FormStylingMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

# 2. Update your forms to use the Mixin
class SignUpForm(FormStylingMixin, UserCreationForm):
    email = forms.EmailField(max_length=254, required=True, help_text='Required. Please enter a valid email address.')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')
    
    # The __init__ method is no longer needed here

class LoginForm(FormStylingMixin, AuthenticationForm):
    # The __init__ method is no longer needed here
    pass

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        # Add 'title' to the list of fields
        fields = ['title', 'content', 'video_timestamp']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter note title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your note here...'}),
            'video_timestamp': forms.HiddenInput(),
        }