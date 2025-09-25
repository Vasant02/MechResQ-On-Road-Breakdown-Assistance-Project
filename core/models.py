from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from decimal import Decimal

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('SERVICE_REQUEST', 'Service Request'),
        ('STATUS_UPDATE', 'Status Update'),
        ('PAYMENT', 'Payment'),
        ('REVIEW', 'Review'),
        ('EMERGENCY', 'Emergency'), # New notification type
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
        title = f"New Service Request #{service_request.id}"
        message = f"A new service request has been created for {service_request.vehicle_type}."
        return cls.objects.create(
            recipient=recipient,
            notification_type='SERVICE_REQUEST',
            title=title,
            message=message
        )

    @classmethod
    def create_status_update_notification(cls, recipient, service_request):
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
        title = f"Payment Update for Request #{payment.service_request.id}"
        message = f"Payment of ${payment.amount} has been {payment.payment_status}."
        return cls.objects.create(
            recipient=recipient,
            notification_type='PAYMENT',
            title=title,
            message=message
        )

    @classmethod
    def create_review_notification(cls, recipient, review):
        title = f"New Review for Request #{review.service_request.id}"
        message = f"You received a {review.rating}-star review."
        return cls.objects.create(
            recipient=recipient,
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
    
    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        if self.is_mechanic:
            return '/static/images/Mechanic.png'
        return '/static/images/User.png'

class Mechanic(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    experience_years = models.IntegerField()
    workshop_address = models.TextField()
    available = models.BooleanField(default=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    rating = models.FloatField(default=0.0)

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
    latitude = models.FloatField()
    longitude = models.FloatField()
    mechanic_latitude = models.FloatField(null=True, blank=True)
    mechanic_longitude = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.status == 'COMPLETED' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    def mark_as_completed(self):
        if self.status != 'COMPLETED':
            self.status = 'COMPLETED'
            self.completed_at = timezone.now()
            
            # Calculate payment details
            service_charge = self.calculate_service_charge()
            tax = self.calculate_tax(service_charge)
            total_amount = service_charge + tax
            mechanic_share = self.calculate_mechanic_share(service_charge)
            platform_fee = service_charge - mechanic_share

            # Create payment record
            Payment.objects.create(
                service_request=self,
                amount=service_charge,
                service_charge=service_charge,
                tax=tax,
                total_amount=total_amount,
                mechanic_share=mechanic_share,
                platform_fee=platform_fee
            )
            self.save()

    def calculate_service_charge(self):
        # Base charge calculation logic
        base_charge = 500  # Minimum service charge
        if self.issue_description and len(self.issue_description.split()) > 50:
            base_charge += 200  # Additional charge for complex issues
        return Decimal(base_charge)

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

class EmergencyRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('DISPATCHED', 'Dispatched'),
        ('RESOLVED', 'Resolved'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emergency_requests')
    mechanic = models.ForeignKey(Mechanic, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_emergency_requests')
    latitude = models.FloatField()
    longitude = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Emergency Request by {self.user.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
