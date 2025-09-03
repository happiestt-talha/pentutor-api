from django.urls import path
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    UserLogoutView,
    EmailVerificationView,
    AdminUserListView,
    AdminRoleUpdateView,
    ResendVerificationEmailView,
    ProfileUpdateView,
    CreateStudentProfileView,
    CreateTeacherProfileView,
    StudentQueryView
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile-update'),
    path('verify-email/<str:token>/', EmailVerificationView.as_view(), name='verify-email'),
    path('resend-verification/', ResendVerificationEmailView.as_view(), name='resend-verification'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<uuid:user_id>/role/', AdminRoleUpdateView.as_view(), name='admin-role-update'),

    # request for teacher/studnet
    path('student-profile/create/', CreateStudentProfileView.as_view(), name='create-student-profile'),
    path('teacher-profile/create/', CreateTeacherProfileView.as_view(), name='create-teacher-profile'),

    path('student-query/', StudentQueryView.as_view(), name='student-query'),
]
