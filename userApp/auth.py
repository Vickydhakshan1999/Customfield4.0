from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from django_access_point.models.user import TENANT_STATUS_CHOICES
from django_access_point.serializers.auth import (
    LoginSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    UserOnboardSerializer,
)
from django_access_point.utils_response import (
    success_response,
    validation_error_response,
    error_response,
    notfound_response,
)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            if user is None:
                return error_response("Invalid credentials.")
            elif not user.is_user_active():
                return error_response("You don't have access to the application. Please contact admin.")
            elif hasattr(user, "tenant") and user.tenant:
                tenant = user.tenant
                if tenant.status != TENANT_STATUS_CHOICES[1][0]:
                    return error_response("You don't have access to the application. Please contact admin.")

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Send tokens as response
            return success_response(
                {"refresh_token": str(refresh), "access_token": str(access_token)}
            )

        return validation_error_response(serializer.errors)


class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Fetch the user
        email = serializer.validated_data["email"]
        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            return notfound_response("User not found.")

        # Generate password reset token
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(user.pk.encode())

        # Send password reset link via email
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uidb64}/{token}"

        # Prepare the email context
        context = {
            "user": user,
            "reset_url": reset_url,
            "support_email": settings.FRONTEND_URL,
            "platform_name": settings.PLATFORM_NAME,
            "logo_url": settings.PLATFORM_LOGO_URL,
        }

        # Render the email content (HTML)
        subject = "Reset Your Password"
        message = render_to_string("password_reset_email.html", context)

        # Send the email
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=message,  # Ensure HTML is sent
        )

        return success_response("Password reset email sent.")


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token, *args, **kwargs):
        try:
            # Decode user ID
            uid = urlsafe_base64_decode(uidb64).decode()
            user = get_user_model().objects.get(pk=uid)
        except (ValueError, TypeError, get_user_model().DoesNotExist):
            return error_response("Invalid link.")

        # Validate token
        if not default_token_generator.check_token(user, token):
            return error_response("Invalid or expired token.")

        # Validate and set new password
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data["new_password"]

        user.set_password(new_password)
        user.save()

        return success_response("Password successfully reset.")


class UserOnboardView(generics.GenericAPIView):
    serializer_class = UserOnboardSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            return success_response(
                {"user": {"email": user.email, "tenant": user.tenant.name}}
            )

        return validation_error_response(serializer.errors)
