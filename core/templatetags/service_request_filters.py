from django import template

register = template.Library()

@register.filter
def completed_count(queryset):
    """Count completed service requests."""
    return queryset.filter(status='COMPLETED').count()

@register.filter
def in_progress_count(queryset):
    """Count in-progress service requests."""
    return queryset.filter(status__in=['PENDING', 'IN_PROGRESS']).count()

@register.filter
def div(value, arg):
    """Divides the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
