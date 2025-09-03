# authentication/serializers.py

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, StudentProfile, TeacherProfile, StudentQuery

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

    # def validate_skills(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Skills must be a list")
    #     return value

    # def validate_interests(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Interests must be a list")
    #     return value

    # def validate_certificates(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Certificates must be a list")
    #     return value

    # def validate_social_links(self, value):
    #     if not isinstance(value, dict):
    #         raise serializers.ValidationError("Social links must be a dictionary")
    #     return value

    # def validate_preferred_learning_time(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Preferred learning time must be a list")
    #     return value

    # def validate_notification_preferences(self, value):
    #     if not isinstance(value, dict):
    #         raise serializers.ValidationError("Notification preferences must be a dictionary")
    #     return value

    # def validate_language_preferences(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Language preferences must be a list")
    #     return value

class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(required=True)
    expertise_areas = serializers.JSONField(required=True)
    education = serializers.JSONField(required=True)
    certifications = serializers.JSONField(required=False)
    awards = serializers.JSONField(required=False)
    publications = serializers.JSONField(required=False)
    languages_spoken = serializers.JSONField(required=True)
    availability_schedule = serializers.JSONField(required=True)
    preferred_teaching_methods = serializers.JSONField(required=True)
    course_categories = serializers.JSONField(required=True)
    notification_preferences = serializers.JSONField(required=False)
    social_links = serializers.JSONField(required=False)
    additional_documents = serializers.JSONField(required=False)
    resume = serializers.FileField(required=False)
    degree_certificates = serializers.FileField(required=False)
    id_proof = serializers.FileField(required=False)

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

    # def validate_expertise_areas(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Expertise areas must be a list")
    #     return value

    # def validate_education(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Education must be a list")
    #     for edu in value:
    #         if not isinstance(edu, dict) or not all(k in edu for k in ['degree', 'institution', 'year']):
    #             raise serializers.ValidationError("Each education entry must contain degree, institution, and year")
    #     return value

    # def validate_certifications(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Certifications must be a list")
    #     return value

    # def validate_awards(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Awards must be a list")
    #     return value

    # def validate_publications(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Publications must be a list")
    #     return value

    # def validate_languages_spoken(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Languages spoken must be a list")
    #     return value

    # def validate_availability_schedule(self, value):
    #     if not isinstance(value, dict):
    #         raise serializers.ValidationError("Availability schedule must be a dictionary")
    #     return value

    # def validate_preferred_teaching_methods(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Preferred teaching methods must be a list")
    #     return value

    # def validate_course_categories(self, value):
    #     if not isinstance(value, list):
    #         raise serializers.ValidationError("Course categories must be a list")
    #     return value

    # def validate_notification_preferences(self, value):
    #     if not isinstance(value, dict):
    #         raise serializers.ValidationError("Notification preferences must be a dictionary")
    #     return value

    # def validate_social_links(self, value):
    #     if not isinstance(value, dict):
    #         raise serializers.ValidationError("Social links must be a dictionary")
    #     return value






class StudentQuerySerializer(serializers.ModelSerializer):
    """
    Serializer for Student Query Form
    """
    class Meta:
        model = StudentQuery
        fields = [
            'id', 'name', 'email', 'contact_no', 'area', 
            'current_class', 'subjects', 'special_requirements',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_email(self, value):
        """Validate email format"""
        return value.lower()

    def validate_subjects(self, value):
        """Clean subjects field"""
        if value:
            # Remove extra spaces and ensure proper formatting
            subjects = [subject.strip() for subject in value.split(',') if subject.strip()]
            return ', '.join(subjects)
        return value



class StudentQueryListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing student queries in admin dashboard
    """
    linked_user_email = serializers.CharField(source='linked_user.email', read_only=True)
    
    class Meta:
        model = StudentQuery
        fields = [
            'id', 'name', 'email', 'contact_no', 'area',
            'current_class', 'subjects', 'special_requirements',
            'is_registered', 'is_processed', 'admin_notes',
            'linked_user_email', 'created_at', 'updated_at'
        ]