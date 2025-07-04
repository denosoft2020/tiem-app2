from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import Profile,  LiveStream

# User Registration Form
class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True, help_text='Required. Enter a valid email address.')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

# Profile Update Form
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us about yourself...'}),
        }

# Profile Picture Form
class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_picture']

# Post Creation Form

# Live Stream Form
class LiveStreamForm(forms.ModelForm):
    class Meta:
        model = LiveStream
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Enter stream title...'
            })
        }

class EmailChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']

class CustomPasswordChangeForm(PasswordChangeForm):
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        # Add custom validation if needed
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise ValidationError("The two password fields didn't match.")
        
        try:
            validate_password(new_password1, self.user)
        except ValidationError as e:
            self.add_error('new_password1', e)
        
        return cleaned_data

class PrivacySettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['is_private', 'show_activity']

class SupportForm(forms.Form):
    subject = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea)
