from django.urls import path
from . import views, notification_views
from django.contrib.auth import views as auth_views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register_user, name='register'),
    path('register/mechanic/', views.register_mechanic, name='register_mechanic'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:login'), name='logout'),
    
    # Service Request URLs
    path('service-requests/', views.service_requests, name='service_requests'),
    path('service-request/create/', views.create_service_request, name='create_service_request'),
    path('service-request/<int:pk>/', views.service_request_detail, name='service_request_detail'),
    path('service-request/<int:service_request_id>/review/', views.submit_review, name='submit_review'),
    path('service-request/<int:service_request_id>/nearby-mechanics/', views.find_nearby_mechanics, name='find_nearby_mechanics'),
    path('notifications/', notification_views.notifications_list, name='notifications'),
    path('notifications/<int:notification_id>/mark-read/', notification_views.mark_notification_read, name='mark_notification_read'),
    
    # Password Reset URLs
    path('password-reset/',
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),
    
    # Service History URLs
    path('service-history/', views.service_history, name='service_history'),
    path('vehicles/', views.vehicles, name='vehicles'),
    path('profile/', views.profile, name='profile'),
    
    # API Endpoints
    path('api/emergency/create/', views.create_emergency_request, name='create_emergency_request'),
    path('api/emergency/<int:emergency_request_id>/accept/', views.accept_emergency_request, name='accept_emergency_request'), # New API endpoint
    path('api/mechanic/update-availability/', views.update_mechanic_availability, name='update_mechanic_availability'),
    path('api/mechanic/update-location/', views.update_mechanic_location, name='update_mechanic_location'),
    path('api/service-request/<int:service_request_id>/mechanic-location/', views.get_mechanic_location_for_service_request, name='get_mechanic_location_for_service_request'),
    
    # Mechanic Dashboard
    path('schedule/', views.mechanic_schedule, name='schedule'),
    path('earnings/', views.mechanic_earnings, name='earnings'),
    path('reviews/', views.mechanic_reviews, name='reviews'),

    path('service/<int:service_id>/payment/', views.service_payment, name='service_payment'),
    path('payment/<int:payment_id>/confirm-cash/', views.confirm_cash_payment, name='confirm_cash_payment'),
    path('payment/<int:payment_id>/receipt/', views.payment_receipt, name='payment_receipt'),
    path('service/<int:service_id>/payment-gateway/', views.payment_gateway, name='payment_gateway'),
    path('service/<int:service_id>/process-payment/', views.process_payment, name='process_payment'),
    path('service-request/<int:service_request_id>/assign-mechanic/<int:mechanic_id>/', views.assign_mechanic, name='assign_mechanic'),
]
