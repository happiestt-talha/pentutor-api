# authenticate/view.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import User,StudentProfile,TeacherProfile,StudentQuery
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer,
    RoleUpdateSerializer,
    StudentProfileSerializer,
    TeacherProfileSerializer,
    StudentQuerySerializer,
    StudentQueryListSerializer
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json
from rest_framework.parsers import MultiPartParser, FormParser

import os
from dotenv import load_dotenv
load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=UserRegistrationSerializer,
        responses={
        201: openapi.Response('Registration Successful', UserSerializer),
        400: 'Bad Request'
    }
    )
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate verification token
            verification_token = get_random_string(50)
            user.verification_token = verification_token
            user.save()
            
            # Send verification email
            self.send_verification_email(user, verification_token)
            
            return Response({
                'success': True,
                'message': 'Registration successful! Please check your email for verification.',
                'data': {
                    'user_id': user.id,
                    'email': user.email,
                    'username': user.username
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Registration failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def send_verification_email(self, user, token):
        subject = 'Verify Your Email - LMS'
        message = f'''
        Hi {user.username},
        
        Thank you for registering with our LMS platform!
        Your Role is {user.role}
        
        Please click the following link to verify your email:
        {FRONTEND_URL}/auth/verify-email/{token}/
        
        If you didn't create this account, please ignore this email.
        
        Best regards,
        LMS Team
        '''
        
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])
        except Exception as e:
            print(f"Email sending failed: {e}")

class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
    manual_parameters=[
        openapi.Parameter(
            'token',
            openapi.IN_PATH,
            description="Email verification token",
            type=openapi.TYPE_STRING
        )
    ],
    responses={200: 'Email verified successfully', 400: 'Invalid or expired token'}
)
    
    def get(self, request, token):
        try:
            user = User.objects.get(verification_token=token)
            user.is_verified = True
            user.verification_token = None
            user.save()
            
            return Response({
                'success': True,
                'message': 'Email verified successfully! You can now login.'
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid or expired verification token.'
            }, status=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
    request_body=UserLoginSerializer,
    responses={200: 'Login successful', 400: 'Invalid credentials'}
)
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'data': {
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                    'user': UserSerializer(user).data
                }
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Login failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(responses={200: UserSerializer})
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        request_body=UserSerializer,
        responses={200: UserSerializer, 400: 'Validation Error'}
    )
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Profile update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'refresh_token': openapi.Schema(type=openapi.TYPE_STRING)
        },
        required=['refresh_token']
    ),
    responses={200: 'Logout successful', 400: 'Logout failed'}
)
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({"detail": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Logout failed'
            }, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL)
        },
        required=['email']
    ),
    responses={200: 'Verification email sent', 404: 'User not found'}
)

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({
                'success': False,
                'message': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            if user.is_verified:
                return Response({
                    'success': False,
                    'message': 'Email is already verified'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate new verification token
            verification_token = get_random_string(50)
            user.verification_token = verification_token
            user.save()
            
            # Send verification email
            self.send_verification_email(user, verification_token)
            
            return Response({
                'success': True,
                'message': 'Verification email sent successfully'
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def send_verification_email(self, user, token):
        subject = 'Verify Your Email - LMS'
        message = f'''
        Hi {user.username},
        
        Please click the following link to verify your email:
        {FRONTEND_URL}/auth/verify-email/{token}/
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        LMS Team
        '''
        
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception as e:
            print(f"Email sending failed: {e}")

# ======================================
# Update Studnet Profile
# ===================================
class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
    responses={
        200: StudentProfileSerializer,  # or TeacherProfileSerializer dynamically
        404: 'Profile not found'
    }
)
    
    def get_profile_and_serializer(self, user):
        """Helper method to get the appropriate profile and serializer based on user role."""
        if user.role == 'student':
            profile = get_object_or_404(StudentProfile, user=user)
            serializer_class = StudentProfileSerializer
        elif user.role == 'teacher':
            profile = get_object_or_404(TeacherProfile, user=user)
            serializer_class = TeacherProfileSerializer
        else:
            return None, None
        return profile, serializer_class
    
    def get(self, request):
        """Retrieve the user's profile."""
        profile, serializer_class = self.get_profile_and_serializer(request.user)
        
        if not profile or not serializer_class:
            return Response({
                'success': False,
                'message': 'Invalid user role or profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = serializer_class(profile)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    

    @swagger_auto_schema(
    request_body=StudentProfileSerializer,  # or TeacherProfileSerializer dynamically
    responses={200: 'Profile updated successfully', 400: 'Validation Error'}
)
    def put(self, request):
        """Update the entire profile."""
        profile, serializer_class = self.get_profile_and_serializer(request.user)
        
        if not profile or not serializer_class:
            return Response({
                'success': False,
                'message': 'Invalid user role or profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = serializer_class(profile, data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Profile update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
    request_body=StudentProfileSerializer,  # or TeacherProfileSerializer dynamically
    responses={200: 'Profile updated successfully', 400: 'Validation Error'})
    
    def patch(self, request):
        """Partially update the profile."""
        profile, serializer_class = self.get_profile_and_serializer(request.user)
        
        if not profile or not serializer_class:
            return Response({
                'success': False,
                'message': 'Invalid user role or profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = serializer_class(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Profile update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)           


# =====================
# request role
# =====================
class CreateStudentProfileView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=StudentProfileSerializer,
        responses={
        201: openapi.Response('Registration Successful', StudentProfileSerializer),
        400: 'Bad Request'
    }
    )

    def post(self, request):
            
        with transaction.atomic():

            # Check if student query exists for this email
            existing_query = StudentQuery.objects.filter(
                    email=request.user.email,
                    is_registered=False
                ).first()
            
            # Create or get student profile
            student_profile, created = StudentProfile.objects.get_or_create(
            user=request.user,
            defaults={"email": request.user.email})
        
        
            # If existing query found, pre-populate some fields
            if existing_query and created:
                # Map query data to profile fields
                profile_data = request.data.copy()
                profile_data.update({
                    'full_name': existing_query.name,
                    'city': existing_query.area,
                    'phone': existing_query.contact_no,
                })
                
                # Update query status
                existing_query.is_registered = True
                existing_query.linked_user = request.user
                existing_query.save()
                
            else:
                profile_data = request.data
            
            
            serializer = StudentProfileSerializer(student_profile,data=request.data,partial=True)
            if serializer.is_valid():
                request.user.role = 'student'
                request.user.save(update_fields=["role"])
                serializer.save(user=request.user, email=request.user.email)
                return Response({"success": True, "message": "Student profile created", "data": serializer.data}, status=201)
        
        return Response({"success": False, "errors": serializer.errors}, status=400)


class CreateTeacherProfileView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=TeacherProfileSerializer,
        responses={
        201: openapi.Response('Registration Successful', TeacherProfileSerializer),
        400: 'Bad Request'
    }
    )
    def post(self, request):
        if hasattr(request.user, 'teacher_profile'):
            return Response({"success": False, "message": "Teacher profile already exists"}, status=400)
        
         # 1️⃣ Parse the JSON string from `data` key in form-data
        try:
            data_json = json.loads(request.data.get('data', '{}'))
        except json.JSONDecodeError:
            return Response({"success": False, "message": "Invalid JSON in 'data' field"}, status=400)
        
        # 2️⃣ Merge files into data dictionary
        data_json['resume'] = request.FILES.get('resume')
        data_json['degree_certificates'] = request.FILES.get('degree_certificates')
        data_json['id_proof'] = request.FILES.get('id_proof')

        # 3️⃣ Inject user and email
        data_json['user'] = request.user
        data_json['full_name'] = f"{request.user.first_name} {request.user.last_name}"
        data_json['email'] = request.user.email
        data_json['status'] = "pending"


        serializer = TeacherProfileSerializer(data=data_json)
        if serializer.is_valid():
            serializer.save(user=request.user, email=request.user.email, status="pending")  # pending approval
            return Response({"success": True, "message": "Teacher profile submitted for approval", "data": serializer.data}, status=201)
        
        return Response({"success": False, "errors": serializer.errors}, status=400)

# ==========================
# Student query form
# =======================

class StudentQueryView(APIView):
    """
    Handle student query form submission (no authentication required)
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=StudentQuerySerializer,
        responses={
            201: openapi.Response('Query Submitted Successfully', StudentQuerySerializer),
            400: 'Bad Request'
        }
    )
    def post(self, request):
        serializer = StudentQuerySerializer(data=request.data)
        if serializer.is_valid():
            # Check if query already exists for this email
            email = serializer.validated_data['email']
            existing_query = StudentQuery.objects.filter(email=email).first()
            
            if existing_query:
                return Response({
                    'success': False,
                    'message': 'A query with this email already exists. Please contact admin for updates.',
                    'data': {'query_id': existing_query.id}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save the query
            query = serializer.save()
            
            # Create admin notification
            # self.create_admin_notification(query)
            
            # Send confirmation email to student
            self.send_confirmation_email(query)
            
            return Response({
                'success': True,
                'message': 'Your query has been submitted successfully! We will contact you soon.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Please check your information and try again.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # def create_admin_notification(self, query):
    #     """Create notification for admin"""
    #     Notification.objects.create(
    #         title=f"New Student Query from {query.name}",
    #         message=f"A new student query has been submitted by {query.name} ({query.email}) from {query.area}. Subject interests: {query.subjects}",
    #         notification_type='student_query',
    #         student_query=query
    #     )
    
    def send_confirmation_email(self, query):
        """Send confirmation email to student"""
        subject = 'Query Received - LMS Platform'
        message = f'''
        Hi {query.name},
        
        Thank you for your interest in our LMS platform!
        
        We have received your query with the following details:
        - Name: {query.name}
        - Email: {query.email}
        - Area: {query.area}
        - Class: {query.current_class}
        - Subjects: {query.subjects}
        
        Our team will review your query and contact you within 24-48 hours.
        
        Best regards,
        LMS Team
        '''
        
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [query.email])
        except Exception as e:
            print(f"Email sending failed: {e}")


# ===================================
# Admin Content
# ===================================
class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
    manual_parameters=[
        openapi.Parameter('role', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        openapi.Parameter('is_verified', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN)
    ],
    responses={200: UserSerializer(many=True)}
)
    def get(self, request):
        # Check if user is admin or subadmin
        if request.user.role not in ['admin', 'subadmin']:
            return Response({
                'success': False,
                'message': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        users = User.objects.all()
        role = request.GET.get('role')
        is_verified = request.GET.get('is_verified')

        if role:
            users = users.filter(role=role)

        if is_verified is not None:
            if is_verified.lower() == 'true':
              users = users.filter(is_verified=True)
            elif is_verified.lower() == 'false':
                users = users.filter(is_verified=False)

        serializer = UserSerializer(users, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

class AdminRoleUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
    manual_parameters=[
        openapi.Parameter('user_id', openapi.IN_PATH, type=openapi.TYPE_INTEGER)
    ],
    request_body=RoleUpdateSerializer,
    responses={200: UserSerializer, 400: 'Validation Error', 404: 'User not found'}
)

    def put(self, request, user_id):
        # Check if user is admin
        if request.user.role != 'admin':
            return Response({
                'success': False,
                'message': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
            old_role = user.role
            if old_role == 'teacher':
                return Response({'success': False, 'message': 'Cannot change role of a teacher. alredy role is teacher'}, status=status.HTTP_404_NOT_FOUND)
                                
            serializer = RoleUpdateSerializer(user, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()

                # If role change to teacher then create Teacher object
                new_role = serializer.validated_data.get('role')
                if new_role == 'teacher' and old_role != 'teacher':
                    from courses.models import Teacher
                    Teacher.objects.get_or_create(user=user) 

                
                return Response({
                    'success': True,
                    'message': 'User role updated successfully',
                    'data': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Role update failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
