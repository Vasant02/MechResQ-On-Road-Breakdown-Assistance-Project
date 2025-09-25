from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Mechanic, ServiceRequest, Review, Payment, Vehicle, Notification

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['service_request', 'amount', 'payment_status', 'paid_at', 'payment_method']
    list_filter = ['payment_status', 'payment_method', 'created_at']
    search_fields = ['service_request__id', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Service Information', {
            'fields': ('service_request',)
        }),
        ('Payment Details', {
            'fields': (
                'amount', 'service_charge', 'tax', 'total_amount',
                'mechanic_share', 'platform_fee'
            )
        }),
        ('Payment Status', {
            'fields': (
                'payment_status', 'payment_method', 'transaction_id',
                'payment_proof', 'paid_at'
            )
        }),
        ('Refund Information', {
            'fields': ('refund_amount', 'refund_reason'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_mechanic']
    list_filter = ['is_mechanic', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']

@admin.register(Mechanic)
class MechanicAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'experience_years', 'available', 'rating']
    list_filter = ['available', 'specialization']
    search_fields = ['user__username', 'user__email', 'specialization']

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'mechanic', 'vehicle_type', 'status', 'created_at']
    list_filter = ['status', 'vehicle_type', 'created_at']
    search_fields = ['user__username', 'mechanic__user__username', 'issue_description']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['service_request', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['service_request__id', 'comment']

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'vehicle_type', 'license_plate', 'status']
    list_filter = ['vehicle_type', 'status', 'created_at']
    search_fields = ['name', 'license_plate', 'user__username']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'read', 'created_at']
    list_filter = ['notification_type', 'read', 'created_at']
    search_fields = ['recipient__username', 'title', 'message']