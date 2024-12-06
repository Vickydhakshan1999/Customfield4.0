from django.urls import path
from rest_framework.routers import DefaultRouter

from .auth import LoginView, ForgotPasswordView, ResetPasswordView, UserOnboardView
from .views import PlatformUser, PlatformUserCustomField, assign_permission_to_group, create_group, create_permission



router = DefaultRouter()
router.register(r"platform/users/custom-fields",PlatformUserCustomField,basename="platform.user.custom-fields")
router.register(r"platform/users", PlatformUser, basename="platform.user")

urlpatterns = [
    path('loginfun/', LoginView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<str:uidb64>/<str:token>/', ResetPasswordView.as_view(), name='reset-password'),
    path('tenant-free-onboard/', UserOnboardView.as_view(), name='tenant-free-onboard'),

    path('groups/create/', create_group, name='create_group'),
    path('permissions/create/',create_permission, name='create_permission'),
    path('permissions/assign/',assign_permission_to_group, name='assign_permission_to_group'),
]

urlpatterns += router.urls
