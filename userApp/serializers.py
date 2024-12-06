from django_access_point.serializers.crud import CrudSerializer
from django_access_point.serializers.custom_field import CustomFieldSerializer

from .models import User, UserCustomField


class UserCustomFieldSerializer(CustomFieldSerializer):
    class Meta:
        model = UserCustomField
        fields = CustomFieldSerializer.Meta.fields


class UserSerializer(CrudSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "phone_no", "password"]




from rest_framework import serializers
from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'action', 'model_name', 'object_id', 'timestamp', 'details']
