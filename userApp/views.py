from venv import create
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from rest_framework.decorators import action

from django_access_point.models.custom_field import CUSTOM_FIELD_STATUS
from django_access_point.models.user import USER_TYPE_CHOICES, USER_STATUS_CHOICES
from django_access_point.views.custom_field import CustomFieldViewSet
from django_access_point.views.crud import CrudViewSet
from django_access_point.views.helpers_crud import (custom_field_values_related_name, _get_custom_field_queryset,
                                                     _prefetch_custom_field_values, _format_custom_field_submitted_values)
from django_access_point.utils import generate_invite_token_with_expiry, validate_invite_token
from django_access_point.utils_response import success_response, validation_error_response
from django_access_point.excel_report import ExcelReportGenerator

# from Custom.userApp.utils import log_audit
from .utils import log_audit

from .models import User, UserCustomField, UserCustomFieldOptions, UserCustomFieldValue
from .serializers import UserSerializer, UserCustomFieldSerializer

from django.contrib.auth.models import Group
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class PlatformUser(CrudViewSet):
    queryset = get_user_model().objects.filter(user_type=USER_TYPE_CHOICES[0][0]).exclude(
        status=USER_STATUS_CHOICES[0][0])
    list_fields = {"id": "ID", "name": "Name", "email": "Email Address", "phone_no": "phone_no"}
    list_search_fields = ["name", "email", "phone_no"]
    serializer_class = UserSerializer
    custom_field_model = UserCustomField
    custom_field_value_model = UserCustomFieldValue
    custom_field_options_model = UserCustomFieldOptions

    @action(detail=False, methods=['post'], url_path='complete-profile-setup/(?P<token_payload>.+)')
    def complete_profile_setup(self, request, token_payload, *args, **kwargs):
        """
        Complete Profile Setup with a token that includes expiry time.
        """
        # Validate the invite token
        is_valid, user, message = validate_invite_token(token_payload)

        if not is_valid:
            return validation_error_response(message)

        # Proceed with the profile setup process (e.g., update password, etc.)
        password = request.data.get('password')
        if password:
            user.set_password(password)
            user.save()
        # Log the completion of the profile setup (audit log)
        log_audit(
            user=request.user,  
            action='UPDATE',     
            model_name='User',   
            object_id=user.id,   
            details=f"Completed profile setup for {user.name}"  # Details of the action
        )
        return success_response("Profile setup completed successfully.")

    @action(detail=False, methods=['post'], url_path='generate-user-report')
    def generate_user_report(self, request, *args, **kwargs):
        """
        Generate User Report.
        """
        # Queryset to fetch active platform users
        users_queryset = self.queryset.order_by("-created_at")
        # Get User Custom Fields
        active_custom_fields = _get_custom_field_queryset(self.custom_field_model)

        # PreFetch User Custom Field Values
        users_queryset = _prefetch_custom_field_values(
            users_queryset, active_custom_fields, self.custom_field_value_model
        )

        def get_headers():
            headers = ["Name", "Email Address"]

            # Custom Field Headers
            for field in active_custom_fields:
                headers.append(field.label)

            return headers

        # Define row data for each user, including custom fields
        def get_row_data(user):
            row = [user.name, user.email]

            # Custom Field Values
            if active_custom_fields:
                if hasattr(user, custom_field_values_related_name):
                    custom_field_submitted_values = getattr(user, custom_field_values_related_name).all()
                    formatted_custom_field_submitted_values = _format_custom_field_submitted_values(
                        custom_field_submitted_values
                    )

                    # Append each custom field value to the row
                    for field in active_custom_fields:
                        row.append(formatted_custom_field_submitted_values.get(field.id, ""))

            return row

        # Create Excel report generator instance
        report_generator = ExcelReportGenerator(
            title="User Report",
            queryset=users_queryset,
            get_headers=get_headers,
            get_row_data=get_row_data
        )

        # Generate and return the report as an HTTP response
        return report_generator.generate_report()
     

    def after_save(self, request, instance):
        """
        Handle after save.
        """ 
        log_audit(
            user=instance,  
            action="CREATE",    
            model_name='User',  
            object_id=instance.id, 
            details=f"Created user {instance.name}"  
        )
        # After user saved, invite user to setup profile
        self.send_invite_user_email(instance)

    def send_invite_user_email(self, user):
        """
        Send the invitation email to the user with a unique token and expiry time encoded.
        """
        name = user.name
        email = user.email

        # Generate the token and encoded user ID with expiry time
        token_payload = generate_invite_token_with_expiry(user, 1)

        # Build the invite URL with the token_payload (no expiry time in the URL)
        invite_url = f"{settings.FRONTEND_URL}/profile-setup/{token_payload}/"

        # Prepare the email context
        context = {
            "user_name": name,
            "invite_url": invite_url,
            "support_email": settings.PLATFORM_SUPPORT_EMAIL,
            "platform_name": settings.PLATFORM_NAME,
            "logo_url": settings.PLATFORM_LOGO_URL,
        }

        # Render the email content (HTML)
        subject = "Invitation to Complete Your Profile"
        message = render_to_string("profile_invite_email.html", context)

        # Send the email
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=message,  # Ensure HTML is sent
        )

        return success_response("Invitation email sent.")
    
# Create a new group
@api_view(['POST'])

def create_group(request):
    """
    This view allows the creation of a new group.
    """
    group_name = request.data.get('name', None)
    if not group_name:
        return Response({'detail': 'Group name is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Create the group
    group = Group.objects.create(name=group_name)
    
    return Response({'detail': f'Group "{group_name}" created successfully.'}, status=status.HTTP_201_CREATED)



class PlatformUserCustomField(CustomFieldViewSet):
    queryset = UserCustomField.objects.filter(status=CUSTOM_FIELD_STATUS[1][0]).order_by("field_order")
    serializer_class = UserCustomFieldSerializer
    custom_field_options_model = UserCustomFieldOptions


# Create a new permission (only for authenticated users)
@api_view(['POST'])
# @permission_classes([IsAuthenticated])
def create_permission(request):
    name = request.data.get('name')
    codename = request.data.get('codename')
    app_label = request.data.get('app_label')
    model_name = request.data.get('model_name')
    
    if not all([name, codename, model_name]):
        return Response(
            {'detail': 'Name, codename, and model_name are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        permission = Permission.objects.create(
            name=name,
            codename=codename,
            content_type=content_type
        )
        return Response(
            {'detail': f'Permission "{name}" created successfully.'},
            status=status.HTTP_201_CREATED 
        )
    except ContentType.DoesNotExist:
        return Response(
            {'detail': f'Model "{model_name}" does not exist.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
# maping permission to group
# 

@api_view(['POST'])
def assign_permission_to_group(request):
    # Get group_name and permission_codenames from the form data
    group_name = request.data.get('group_name')
    permission_codenames = request.data.getlist('permission_codenames')

    # Validate input
    if not group_name or not permission_codenames:
        return Response(
            {'detail': 'Group name and permission codenames are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if isinstance(permission_codenames[0], str):
        permission_codenames = permission_codenames[0].strip('[]').replace(' ', '').split(',')


    try:
        # Get the group by name
        group = Group.objects.get(name=group_name)
        print(permission_codenames)

        # Fetch permissions based on the codenames
        permissions = Permission.objects.filter(codename__in=permission_codenames)

        # Validate that all requested permissions exist
        if len(permissions) != len(permission_codenames):
            missing_permissions = set(permission_codenames) - set(permissions.values_list('codename', flat=True))
            return Response(
                {'detail': f'The following permissions do not exist: {", ".join(missing_permissions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Add permissions to the group
        group.permissions.add(*permissions)

        return Response(
            {'detail': f'Permissions {permission_codenames} added to group "{group_name}" successfully.'},
            status=status.HTTP_200_OK
        )
    except Group.DoesNotExist:
        return Response(
            {'detail': f'Group "{group_name}" does not exist.'},
            status=status.HTTP_400_BAD_REQUEST
        )       


# mapping user to group
@api_view(['POST'])
# @permission_classes([IsAuthenticated])  # Ensure only authenticated users can use this
def assign_user_to_group(request):
    user_id = request.data.get('user_id')  # User ID to map
    group_name = request.data.get('group_name')  # Group to assign the user to
    
    if not all([user_id, group_name]):
        return Response({'detail': 'user_id and group_name are required.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)  # Get the user by ID
        group = Group.objects.get(name=group_name)  # Get the group by name

        # Add the user to the group
        user.groups.add(group)
        return Response({'detail': f'User "{user.phone_no}" assigned to group "{group_name}" successfully.'}, 
                        status=status.HTTP_200_OK)
    
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    except Group.DoesNotExist:
        return Response({'detail': 'Group not found.'}, status=status.HTTP_404_NOT_FOUND)

