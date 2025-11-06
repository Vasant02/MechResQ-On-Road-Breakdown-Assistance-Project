from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Sum, Count
from django.db.models.functions import TruncDay
from .models import User, Mechanic, ServiceRequest, Review, Payment, Notification, Vehicle, EmergencyRequest
from django.contrib.auth.forms import UserCreationForm
from django import forms
from math import radians, sin, cos, sqrt, atan2
from .notification_views import get_unread_notifications_count
from django.template.context_processors import request
from .forms import ReviewForm
from django.conf import settings
from django.http import JsonResponse
import json
from django.db import models
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from django.views.decorators.csrf import csrf_exempt # Added import for csrf_exempt
import googlemaps # Import googlemaps library

def notification_context_processor(request):
    if request.user.is_authenticated:
        return {'unread_notifications_count': get_unread_notifications_count(request.user)}
    return {'unread_notifications_count': 0}

@login_required
@csrf_exempt
def create_emergency_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            if not latitude or not longitude:
                return JsonResponse({'success': False, 'error': 'Location data missing.'}, status=400)

            # Create the emergency request
            emergency_request = EmergencyRequest.objects.create(
                user=request.user,
                latitude=latitude,
                longitude=longitude,
                status='PENDING'
            )

            # Find nearby mechanics (within a certain radius, e.g., 50 km)
            nearby_mechanics = []
            all_mechanics = Mechanic.objects.filter(available=True)
            user_location = (latitude, longitude)

            for mechanic in all_mechanics:
                if mechanic.latitude and mechanic.longitude:
                    mechanic_location = (mechanic.latitude, mechanic.longitude)
                    distance = geodesic(user_location, mechanic_location).km
                    if distance <= 50:  # 50 km radius
                        nearby_mechanics.append(mechanic)
                        
                        # Create notification for nearby mechanic
                        Notification.objects.create(
                            recipient=mechanic.user,
                            notification_type='EMERGENCY',
                            title=f"New Emergency Request from {request.user.username}",
                            message=f"An emergency request has been placed at {latitude}, {longitude}. Distance: {round(distance, 2)} km."
                        )
            
            if not nearby_mechanics:
                # Notify user if no mechanics are found
                Notification.objects.create(
                    recipient=request.user,
                    notification_type='STATUS_UPDATE',
                    title="Emergency Request Received",
                    message="Your emergency request has been received, but no nearby mechanics are currently available. We are expanding our search."
                )
                return JsonResponse({'success': True, 'message': 'Emergency request created. No nearby mechanics found yet.'})

            return JsonResponse({'success': True, 'message': 'Emergency request created and nearby mechanics notified.'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

class UserRegistrationForm(UserCreationForm):
    phone_number = forms.CharField(max_length=17)
    address = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'address', 'password1', 'password2']

class MechanicRegistrationForm(forms.ModelForm):
    class Meta:
        model = Mechanic
        fields = ['specialization', 'experience_years', 'workshop_address', 'latitude', 'longitude']

from .forms import ServiceRequestForm as CoreServiceRequestForm # Rename to avoid conflict

class ServiceRequestForm(CoreServiceRequestForm): # Use the form from forms.py
    class Meta(CoreServiceRequestForm.Meta):
        fields = ['vehicle_type', 'issue_description', 'issue_image', 'issue_video', 'issue_file', 'location', 'latitude', 'longitude']

def register_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.phone_number = form.cleaned_data['phone_number']
            user.address = form.cleaned_data['address']
            user.save()
            messages.success(request, 'Registration successful! Please login to continue.')
            return redirect('core:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

def register_mechanic(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        mechanic_form = MechanicRegistrationForm(request.POST)
        if user_form.is_valid() and mechanic_form.is_valid():
            user = user_form.save(commit=False)
            user.is_mechanic = True
            user.save()
            mechanic = mechanic_form.save(commit=False)
            mechanic.user = user
            mechanic.save()
            messages.success(request, 'Mechanic registration successful! Please login to continue.')
            return redirect('core:login')
        else:
            # Show user form errors
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f'User {field}: {error}')
            # Show mechanic form errors
            for field, errors in mechanic_form.errors.items():
                for error in errors:
                    messages.error(request, f'Mechanic {field}: {error}')
    else:
        user_form = UserRegistrationForm()
        mechanic_form = MechanicRegistrationForm()
    return render(request, 'registration/register_mechanic.html', {
        'user_form': user_form,
        'mechanic_form': mechanic_form
    })

@login_required
def create_service_request(request):
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, request.FILES)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.user = request.user
            
            # Calculate estimated cost
            mechanic = Mechanic.objects.filter(available=True).first() # Find an available mechanic
            if mechanic:
                base_fee = mechanic.base_fee
                issue_length = len(service_request.issue_description.split())
                estimated_cost = base_fee + (issue_length * 2) # Add Rs.2 for each word in the issue description
                service_request.estimated_cost = estimated_cost
            
            service_request.save()
            messages.success(request, f'Service request created successfully! The estimated cost is Rs.{service_request.estimated_cost}.')
            return redirect('core:service_request_detail', pk=service_request.pk)
    else:
        form = ServiceRequestForm()
    
    context = {
        'form': form,
        'active_page': 'new_request',
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    }
    return render(request, 'service_request/create.html', context)

@login_required
def dashboard(request):
    if request.user.is_mechanic:
        mechanic = get_object_or_404(Mechanic, user=request.user)
        service_requests = ServiceRequest.objects.filter(
            Q(mechanic=mechanic) | 
            Q(mechanic__isnull=True, status='PENDING')
        ).order_by('-created_at')
        
        # Calculate additional statistics
        total_services = ServiceRequest.objects.filter(mechanic=mechanic).count()
        completed_services = ServiceRequest.objects.filter(mechanic=mechanic, status='COMPLETED').count()
        in_progress_services = ServiceRequest.objects.filter(mechanic=mechanic, status='IN_PROGRESS').count()
        total_earnings = Payment.objects.filter(service_request__mechanic=mechanic).aggregate(total=Sum('amount'))['total'] or 0
        average_rating = Review.objects.filter(service_request__mechanic=mechanic).aggregate(Avg('rating'))['rating__avg'] or 0
        pending_requests_count = ServiceRequest.objects.filter(mechanic__isnull=True, status='PENDING').count()
        
        # Get emergency requests for the mechanic
        emergency_requests = EmergencyRequest.objects.filter(
            Q(mechanic=mechanic) | Q(mechanic__isnull=True, status='PENDING')
        ).order_by('-created_at')

        # Get last 30 days service trend
        today = timezone.now()
        thirty_days_ago = today - timedelta(days=30)
        service_trend = (
            ServiceRequest.objects
            .filter(mechanic=mechanic, created_at__gte=thirty_days_ago)
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        # Convert service_trend to a list of dictionaries with serializable dates
        service_trend_data = [
            {
                'day': item['day'].strftime('%Y-%m-%d'),
                'count': item['count']
            }
            for item in service_trend
        ]
        
        return render(request, 'dashboard/mechanic.html', {
            'mechanic': mechanic,
            'service_requests': service_requests,
            'emergency_requests': emergency_requests, # Pass emergency requests to template
            'total_services': total_services,
            'completed_services': completed_services,
            'in_progress_services': in_progress_services,
            'total_earnings': total_earnings,
            'average_rating': average_rating,
            'service_trend': json.dumps(service_trend_data),
            'pending_requests_count': pending_requests_count,
            'active_page': 'dashboard'
        })
    else:
        service_requests = ServiceRequest.objects.filter(user=request.user).order_by('-created_at')
        emergency_requests = EmergencyRequest.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'dashboard/user.html', {
            'service_requests': service_requests,
            'emergency_requests': emergency_requests, # Pass emergency requests to user dashboard
            'active_page': 'dashboard'
        })

@login_required
def service_request_detail(request, pk):
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    # Check if the user has permission to view this request
    if not (request.user == service_request.user or 
            (hasattr(request.user, 'mechanic') and 
             (service_request.mechanic == request.user.mechanic or service_request.status == 'PENDING'))):
        messages.error(request, 'You do not have permission to view this service request.')
        return redirect('core:dashboard')
    
    if request.user.is_mechanic:
        mechanic = get_object_or_404(Mechanic, user=request.user)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'accept' and service_request.status == 'PENDING':
                service_request.mechanic = mechanic
                service_request.status = 'ACCEPTED'
                # Set mechanic's current location to service request
                service_request.mechanic_latitude = mechanic.latitude
                service_request.mechanic_longitude = mechanic.longitude
                service_request.save()
                Notification.create_status_update_notification(
                    recipient=service_request.user,
                    service_request=service_request
                )
                messages.success(request, 'Service request accepted successfully!')
            
            elif action == 'start' and service_request.status == 'ACCEPTED':
                service_request.status = 'IN_PROGRESS'
                service_request.save()
                Notification.create_status_update_notification(
                    recipient=service_request.user,
                    service_request=service_request
                )
                messages.success(request, 'Service started successfully!')
            
            elif action == 'complete' and service_request.status == 'IN_PROGRESS':
                service_request.mark_as_completed()  # This method will create the payment
                Notification.create_status_update_notification(
                    recipient=service_request.user,
                    service_request=service_request
                )
                # Create payment notification
                Notification.create_payment_notification(
                    recipient=service_request.user,
                    payment=service_request.payment
                )
                messages.success(request, 'Service completed successfully! Payment has been initiated.')
            
            return redirect('core:service_request_detail', pk=service_request.pk)
        
        return render(request, 'service_request/mechanic_detail.html', {
            'service_request': service_request,
            'active_page': 'service_requests',
            'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
        })
    
    # Provide default coordinates if service_request.latitude or longitude are invalid
    default_lat = 20.5937  # Center of India
    default_lng = 78.9629

    # Provide default coordinates if service_request.latitude or longitude are invalid
    default_lat = 20.5937  # Center of India
    default_lng = 78.9629

    # Safely get latitude and longitude, falling back to defaults
    service_lat = default_lat
    if isinstance(service_request.latitude, (int, float)):
        service_lat = service_request.latitude
    elif isinstance(service_request.latitude, str) and service_request.latitude.replace('.', '', 1).isdigit():
        try:
            service_lat = float(service_request.latitude)
        except ValueError:
            pass # Keep default_lat

    service_lng = default_lng
    if isinstance(service_request.longitude, (int, float)):
        service_lng = service_request.longitude
    elif isinstance(service_request.longitude, str) and service_request.longitude.replace('.', '', 1).isdigit():
        try:
            service_lng = float(service_request.longitude)
        except ValueError:
            pass # Keep default_lng

    service_request_data_dict = { # Renamed to avoid confusion with the JSON string
        'id': service_request.id,
        'latitude': service_lat,
        'longitude': service_lng,
        'mechanic_latitude': service_request.mechanic_latitude,
        'mechanic_longitude': service_request.mechanic_longitude,
        'status': service_request.status,
        'mechanic': service_request.mechanic is not None, # Boolean to indicate if mechanic is assigned
        'mechanic_name': service_request.mechanic.user.get_full_name() if service_request.mechanic else None,
    }

    # For regular users, show the normal detail template
    return render(request, 'service_request/detail.html', {
        'service_request': service_request,
        'active_page': 'service_requests',
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'service_request_data_json': json.dumps(service_request_data_dict), # Pass as JSON string
    })

@login_required
def submit_review(request, service_request_id):
    service_request = get_object_or_404(ServiceRequest, pk=service_request_id, user=request.user)
    
    # Check if review already exists
    if Review.objects.filter(service_request=service_request).exists():
        messages.warning(request, 'You have already submitted a review for this service request.')
        return redirect('core:service_request_detail', pk=service_request_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.service_request = service_request
            review.save()
            
            # Update mechanic's rating
            mechanic = service_request.mechanic
            reviews = Review.objects.filter(service_request__mechanic=mechanic)
            avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
            mechanic.rating = round(avg_rating, 2) if avg_rating else 0
            mechanic.save()
            
            messages.success(request, 'Thank you! Your review has been submitted successfully.')
            return redirect('core:service_request_detail', pk=service_request_id)
    else:
        form = ReviewForm()
    
    return render(request, 'service_request/review.html', {
        'service_request': service_request,
        'form': form
    })


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

@login_required
def find_nearby_mechanics(request, service_request_id):
    service_request = get_object_or_404(ServiceRequest, pk=service_request_id)

    # Ensure service request has valid coordinates
    if service_request.latitude is None or service_request.longitude is None:
        messages.error(request, 'Service request location is not valid. Cannot find nearby mechanics.')
        return redirect('core:service_request_detail', pk=service_request_id)

    nearby_mechanics = []
    # Filter mechanics to only include those with valid latitude and longitude
    all_mechanics = Mechanic.objects.filter(available=True, latitude__isnull=False, longitude__isnull=False)
    
    for mechanic in all_mechanics:
        distance = calculate_distance(
            service_request.latitude,
            service_request.longitude,
            mechanic.latitude,
            mechanic.longitude
        )
        if distance <= 50:  # Within 50km radius
            nearby_mechanics.append({
                'mechanic': mechanic,
                'distance': round(distance, 2)
            })
    
    nearby_mechanics.sort(key=lambda x: x['distance'])
    
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
    
    # Define types of places to search for
    place_types = ['gas_station', 'car_repair', 'car_dealer'] # Petrol bunks, automobile shops, towing services (car_repair/car_dealer for shops, towing not a direct type, but car_repair is close)
    
    nearby_places = []
    for place_type in place_types:
        places_result = gmaps.places_nearby(
            location=(service_request.latitude, service_request.longitude),
            radius=50000, # 50 km radius
            type=place_type
        )
        for place in places_result.get('results', []):
            # Filter out places without location or name
            if 'geometry' in place and 'location' in place['geometry'] and 'name' in place:
                nearby_places.append({
                    'name': place['name'],
                    'lat': place['geometry']['location']['lat'],
                    'lng': place['geometry']['location']['lng'],
                    'type': place_type.replace('_', ' ').title(), # Format type for display
                    'rating': place.get('rating', 'N/A'),
                    'vicinity': place.get('vicinity', 'N/A')
                })

    # Prepare mechanics data for JavaScript
    mechanics_json = json.dumps([
        {
            'lat': float(m['mechanic'].latitude),
            'lng': float(m['mechanic'].longitude),
            'name': m['mechanic'].user.get_full_name(),
            'specialization': m['mechanic'].specialization,
            'distance': m['distance']
        } for m in nearby_mechanics
    ])

    # Prepare nearby places data for JavaScript
    places_json = json.dumps(nearby_places)

    return render(request, 'service_request/nearby_mechanics.html', {
        'service_request': service_request,
        'nearby_mechanics': nearby_mechanics, # Keep for Django template rendering
        'mechanics_json': mechanics_json,
        'places_json': places_json, # New: Pass nearby places data
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })

@login_required
def service_history(request):
    if request.user.is_mechanic:
        # Get all service requests for the mechanic
        service_requests = ServiceRequest.objects.filter(
            mechanic=request.user.mechanic
        ).select_related('user', 'vehicle').order_by('-created_at')
        
        return render(request, 'service/mechanic_history.html', {
            'service_requests': service_requests,
            'active_page': 'history',
            'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY # Pass API key
        })
    else:
        # Get all service requests for the regular user
        service_requests = ServiceRequest.objects.filter(
            user=request.user
        ).order_by('-created_at')
        
        return render(request, 'service/history.html', {
            'service_requests': service_requests,
            'active_page': 'history',
            'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY # Pass API key
        })

@login_required
def vehicles(request):
    if request.method == 'POST':
        # Handle vehicle creation
        try:
            vehicle_data = {
                'user': request.user,
                'name': request.POST.get('vehicleName'),
                'vehicle_type': request.POST.get('vehicleType'),
                'make': request.POST.get('make'),
                'model': request.POST.get('model'),
                'year': request.POST.get('year'),
                'license_plate': request.POST.get('licensePlate'),
            }
            
            # Handle image upload
            if 'vehicleImage' in request.FILES:
                vehicle_data['image'] = request.FILES['vehicleImage']
            
            vehicle = Vehicle.objects.create(**vehicle_data)
            messages.success(request, 'Vehicle added successfully!')
            return redirect('core:vehicles')
        except Exception as e:
            messages.error(request, f'Error adding vehicle: {str(e)}')
            return redirect('core:vehicles')
    
    # Get all vehicles for the current user
    vehicles = Vehicle.objects.filter(user=request.user)
    return render(request, 'vehicles/index.html', {
        'vehicles': vehicles,
        'active_page': 'vehicles'
    })

@login_required
def profile(request):
    if request.method == 'POST':
        try:
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.phone_number = request.POST.get('phone_number', user.phone_number)
            user.address = request.POST.get('address', user.address)
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                user.profile_picture = request.FILES['profile_picture']
            
            user.save()

            # Update mechanic-specific fields if user is a mechanic
            if user.is_mechanic:
                mechanic = user.mechanic
                mechanic.specialization = request.POST.get('specialization', mechanic.specialization)
                mechanic.experience_years = request.POST.get('experience_years', mechanic.experience_years)
                mechanic.workshop_address = request.POST.get('workshop_address', mechanic.workshop_address)
                mechanic.latitude = request.POST.get('latitude', mechanic.latitude)
                mechanic.longitude = request.POST.get('longitude', mechanic.longitude)
                mechanic.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            return redirect('core:profile')
    
    if request.user.is_mechanic:
        return render(request, 'profile/mechanic_profile.html', {
            'user': request.user,
            'mechanic': request.user.mechanic,
            'active_page': 'profile',
            'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
        })
    
    return render(request, 'profile/index.html', {
        'user': request.user,
        'active_page': 'profile'
    })

@login_required
def service_requests(request):
    if not hasattr(request.user, 'mechanic'):
        return redirect('core:dashboard')
    
    pending_requests = ServiceRequest.objects.filter(status='PENDING')
    active_requests = ServiceRequest.objects.filter(mechanic=request.user.mechanic).exclude(status='COMPLETED')
    pending_requests_count = pending_requests.count()
    
    context = {
        'pending_requests': pending_requests,
        'active_requests': active_requests,
        'pending_requests_count': pending_requests_count,
        'active_page': 'service_requests'
    }
    return render(request, 'service_requests/list.html', context)

@login_required
def mechanic_schedule(request):
    if not request.user.is_mechanic:
        return redirect('core:dashboard')
        
    mechanic = request.user.mechanic
    service_requests = ServiceRequest.objects.filter(mechanic=mechanic)
    
    # Format events for the calendar
    events = []
    for service_request in service_requests:
        event = {
            'id': service_request.id,
            'title': f'Service Request #{service_request.id}',
            'start': service_request.scheduled_time.isoformat() if service_request.scheduled_time else service_request.created_at.isoformat(),
            'status': service_request.status,
            'customerName': service_request.user.get_full_name() or service_request.user.username,
            'vehicleInfo': f"{service_request.vehicle.name} - {service_request.vehicle.license_plate}" if service_request.vehicle else service_request.vehicle_type,
            'issueDescription': service_request.issue_description,
            'location': service_request.location
        }
        events.append(event)
    
    context = {
        'events': json.dumps(events),
        'active_page': 'schedule'
    }
    
    return render(request, 'dashboard/schedule.html', context)

@login_required
def mechanic_earnings(request):
    if not request.user.is_mechanic:
        return redirect('core:dashboard')
    
    mechanic = request.user.mechanic
    today = timezone.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get the filter period from query params
    months = request.GET.get('months', 'all')
    if months != 'all':
        months = int(months)
        start_date = today - timezone.timedelta(days=30 * months)
    else:
        start_date = None
    
    # Query payments
    payments_query = Payment.objects.filter(
        service_request__mechanic=mechanic,
        service_request__status='COMPLETED'
    )
    
    if start_date:
        payments_query = payments_query.filter(paid_at__gte=start_date)
    
    payments = payments_query.select_related('service_request', 'service_request__user').order_by('-paid_at')
    
    # Calculate earnings
    total_earnings = payments_query.aggregate(
        total=models.Sum('mechanic_share')
    )['total'] or 0
    
    monthly_earnings = payments_query.filter(
        paid_at__gte=start_of_month
    ).aggregate(
        total=models.Sum('mechanic_share')
    )['total'] or 0
    
    # Get pending payments
    pending_payments = Payment.objects.filter(
        service_request__mechanic=mechanic,
        payment_status='PENDING'
    )
    
    pending_amount = pending_payments.aggregate(
        total=models.Sum('mechanic_share')
    )['total'] or 0
    
    # Calculate completed and pending services
    completed_services = payments_query.filter(
        paid_at__gte=start_of_month
    ).count()
    
    pending_services = pending_payments.count()
    
    # Calculate earnings growth
    last_month_start = start_of_month - timezone.timedelta(days=start_of_month.day)
    last_month_earnings = payments_query.filter(
        paid_at__gte=last_month_start,
        paid_at__lt=start_of_month
    ).aggregate(
        total=models.Sum('mechanic_share')
    )['total'] or 0
    
    if last_month_earnings > 0:
        earnings_growth = ((monthly_earnings - last_month_earnings) / last_month_earnings) * 100
    else:
        earnings_growth = 100 if monthly_earnings > 0 else 0
    
    # Prepare chart data
    last_6_months = []
    for i in range(5, -1, -1):
        month_start = (today - timezone.timedelta(days=30 * i)).replace(day=1)
        month_end = (month_start + timezone.timedelta(days=32)).replace(day=1)
        
        month_earnings = payments_query.filter(
            paid_at__gte=month_start,
            paid_at__lt=month_end
        ).aggregate(
            total=models.Sum('mechanic_share')
        )['total'] or 0
        
        last_6_months.append({
            'month': month_start.strftime('%b'),
            'earnings': float(month_earnings)
        })
    
    earnings_data = {
        'labels': [month['month'] for month in last_6_months],
        'values': [month['earnings'] for month in last_6_months]
    }
    
    context = {
        'active_page': 'earnings',
        'total_earnings': total_earnings,
        'monthly_earnings': monthly_earnings,
        'pending_amount': pending_amount,
        'completed_services': completed_services,
        'pending_services': pending_services,
        'earnings_growth': round(earnings_growth, 1),
        'earnings_data': json.dumps(earnings_data),
        'payments': payments
    }
    
    return render(request, 'dashboard/earnings.html', context)

@login_required
def mechanic_reviews(request):
    if not request.user.is_mechanic:
        return redirect('core:dashboard')
    
    # Get reviews through service requests
    reviews = Review.objects.filter(
        service_request__mechanic=request.user.mechanic
    ).order_by('-created_at')
    
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    context = {
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'active_page': 'reviews'
    }
    return render(request, 'dashboard/reviews.html', context)

@login_required
def update_mechanic_availability(request):
    if not hasattr(request.user, 'mechanic'):
        return JsonResponse({'success': False, 'error': 'Not a mechanic'}, status=403)
    
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        available = data.get('available', False)
        
        mechanic = request.user.mechanic
        mechanic.available = available
        mechanic.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def service_payment(request, service_id):
    service_request = get_object_or_404(ServiceRequest, id=service_id)
    payment = get_object_or_404(Payment, service_request=service_request)

    if request.method == 'POST':
        service_charge = float(request.POST.get('service_charge', 0))
        tax = float(request.POST.get('tax', 0))
        total_amount = float(request.POST.get('total_amount', 0))
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id')
        payment_proof = request.FILES.get('payment_proof')

        # Update payment details
        payment.service_charge = service_charge
        payment.tax = tax
        payment.total_amount = total_amount
        payment.payment_method = payment_method
        payment.mechanic_share = service_charge * 0.80  # 80% to mechanic
        payment.platform_fee = service_charge * 0.20    # 20% platform fee

        if payment_method == 'CASH':
            payment.payment_status = 'PENDING'
            messages.info(request, 'Please pay the cash amount to the mechanic. They will confirm once received.')
        else:
            if transaction_id:
                payment.transaction_id = transaction_id
            if payment_proof:
                payment.payment_proof = payment_proof
            payment.payment_status = 'PAID'
            payment.paid_at = timezone.now()
            
            # Notify mechanic about payment completion
            Notification.create_payment_notification(
                recipient=service_request.mechanic.user,
                payment=payment
            )
            messages.success(request, 'Payment completed successfully!')
        
        payment.save()
        return redirect('core:service_request_detail', pk=service_id)

    context = {
        'service_request': service_request,
        'payment': payment,
        'active_page': 'services'
    }
    
    if request.user.is_mechanic:
        return render(request, 'service/mechanic_payment.html', context)
    return render(request, 'service/user_payment.html', context)

@login_required
def confirm_cash_payment(request, payment_id):
    if not request.user.is_mechanic:
        messages.error(request, 'Only mechanics can confirm cash payments.')
        return redirect('core:dashboard')

    payment = get_object_or_404(Payment, id=payment_id)
    service_request = payment.service_request

    if service_request.mechanic.user != request.user:
        messages.error(request, 'You can only confirm payments for your own services.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        payment.payment_status = 'PAID'
        payment.paid_at = timezone.now()
        payment.save()
        
        # Notify user about payment confirmation
        Notification.create_payment_notification(
            recipient=service_request.user,
            payment=payment
        )
        messages.success(request, 'Cash payment confirmed successfully!')
        return redirect('core:service_request_detail', pk=service_request.id)

    return render(request, 'service/confirm_cash_payment.html', {
        'payment': payment,
        'service_request': service_request,
        'active_page': 'services'
    })

@login_required
def payment_receipt(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    service_request = payment.service_request

    # Check if user has permission to view this receipt
    if not (request.user == service_request.user or 
            (hasattr(request.user, 'mechanic') and service_request.mechanic == request.user.mechanic)):
        messages.error(request, 'You do not have permission to view this receipt.')
        return redirect('core:dashboard')

    return render(request, 'service/payment_receipt.html', {
        'payment': payment,
        'service_request': service_request
    })

@login_required
def payment_gateway(request, service_id):
    service_request = get_object_or_404(ServiceRequest, id=service_id)
    payment = get_object_or_404(Payment, service_request=service_request)
    
    if request.method == 'POST':
        context = {
            'service_request': service_request,
            'payment_method': request.POST.get('payment_method'),
            'service_charge': request.POST.get('service_charge'),
            'tax': request.POST.get('tax'),
            'total_amount': request.POST.get('total_amount')
        }
        return render(request, 'service/payment_gateway.html', context)
    
    return redirect('core:service_request_detail', pk=service_id)

@login_required
def process_payment(request, service_id):
    if request.method != 'POST':
        return redirect('core:service_request_detail', pk=service_id)
        
    service_request = get_object_or_404(ServiceRequest, id=service_id)
    payment = get_object_or_404(Payment, service_request=service_request)
    
    # Get payment details from form
    service_charge = float(request.POST.get('service_charge', 0))
    tax = float(request.POST.get('tax', 0))
    total_amount = float(request.POST.get('total_amount', 0))
    payment_method = request.POST.get('payment_method')
    
    # Update payment details
    payment.service_charge = service_charge
    payment.tax = tax
    payment.total_amount = total_amount
    payment.payment_method = payment_method
    payment.mechanic_share = service_charge * 0.80  # 80% to mechanic
    payment.platform_fee = service_charge * 0.20    # 20% platform fee
    
    # For demonstration, we'll generate a random transaction ID
    import random
    import string
    transaction_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    payment.transaction_id = transaction_id
    
    # Mark payment as completed
    payment.payment_status = 'PAID'
    payment.paid_at = timezone.now()
    payment.save()
    
    # Notify mechanic about payment completion
    Notification.create_payment_notification(
        recipient=service_request.mechanic.user,
        payment=payment
    )
    
    messages.success(request, 'Payment processed successfully!')
    return redirect('core:service_request_detail', pk=service_id)

@login_required
def assign_mechanic(request, service_request_id, mechanic_id):
    service_request = get_object_or_404(ServiceRequest, pk=service_request_id)
    mechanic = get_object_or_404(Mechanic, pk=mechanic_id)

    if request.user != service_request.user:
        messages.error(request, 'You do not have permission to assign a mechanic to this request.')
        return redirect('core:dashboard')

    if service_request.status != 'PENDING':
        messages.warning(request, 'This service request is no longer pending.')
        return redirect('core:service_request_detail', pk=service_request_id)

    service_request.mechanic = mechanic
    service_request.status = 'ACCEPTED'
    service_request.save()

    Notification.create_status_update_notification(
        recipient=service_request.user,
        service_request=service_request
    )
    Notification.create_status_update_notification(
        recipient=mechanic.user,
        service_request=service_request
    )
    messages.success(request, f'Mechanic {mechanic.user.get_full_name()} assigned to your request!')
    return redirect('core:service_request_detail', pk=service_request_id)


@login_required
@csrf_exempt
def accept_emergency_request(request, emergency_request_id):
    if request.method == 'POST':
        try:
            emergency_request = get_object_or_404(EmergencyRequest, pk=emergency_request_id)
            mechanic = get_object_or_404(Mechanic, user=request.user)

            if emergency_request.status != 'PENDING':
                return JsonResponse({'success': False, 'error': 'Emergency request is not pending.'}, status=400)

            emergency_request.mechanic = mechanic
            emergency_request.status = 'DISPATCHED'
            emergency_request.save()

            # Notify the user that a mechanic has accepted their request
            Notification.objects.create(
                recipient=emergency_request.user,
                notification_type='STATUS_UPDATE',
                title=f"Emergency Request Accepted by {mechanic.user.username}",
                message=f"Mechanic {mechanic.user.username} is on their way to your emergency location."
            )

            return JsonResponse({'success': True, 'message': 'Emergency request accepted.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)


@login_required
@csrf_exempt
def update_mechanic_location(request):
    if not request.user.is_mechanic:
        return JsonResponse({'success': False, 'error': 'Not a mechanic'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            if latitude is None or longitude is None:
                return JsonResponse({'success': False, 'error': 'Location data missing.'}, status=400)

            mechanic = request.user.mechanic
            mechanic.latitude = latitude
            mechanic.longitude = longitude
            mechanic.save()

            # Save location to history
            LocationHistory.objects.create(
                mechanic=mechanic,
                latitude=latitude,
                longitude=longitude
            )

            # Update active service requests for this mechanic
            active_service_requests = ServiceRequest.objects.filter(
                mechanic=mechanic,
                status__in=['ACCEPTED', 'IN_PROGRESS']
            )
            for sr in active_service_requests:
                sr.mechanic_latitude = latitude
                sr.mechanic_longitude = longitude
                sr.save()

            return JsonResponse({'success': True, 'message': 'Mechanic location updated successfully.'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

@login_required
def get_mechanic_location_for_service_request(request, service_request_id):
    service_request = get_object_or_404(ServiceRequest, pk=service_request_id)

    # Ensure the requesting user is either the service request owner or the assigned mechanic
    if not (request.user == service_request.user or
            (service_request.mechanic and request.user == service_request.mechanic.user)):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    if service_request.mechanic and (service_request.status == 'ACCEPTED' or service_request.status == 'IN_PROGRESS'):
        return JsonResponse({
            'success': True,
            'mechanic_latitude': service_request.mechanic_latitude,
            'mechanic_longitude': service_request.mechanic_longitude,
            'status': service_request.status
        })
    else:
        return JsonResponse({'success': False, 'error': 'Mechanic not assigned or service not in progress.'}, status=404)


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                auth_login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('core:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please enter a correct username and password. Note that both fields may be case-sensitive.')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

from .models import LocationHistory

@login_required
def get_location_history(request, mechanic_id):
    mechanic = get_object_or_404(Mechanic, pk=mechanic_id)
    location_history = LocationHistory.objects.filter(mechanic=mechanic).order_by('-timestamp')
    data = {
        'success': True,
        'location_history': [
            {
                'latitude': lh.latitude,
                'longitude': lh.longitude,
                'timestamp': lh.timestamp.isoformat()
            } for lh in location_history
        ]
    }
    return JsonResponse(data)
