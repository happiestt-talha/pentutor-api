# permissions.py
from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    message = 'Access denied. Teacher privileges required.'

    def has_permission(self, request, view):
        return hasattr(request.user, 'teacher_profile')

