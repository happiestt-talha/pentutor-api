# chat/view.py

from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from chat.models import ChatMessage


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, room_id):
        # Pagination params
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("limit", 20))
        offset = (page - 1) * page_size

        # Filter messages for the room, latest first
        messages_qs = ChatMessage.objects.filter(room_id=room_id).order_by("-timestamp")
        total = messages_qs.count()

        # Paginating
        messages = messages_qs[offset:offset + page_size]

        # Response
        data = [
            {
                "user": msg.user,
                "message": msg.message,
                "timestamp": msg.timestamp
            }
            for msg in messages
        ]

        return Response({
            "messages": data,
            "total": total,
            "page": page,
            "limit": page_size
        })


class ChatbotView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user_role = getattr(user, "role", "student") or "student"
        incoming_message = (request.data.get("message") or "").strip()

        if not incoming_message:
            return Response({
                "reply": "Please provide a message, e.g., 'help' to see what I can do.'",
                "role": user_role
            }, status=200)

        # Log user's message
        room_id = f"bot:{user.id}"
        ChatMessage.objects.create(
            room_id=room_id,
            user=user.email or user.username or str(user.id),
            message=incoming_message,
        )

        reply_text = self._generate_reply(incoming_message, user_role)

        # Log bot reply
        ChatMessage.objects.create(
            room_id=room_id,
            user="bot",
            message=reply_text,
        )

        return Response({
            "reply": reply_text,
            "role": user_role
        }, status=200)

    def _generate_reply(self, message: str, role: str) -> str:
        text = message.lower()

        # Greetings
        if any(g in text for g in ["hello", "hi", "hey"]):
            if role == "teacher":
                return "Hello, Teacher! How can I assist with your classes, meetings, or notifications today?"
            if role == "student":
                return "Hi there! Need help with your courses, assignments, or meetings? Type 'help' to see options."
            return "Hello! How can I help you today?"

        # Help menu
        if "help" in text:
            if role == "teacher":
                return (
                    "I can help with: courses, meetings, notifications, profile. "
                    "Examples: 'upcoming meetings', 'my courses', 'update profile', 'notifications'."
                )
            return (
                "I can help with: courses, assignments, attendance, meetings, profile. "
                "Examples: 'my courses', 'my attendance', 'upcoming meetings', 'update profile'."
            )

        # Common intents
        if "course" in text:
            if role == "teacher":
                return "To manage your courses, visit the teacher portal or use /api/courses/."
            return "To view your courses, open the student dashboard or call GET /api/courses/."

        if any(k in text for k in ["meeting", "class", "schedule"]):
            return "You can view meetings via the dashboard or API at /api/meetings/. Try asking 'upcoming meetings'."

        if any(k in text for k in ["assign", "homework", "task"]):
            if role == "teacher":
                return "To share assignments, use your course tools in the teacher portal."
            return "Check your assignments in the student dashboard."

        if any(k in text for k in ["attendance", "present", "absent"]):
            return "Attendance details are available in the student dashboard."

        if any(k in text for k in ["profile", "account", "settings"]):
            return "Use GET/PUT /api/auth/profile/ to view or update your profile."

        if any(k in text for k in ["notification", "alert", "reminder"]):
            return "You can view alerts at /api/alerts/ and notifications at /api/notifications/."

        # Fallback
        return (
            "I'm not sure about that yet. Try 'help' for suggestions like courses, meetings, assignments, "
            "attendance, profile, or notifications."
        )



