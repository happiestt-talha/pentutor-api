# authentication/serializers.py

import json
import ast
import logging
from typing import Any, Dict

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, StudentProfile, TeacherProfile

logger = logging.getLogger(__name__)


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'age', 'city', 'country', 'gender']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            if not user.is_verified:
                raise serializers.ValidationError('Please verify your email first.')
            attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'age', 'gender', 'city', 'country', 'is_verified', 'created_at']
        read_only_fields = ['id', 'created_at', 'is_verified']


class RoleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['role']


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(required=True)
    skills = serializers.JSONField(required=False)
    interests = serializers.JSONField(required=False)
    certificates = serializers.JSONField(required=False)
    social_links = serializers.JSONField(required=False)
    preferred_learning_time = serializers.JSONField(required=False)
    notification_preferences = serializers.JSONField(required=False)
    language_preferences = serializers.JSONField(required=False)

    class Meta:
        model = StudentProfile
        exclude = ['created_at', 'updated_at', 'is_active']
        read_only_fields = [
            'user', 'email', 'enrollment_number',
            'completed_courses_count', 'current_courses_count',
            'attendance_percentage', 'completed_assignments',
            'average_course_rating'
        ]

    def validate_skills(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Skills must be a list")
        return value

    def validate_interests(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Interests must be a list")
        return value

    def validate_certificates(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Certificates must be a list")
        return value

    def validate_social_links(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Social links must be a dictionary")
        return value

    def validate_preferred_learning_time(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Preferred learning time must be a list")
        return value

    def validate_notification_preferences(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Notification preferences must be a dictionary")
        return value

    def validate_language_preferences(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Language preferences must be a list")
        return value


class TeacherProfileSerializer(serializers.ModelSerializer):
    # Keep user & email read-only (we will attach request.user in the view)
    user = UserSerializer(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(required=True)

    # Structured fields — validate as JSON/list/dict
    expertise_areas = serializers.JSONField(required=True)
    education = serializers.JSONField(required=True)
    certifications = serializers.JSONField(required=False, allow_null=True)
    awards = serializers.JSONField(required=False, allow_null=True)
    publications = serializers.JSONField(required=False, allow_null=True)
    languages_spoken = serializers.JSONField(required=True)
    availability_schedule = serializers.JSONField(required=True)
    preferred_teaching_methods = serializers.JSONField(required=True)
    course_categories = serializers.JSONField(required=True)
    notification_preferences = serializers.JSONField(required=False, allow_null=True)
    social_links = serializers.JSONField(required=False, allow_null=True)

    # Files
    resume = serializers.FileField(required=False, allow_null=True)
    degree_certificates = serializers.FileField(required=False, allow_null=True)
    id_proof = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = TeacherProfile
        exclude = ['created_at', 'updated_at', 'is_active']
        read_only_fields = [
            'user', 'email', 'employee_id',
            'total_courses', 'total_students',
            'average_rating', 'total_course_hours',
            'total_students_helped', 'response_rate',
            'average_response_time'
        ]

    # ---- tolerant JSON parsing for multipart/form-data ----
    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSON-like strings coming from multipart/form-data.
        The frontend sends JSON strings (e.g. "[\"English\",\"Urdu\"]") or
        repeated fields (field[]). This method will try to convert those
        strings into Python lists/dicts so normal validation works.
        """
        # First let DRF parse basic types (files remain in data)
        ret = super().to_internal_value(data)

        json_fields = [
            "expertise_areas",
            "education",
            "certifications",
            "awards",
            "publications",
            "languages_spoken",
            "availability_schedule",
            "preferred_teaching_methods",
            "course_categories",
            "notification_preferences",
            "social_links",
        ]

        for field in json_fields:
            raw_value = data.get(field)

            # Already parsed by parser (list/dict) -> accept as-is
            if isinstance(raw_value, (list, dict)):
                ret[field] = raw_value
                continue

            # Missing or empty -> sensible default
            if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
                if field in ("availability_schedule", "notification_preferences", "social_links"):
                    ret[field] = {}
                else:
                    ret[field] = []
                continue

            # Try JSON decode
            if isinstance(raw_value, str):
                s = raw_value.strip()
                try:
                    parsed = json.loads(s)
                    ret[field] = parsed
                    continue
                except Exception as ex_json:
                    logger.debug("json.loads failed for field=%s raw=%r err=%s", field, raw_value, ex_json)

                # Try ast.literal_eval (handles Python-list like strings)
                try:
                    parsed = ast.literal_eval(s)
                    if isinstance(parsed, (list, dict)):
                        ret[field] = parsed
                        continue
                except Exception:
                    pass

                # Fallback: comma-separated list -> split (for simple list fields)
                if "," in s and field not in ("availability_schedule", "notification_preferences", "social_links", "additional_documents"):
                    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
                    ret[field] = parts
                    continue

                # Last resort: keep raw string (validator will reject if wrong type)
                ret[field] = s
                continue

            # Any other type -> keep and let validators handle
            ret[field] = raw_value

        return ret

    # ---- field-level validators (ensure types) ----
    def validate_expertise_areas(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Expertise areas must be a list")
        return value

    def validate_education(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Education must be a list")
        for edu in value:
            if not isinstance(edu, dict) or not all(k in edu for k in ['degree', 'institution', 'year']):
                raise serializers.ValidationError("Each education entry must contain degree, institution, and year")
        return value

    def validate_certifications(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Certifications must be a list")
        return value

    def validate_awards(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Awards must be a list")
        return value

    def validate_publications(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Publications must be a list")
        return value

    def validate_languages_spoken(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Languages spoken must be a list")
        return value

    def validate_availability_schedule(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Availability schedule must be a dictionary")
        return value

    def validate_preferred_teaching_methods(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Preferred teaching methods must be a list")
        return value

    def validate_course_categories(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Course categories must be a list")
        return value

    def validate_notification_preferences(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Notification preferences must be a dictionary")
        return value

    def validate_social_links(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Social links must be a dictionary")
        return value
