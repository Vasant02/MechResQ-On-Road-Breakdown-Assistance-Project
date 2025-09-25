from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ServiceRequest, Payment, Review, Notification

@receiver(post_save, sender=ServiceRequest)
def service_request_notification(sender, instance, created, **kwargs):
    if created:
        # Notify mechanics about new service request
        from .models import User
        mechanics = User.objects.filter(is_mechanic=True)
        for mechanic in mechanics:
            Notification.create_service_request_notification(mechanic, instance)
    else:
        # Notify user about status update
        if instance.status != 'PENDING':
            Notification.create_status_update_notification(instance.user, instance)

@receiver(post_save, sender=Payment)
def payment_notification(sender, instance, created, **kwargs):
    if created:
        # Notify both user and mechanic about payment
        Notification.create_payment_notification(instance.service_request.user, instance)
        if instance.service_request.mechanic:
            Notification.create_payment_notification(instance.service_request.mechanic.user, instance)

@receiver(post_save, sender=Review)
def review_notification(sender, instance, created, **kwargs):
    if created and instance.service_request.mechanic:
        # Notify mechanic about new review
        Notification.create_review_notification(instance.service_request.mechanic.user, instance)