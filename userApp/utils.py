from .models import AuditLog

def log_audit(action, user, model_name, object_id, details=None):
        """
        Logs an action performed by a user on a specific model.
        """
        # if not user or not user.is_authenticated:
        #     raise ValueError("User must be authenticated to log an action.")

        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            details=details
        )
