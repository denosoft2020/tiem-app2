from django import forms
from .models import Profile, Post

#form for profile page
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'profile_picture']

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            if picture.size > 2*1024*1024:  # 2MB limit
                raise forms.ValidationError("Image file too large (max 2MB)")
            return picture
        return None   

# Forms.py (Create an upload form)
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['media_file', 'caption', 'filter_effect', 'duration']
        widgets = {
            'media_file': forms.FileInput(attrs={
                'accept': 'image/*,video/*',
                'capture': 'environment',
                'class': 'file-input',
                'id': 'media-upload'
            }),
            'caption': forms.Textarea(attrs={
                'placeholder': 'Write a caption...',
                'rows': 3
            }),
            'filter_effect': forms.Select(attrs={
                'class': 'filter-select'
            }),
            'duration': forms.NumberInput(attrs={
                'min': 1,
                'max': 60,
                'class': 'duration-input'
            })
        }

class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'accept': 'image/*', 
                'capture': 'environment'  # This enables camera on mobile
            })
        }
        
    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture and picture.size > 2*1024*1024:  # 2MB limit
            raise forms.ValidationError("Image file too large ( > 2MB )")
        return picture