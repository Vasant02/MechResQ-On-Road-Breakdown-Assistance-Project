from django import forms
from django import forms
from .models import Review, ServiceRequest, User, Mechanic
from django.contrib.auth.forms import UserCreationForm as AuthUserCreationForm

class UserRegistrationForm(AuthUserCreationForm):
    phone_number = forms.CharField(max_length=17, help_text="Enter phone number in format: '+999999999'. Up to 15 digits.")
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    id_proof_type = forms.ChoiceField(choices=User.ID_PROOF_CHOICES, required=False, label="ID Proof Type")
    id_proof_number = forms.CharField(max_length=50, required=False, label="ID Proof Number")
    id_proof_image = forms.ImageField(required=False, label="Upload ID Proof Photo")

    class Meta(AuthUserCreationForm.Meta):
        model = User
        fields = AuthUserCreationForm.Meta.fields + ('email', 'phone_number', 'address', 'id_proof_type', 'id_proof_number', 'id_proof_image',)
        field_classes = {'username': forms.CharField, 'email': forms.EmailField} # Ensure email is handled as an EmailField

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True # Make email required
        self.fields['email'].widget.attrs['placeholder'] = 'Your Email'
        self.fields['phone_number'].widget.attrs['placeholder'] = 'e.g. +1234567890'
        self.fields['address'].widget.attrs['placeholder'] = 'Your Residential Address'
        self.fields['id_proof_number'].widget.attrs['placeholder'] = 'Enter ID number'

class MechanicRegistrationForm(forms.ModelForm):
    # These fields correspond to the User model, but are collected on the mechanic registration form
    username = forms.CharField(max_length=150, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.")
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=17, help_text="Enter phone number in format: '+999999999'. Up to 15 digits.")
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Mechanic
        fields = ['specialization', 'experience_years', 'workshop_address', 'latitude', 'longitude', 
                  'mechanic_id_proof_type', 'mechanic_id_proof_number', 'mechanic_id_proof_image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Choose a Username'
        self.fields['email'].widget.attrs['placeholder'] = 'Your Email'
        self.fields['phone_number'].widget.attrs['placeholder'] = 'e.g. +1234567890'
        self.fields['address'].widget.attrs['placeholder'] = 'Your Residential Address'
        self.fields['password'].widget.attrs['placeholder'] = 'Password'
        self.fields['confirm_password'].widget.attrs['placeholder'] = 'Confirm Password'
        self.fields['specialization'].widget.attrs['placeholder'] = 'e.g. Car Mechanic, Bike Specialist, etc.'
        self.fields['experience_years'].widget.attrs['placeholder'] = 'Years of Experience'
        self.fields['workshop_address'].widget.attrs['placeholder'] = 'Your Workshop Address'
        self.fields['mechanic_id_proof_type'].label = "ID Proof Type"
        self.fields['mechanic_id_proof_number'].label = "ID Proof Number"
        self.fields['mechanic_id_proof_number'].widget.attrs['placeholder'] = 'Enter ID number'
        self.fields['mechanic_id_proof_image'].label = "Upload ID Proof Photo"

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        
        # Check if username/email already exists for User model (handled in views during save)
        return cleaned_data

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

class OtpForm(forms.Form):
    otp = forms.CharField(max_length=6, required=True)

class NewPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, label="New Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'profile_picture', 'preferred_language']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class MechanicProfileForm(forms.ModelForm):
    class Meta:
        model = Mechanic
        fields = ['specialization', 'experience_years', 'workshop_address', 'latitude', 'longitude', 'available', 'preferred_language']
        widgets = {
            'workshop_address': forms.Textarea(attrs={'rows': 3}),
        }
