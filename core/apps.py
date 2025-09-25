from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Import template tags when the app is ready
        from django.template.defaulttags import register
        try:
            import core.templatetags.service_request_filters
        except ImportError:
            pass