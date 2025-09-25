from django import forms
from .models import Review, ServiceRequest

class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(widget=forms.HiddenInput(), required=True)
    comment = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=True)
    
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].label = "Rating"
        self.fields['comment'].label = "Your Comments"
        self.fields['rating'].help_text = "Click on the stars to rate your experience"
        self.fields['comment'].help_text = "Please share your experience with the service"

class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['vehicle_type', 'issue_description', 'issue_image', 'issue_video', 'issue_file', 'location', 'latitude', 'longitude']
        widgets = {
            'issue_description': forms.Textarea(attrs={'rows': 4}),
        }
