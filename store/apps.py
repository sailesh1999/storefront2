from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'

    # This method is called when this app is ready
    def ready(self):
        import store.signals.handlers