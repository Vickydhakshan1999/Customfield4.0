from auditlog.registry import auditlog 
from django.db import models
from django.contrib.auth.models import Group

from django_access_point.models.user import TenantBase, UserBase
from django_access_point.models.custom_field import CustomFieldBase, CustomFieldOptionsBase, CustomFieldValueBase
from simple_history.models import HistoricalRecords


class Tenant(TenantBase):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=200, blank=True)


class User(UserBase):
    phone_no = models.CharField(max_length=100)
    groups = models.ManyToManyField(Group, related_name='user_groups', blank=True)
    history = HistoricalRecords()


class UserCustomField(CustomFieldBase):
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, null=True, default=None
    )

class UserCustomFieldOptions(CustomFieldOptionsBase):
    custom_field = models.ForeignKey(UserCustomField, on_delete=models.CASCADE)


class UserCustomFieldValue(CustomFieldValueBase):
    submission = models.ForeignKey(User, related_name="custom_field_values", on_delete=models.CASCADE)
    custom_field = models.ForeignKey(UserCustomField, on_delete=models.CASCADE)



from django.db import models
from django.contrib.auth import get_user_model

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        
    ]

    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=255)
    object_id = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)  # To store additional details about the action
        

    def __str__(self):
        return f"{self.user} {self.action} {self.model_name} at {self.timestamp}"
    
    def store_changes(self, old_obj, new_obj):
        """
        This method compares the old and new object and stores the changes in a JSON format.
        """
        changes = {}

        for field in old_obj._meta.fields:
            field_name = field.name
            old_value = getattr(old_obj, field_name, None)
            new_value = getattr(new_obj, field_name, None)

            if old_value != new_value:
                changes[field_name] = [old_value, new_value]

        return changes


# auditlog.register(User)