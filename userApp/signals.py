from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from .models import User, AuditLog
import json


@receiver(pre_save, sender=User)
def log_user_updates(sender, instance, **kwargs):
    if instance.pk:  # Update operation (object already exists)
        old_obj = sender.objects.get(pk=instance.pk)
        changes = AuditLog().store_changes(old_obj, instance)

        if changes:  # Log changes only if there are any
            audit_log = AuditLog(
                user=instance,
                action='UPDATE',
                model_name=sender.__name__,
                object_id=instance.pk,
                details=json.dumps(changes),
            )
            audit_log.save()


@receiver(post_save, sender=User)
def log_user_creation(sender, instance, created, **kwargs):
    if created:  # Only for newly created instances
        # Log a single "CREATE" entry with relevant details
        audit_log = AuditLog(
            user=instance,
            action='CREATE',
            model_name=sender.__name__,
            object_id=instance.pk,
            details=({'created': f"User {instance} was created."}),
                
        )
        audit_log.save()

@receiver(pre_delete, sender=User)
def log_user_deletion(sender, instance, **kwargs):
    # Capture the details of the deleted user
    audit_log = AuditLog(
        user=instance,
        action='DELETE',
        model_name=sender.__name__,
        object_id=instance.pk,
        details=json.dumps({'deleted': f"User {instance.email} was deleted."}),
    )
    audit_log.save()  # Save the audit log when the user is deleted
