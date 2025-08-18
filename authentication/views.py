# authenticate/view.py

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404
from .models import User,StudentProfile,TeacherProfile
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer,
    RoleUpdateSerializer,
    StudentProfileSerializer,
    TeacherProfileSerializer
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json
from rest_framework.parsers import MultiPartParser, FormParser

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
        {settings.FRONTEND_URL}/auth/verify-email/{token}/
        
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
        {settings.FRONTEND_URL}/auth/verify-email/{token}/
        
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
        student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={"email": request.user.email}
    )
            
        serializer = StudentProfileSerializer(student_profile,data=request.data,partial=True)
        if serializer.is_valid():
            request.user.role = 'student'
            request.user.save(update_fields=["role"])
            serializer.save(user=request.user, email=request.user.email)
            return Response({"success": True, "message": "Student profile created", "data": serializer.data}, status=201)
        
        return Response({"success": False, "errors": serializer.errors}, status=400)


class CreateTeacherProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @swagger_auto_schema(
        request_body=TeacherProfileSerializer,
        responses={
            201: openapi.Response('Registration Successful', TeacherProfileSerializer),
            400: 'Bad Request'
        }
    )
    def post(self, request):
        # Prevent duplicate
        if hasattr(request.user, 'teacher_profile'):
            return Response({"success": False, "message": "Teacher profile already exists"}, status=400)

        # copy request.data (QueryDict) to a mutable dict
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

        # Helper to get repeated fields
        def get_repeated(key):
            try:
                return request.data.getlist(key)
            except Exception:
                # getlist may not be available — fall back to single value
                v = request.data.get(key)
                return [v] if v is not None else []

        # Fields we expect to be JSON/list/object
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
            "additional_documents",
        ]

        # Normalize array-style repeated keys (field[]), prefer explicit field value if present
        for field in json_fields:
            # If plain field exists and is non-empty, leave it (serializer will parse it)
            raw = request.data.get(field)
            if raw not in (None, ""):
                # plain value present — keep as-is (likely JSON string or already parsed)
                data[field] = raw
                continue

            # Otherwise look for repeated `field[]`
            arr = get_repeated(f"{field}[]")
            if arr:
                # arr may contain JSON strings or primitive strings. Try to parse individual items, else keep raw.
                normalized = []
                for item in arr:
                    if item is None or item == "":
                        continue
                    if isinstance(item, str):
                        item = item.strip()
                        # try JSON parse if looks like json
                        if (item.startswith("{") and item.endswith("}")) or (item.startswith("[") and item.endswith("]")):
                            try:
                                normalized.append(json.loads(item))
                                continue
                            except Exception:
                                pass
                        normalized.append(item)
                    else:
                        normalized.append(item)
                # set JSON-string representation so serializer.to_internal_value() can json.loads it
                data[field] = json.dumps(normalized)
                continue

            # For nested objects like availability_schedule, look for keys like availability_schedule[Monday]
            # collect subkeys
            nested = {}
            for key in request.data.keys():
                if key.startswith(f"{field}[") and key.endswith("]"):
                    # form key like availability_schedule[Monday]
                    subkey = key[len(field) + 1 : -1]
                    val = request.data.get(key)
                    # if the value looks like a JSON array string, parse it, else try getlist for repeated items
                    if val and isinstance(val, str) and val.strip().startswith("["):
                        try:
                            nested[subkey] = json.loads(val)
                            continue
                        except Exception:
                            pass
                    # try getlist for availability_schedule[Monday][]
                    sub_arr = get_repeated(f"{field}[{subkey}][]")
                    if sub_arr:
                        nested[subkey] = sub_arr
                    elif val not in (None, ""):
                        nested[subkey] = [val] if not isinstance(val, list) else val

            if nested:
                data[field] = json.dumps(nested)

        # Attach files explicitly if present (some serializers expect file objects in data)
        for file_field in ("resume", "degree_certificates", "id_proof", "profile_picture", "cnic_front", "cnic_back", "degree_image"):
            f = request.FILES.get(file_field)
            if f:
                data[file_field] = f

        # Inject user-related fields if you want defaults (full_name/email/status)
        # Only set if not already provided by client
        if not data.get("full_name"):
            data["full_name"] = f"{request.user.first_name} {request.user.last_name}".strip()
        if not data.get("email"):
            data["email"] = request.user.email or ""
        data["status"] = data.get("status", "pending")

        # Instantiate serializer — serializer.to_internal_value() will parse JSON strings
        serializer = TeacherProfileSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user, email=request.user.email, status="pending")
            return Response({"success": True, "message": "Teacher profile submitted for approval", "data": serializer.data}, status=201)

        return Response({"success": False, "errors": serializer.errors}, status=400)

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
