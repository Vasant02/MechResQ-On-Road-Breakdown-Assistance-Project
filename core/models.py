from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from decimal import Decimal
from django.conf import settings # Import settings
from geopy.distance import geodesic # Import geodesic for distance calculation

# Define language choices based on settings.LANGUAGES
LANGUAGE_CHOICES = settings.LANGUAGES

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('SERVICE_REQUEST', 'Service Request'),
        ('STATUS_UPDATE', 'Status Update'),
        ('PAYMENT', 'Payment'),
        ('REVIEW', 'Review'),
    ]

    recipient = models.ForeignKey('User', on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} - {self.title}"

    @classmethod
    def create_service_request_notification(cls, recipient, service_request):
        if getattr(recipient, 'is_mechanic', False):
            title = "New Request Received"
            message = "A new service request is available near your area."
        else:
            title = "Request Created Successfully"
            message = "Your service request has been created successfully."
        return cls.objects.create(
            recipient=recipient,
            notification_type='SERVICE_REQUEST',
            title=title,
            message=message
        )

    @classmethod
    def create_status_update_notification(cls, recipient, service_request):
        status = service_request.status
        if status == 'PENDING':
            title = "Request Under Review"
            message = "Your request is being reviewed by our team."
        elif status == 'ACCEPTED':
            title = "Mechanic Accepted Request"
            message = "A mechanic has accepted your request! They will contact you soon."
        elif status == 'IN_PROGRESS':
            title = "Mechanic On The Way"
            message = "Your assigned mechanic is en route to your location."
        elif status == 'COMPLETED':
            title = "Service Completed Successfully"
            message = "Your service has been completed successfully. Please provide feedback."
        elif status == 'CANCELLED':
            title = "Request Cancelled"
            message = "Your service request has been cancelled."
        else:
            title = f"Status Update for Request #{service_request.id}"
            message = f"Your service request status has been updated to {service_request.status}."
        return cls.objects.create(
            recipient=recipient,
            notification_type='STATUS_UPDATE',
            title=title,
            message=message
        )

    @classmethod
    def create_payment_notification(cls, recipient, payment):
        status = payment.payment_status
        if getattr(recipient, 'is_mechanic', False):
            if status == 'PAID':
                title = "Payment Received Successfully"
                message = "Payment for your last service has been credited to your wallet."
            elif status == 'FAILED':
                title = "Payment Failed"
                message = "User’s payment for a completed service has failed."
            else:
                title = f"Payment Update for Request #{payment.service_request.id}"
                message = "Payment status has been updated."
        else:
            if status == 'PAID':
                title = "Payment Successful"
                message = "Your payment was processed securely."
            elif status == 'FAILED':
                title = "Payment Failed"
                message = "Payment failed. Please try again or use another method."
            else:
                title = f"Payment Update for Request #{payment.service_request.id}"
                message = "Payment status has been updated."
        return cls.objects.create(
            recipient=recipient,
            notification_type='PAYMENT',
            title=title,
            message=message
        )

    @classmethod
    def create_review_notification(cls, recipient, review):
        if getattr(recipient, 'is_mechanic', False):
            title = "User Feedback Received"
            message = "You’ve received feedback from a recent service."
        else:
            title = f"New Review for Request #{review.service_request.id}"
            message = f"You received a {review.rating}-star review."
        return cls.objects.create(
            recipient=recipient,
            notification_type='REVIEW',
            title=title,
            message=message
        )

    @classmethod
    def create_profile_updated_notification(cls, recipient):
        if getattr(recipient, 'is_mechanic', False):
            title = "Profile Updated Successfully"
            message = "Your profile information has been updated."
        else:
            title = "Profile Updated Successfully"
            message = "Your profile details have been updated."
        return cls.objects.create(
            recipient=recipient,
            notification_type='STATUS_UPDATE',
            title=title,
            message=message
        )

    @classmethod
    def create_password_changed_notification(cls, recipient):
        if getattr(recipient, 'is_mechanic', False):
            title = "Password Changed Successfully"
            message = "Your account password has been updated."
        else:
            title = "Password Changed Successfully"
            message = "Your password has been updated for account security."
        return cls.objects.create(
            recipient=recipient,
            notification_type='STATUS_UPDATE',
            title=title,
            message=message
        )

    @classmethod
    def create_welcome_notification(cls, recipient):
        if getattr(recipient, 'is_mechanic', False):
            title = f"Welcome {recipient.get_full_name()}!"
            message = "Welcome back to MechResQ! Ready to assist stranded users."
        else:
            title = f"Welcome {recipient.get_full_name()}!"
            message = "Welcome back! We’re ready to assist you."
        return cls.objects.create(
            recipient=recipient,
            notification_type='STATUS_UPDATE',
            title=title,
            message=message
        )

    @classmethod
    def create_logout_notification(cls, recipient):
        title = "Logout Successful"
        message = "You’ve logged out safely. See you again soon!"
        return cls.objects.create(
            recipient=recipient,
            notification_type='STATUS_UPDATE',
            title=title,
            message=message
        )

    @classmethod
    def create_feedback_submitted_notification(cls, recipient):
        title = "Feedback Submitted"
        message = "Thanks for your valuable feedback!"
        return cls.objects.create(
            recipient=recipient,
            notification_type='REVIEW',
            title=title,
            message=message
        )

    @classmethod
    def create_invoice_generated_notification(cls, recipient, payment):
        if getattr(recipient, 'is_mechanic', False):
            title = "Invoice Generated"
            message = "Invoice for this service has been generated and sent to the user."
        else:
            title = "Invoice Generated"
            message = "Invoice generated for your completed service. Check your email."
        return cls.objects.create(
            recipient=recipient,
            notification_type='PAYMENT',
            title=title,
            message=message
        )

    @classmethod
    def create_rating_updated_notification(cls, mechanic):
        title = "Rating Updated"
        message = "Your average rating has been updated."
        return cls.objects.create(
            recipient=mechanic.user,
            notification_type='REVIEW',
            title=title,
            message=message
        )

class User(AbstractUser):
    is_mechanic = models.BooleanField(default=False)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pics/', 
        null=True, 
        blank=True
    )
    ID_PROOF_CHOICES = [
        ('AADHAR', 'Aadhar Card'),
        ('DL', 'Driver\'s License'),
        ('ID_CARD', 'Other ID Card'),
    ]
    
    fcm_token = models.CharField(max_length=255, blank=True, null=True, verbose_name="FCM Token for Push Notifications")
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en') # New field
    
    id_proof_type = models.CharField(max_length=20, choices=ID_PROOF_CHOICES, blank=True, null=True)
    id_proof_number = models.CharField(max_length=50, blank=True, null=True)
    id_proof_image = models.ImageField(upload_to='id_proofs/', null=True, blank=True)

    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        if self.is_mechanic:
            return '/static/images/Mechanic.png'
        return '/static/images/User.png'

class Mechanic(models.Model):
    ID_PROOF_CHOICES = [
        ('AADHAR', 'Aadhar Card'),
        ('DL', 'Driver\'s License'),
        ('ID_CARD', 'Other ID Card'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    experience_years = models.IntegerField()
    workshop_address = models.TextField()
    available = models.BooleanField(default=True)
    latitude = models.FloatField(null=True, blank=True)
    mechanic_id_proof_type = models.CharField(max_length=20, choices=ID_PROOF_CHOICES, blank=True, null=True)
    mechanic_id_proof_number = models.CharField(max_length=50, blank=True, null=True)
    mechanic_id_proof_image = models.ImageField(upload_to='mechanic_id_proofs/', null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    rating = models.FloatField(default=0.0)
    base_fee = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en') # New field

    def __str__(self):
        return f"{self.user.username} - {self.specialization}"

class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mechanic = models.ForeignKey(Mechanic, on_delete=models.SET_NULL, null=True)
    vehicle = models.ForeignKey('Vehicle', on_delete=models.SET_NULL, null=True, related_name='service_requests')
    vehicle_type = models.CharField(max_length=50)
    issue_description = models.TextField()
    issue_image = models.ImageField(upload_to='issue_images/', null=True, blank=True)
    issue_video = models.FileField(upload_to='issue_videos/', null=True, blank=True)
    issue_file = models.FileField(upload_to='issue_files/', null=True, blank=True) # New field for general file uploads
    location = models.TextField()
    latitude = models.FloatField(null=True, blank=True) # Made nullable
    longitude = models.FloatField(null=True, blank=True) # Made nullable
    mechanic_latitude = models.FloatField(null=True, blank=True)
    mechanic_longitude = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    distance_km = models.FloatField(null=True, blank=True, help_text="Calculated distance between user and mechanic in kilometers")
    problem_complexity_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Fee based on problem description complexity")
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'COMPLETED' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    def mark_as_completed(self):
        if self.status != 'COMPLETED':
            self.status = 'COMPLETED'
            self.completed_at = timezone.now()
            
            # Calculate payment details preferring final or estimated cost
            base_amount = (
                self.final_cost if self.final_cost is not None
                else (self.estimated_cost if self.estimated_cost is not None else self.calculate_service_charge())
            )
            service_charge = Decimal(base_amount)
            tax = self.calculate_tax(service_charge)
            total_amount = service_charge + tax
            mechanic_share = self.calculate_mechanic_share(service_charge)
            platform_fee = service_charge - mechanic_share

            # Create or update payment record to avoid duplication
            Payment.objects.update_or_create(
                service_request=self,
                defaults={
                    'amount': service_charge,
                    'service_charge': service_charge,
                    'tax': tax,
                    'total_amount': total_amount,
                    'mechanic_share': mechanic_share,
                    'platform_fee': platform_fee,
                }
            )
            self.save()

    def calculate_service_charge(self):
        base_charge = Decimal('500.00')  # Minimum service charge

        # 1. Distance-based pricing
        distance_fee = Decimal('0.00')
        # Only calculate distance if both user and mechanic locations are available
        if all([self.latitude, self.longitude, self.mechanic_latitude, self.mechanic_longitude]):
            user_location = (self.latitude, self.longitude)
            mechanic_location = (self.mechanic_latitude, self.mechanic_longitude)
            distance = geodesic(user_location, mechanic_location).km
            self.distance_km = round(distance, 2) # Store calculated distance
            if distance > 10: # Example: charge for distances over 10 km
                distance_fee = Decimal(str(max(0, distance - 10) * 10)) # 10 Rs per km after 10 km
        else:
            self.distance_km = 0.0 # No mechanic assigned or location missing, so distance is 0

        # 2. Problem description-based pricing (simplified for demonstration)
        problem_fee = Decimal('0.00')
        if self.issue_description:
            description_length = len(self.issue_description.split())
            if description_length > 50:
                problem_fee = Decimal('200.00') # More complex issue
            elif description_length > 20:
                problem_fee = Decimal('100.00') # Moderately complex issue
            
            # Example: keyword-based complexity
            keywords = ['engine failure', 'transmission', 'major repair', 'electrical fault']
            if any(keyword in self.issue_description.lower() for keyword in keywords):
                problem_fee += Decimal('300.00') # Additional charge for specific keywords
        
        self.problem_complexity_fee = problem_fee # Store calculated problem fee

        total_charge = base_charge + distance_fee + problem_fee
        return total_charge

    def calculate_tax(self, amount):
        # 18% GST
        return Decimal(amount) * Decimal('0.18')

    def calculate_mechanic_share(self, amount):
        # Mechanic gets 80% of the service charge
        return Decimal(amount) * Decimal('0.80')

class Review(models.Model):
    service_request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded')
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('UPI', 'UPI'),
        ('CARD', 'Card'),
        ('NET_BANKING', 'Net Banking')
    ]

    service_request = models.OneToOneField('ServiceRequest', on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    mechanic_share = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    payment_proof = models.ImageField(upload_to='payment_proofs/', null=True, blank=True)
    
    paid_at = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refund_reason = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Service #{self.service_request.id}"

    class Meta:
        ordering = ['-created_at']

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('car', 'Car'),
        ('motorcycle', 'Motorcycle'),
        ('truck', 'Truck'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles')
    name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()
    license_plate = models.CharField(max_length=20, unique=True)
    image = models.ImageField(upload_to='vehicle_images/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    mileage = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.license_plate}"

    @property
    def service_count(self):
        return self.service_requests.all().count()

    @property
    def active_issues(self):
        return self.service_requests.filter(status__in=['PENDING', 'IN_PROGRESS']).count()

    @property
    def last_service(self):
        return self.service_requests.filter(status='COMPLETED').order_by('-created_at').first()

class LocationHistory(models.Model):
    mechanic = models.ForeignKey(Mechanic, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mechanic.user.username} at {self.timestamp}"
