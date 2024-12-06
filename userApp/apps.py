from django.apps import AppConfig

class YourAppConfig(AppConfig):
    name = 'userApp'

    def ready(self):
        import userApp.signals  # Ensure signals are connected when app is ready
