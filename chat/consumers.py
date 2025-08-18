import json
from channels.generic.websocket import AsyncWebsocketConsumer
# from accounts.models import CustomUser
from rest_framework_simplejwt.tokens import UntypedToken
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from jwt import decode as jwt_decode
from django.conf import settings

from .models import ChatMessage

User = get_user_model()

# Temporary in-memory user tracking (for dev)
ONLINE_USERS = {}  # { room_id: set(user_info_dicts) }

def get_cookie(headers, key):
    for header in headers:
        if header[0] == b'cookie':
            cookies = header[1].decode()
            for item in cookies.split(';'):
                if item.strip().startswith(key + "="):
                    return item.strip().split('=', 1)[1]
    return None


class VideoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"meeting_{self.room_id}"
        self.user = None  # Initialize user

        # Extract JWT from cookies
        token = get_cookie(self.scope["headers"], "access")
        # Debug: Print all headers for inspection
        print("Request Headers:")
        for header in self.scope["headers"]:
            print(f"{header[0].decode()}: {header[1].decode()}")
        
        if not token:
            print("❌ No access token found in cookies")
            await self.close()
            return
            
        self.user = await self.get_user_from_token(token)

        if not self.user or self.user.is_anonymous:
            print("❌ Invalid user or token")
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Add user with first_name to online users
        await self.add_online_user(self.room_id, self.user.username, self.user.first_name)
        await self.send_online_users()

        print(f"✅ {self.user.first_name} ({self.user.username}) connected to {self.room_group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        
        # Only remove user if self.user exists
        if hasattr(self, 'user') and self.user and hasattr(self.user, 'username'):
            await self.remove_online_user(self.room_id, self.user.username)
            await self.send_online_users()
            print(f"❌ {self.user.first_name} ({self.user.username}) disconnected from {self.room_group_name}")
        else:
            print(f"❌ User disconnected from {getattr(self, 'room_group_name', 'unknown room')}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get("message", "")

            if self.user and not self.user.is_anonymous and message.strip():
                # Save to DB with username (for identification)
                await database_sync_to_async(ChatMessage.objects.create)(
                    room_id=self.room_id,
                    user=self.user.username,
                    message=message
                )

                # Broadcast with first_name (for display)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'broadcast_message',
                        'message': message,
                        'user': self.user.username,  # for backend identification
                        'first_name': self.user.first_name,  # for frontend display
                        'user_id': self.user.id
                    }
                )
                print(f"💬 Message from {self.user.first_name}: {message}")
        except Exception as e:
            print(f"[receive error] {str(e)}")

    async def broadcast_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',  # Add message type
            'message': event['message'],
            'user': event.get('user'),  # username for identification
            'first_name': event.get('first_name'),  # first_name for display
            'user_id': event.get('user_id')
        }))

    async def online_users(self, event):
        await self.send(text_data=json.dumps({
            'type': 'online_users',
            'users': event['users']
        }))

    async def send_online_users(self):
        if hasattr(self, 'room_id'):
            users_data = []
            raw_users = list(ONLINE_USERS.get(self.room_id, set()))
            
            for user_info in raw_users:
                if '|' in user_info:
                    username, first_name = user_info.split('|', 1)
                    users_data.append({
                        'username': username,
                        'first_name': first_name
                    })
                else:
                    users_data.append({
                        'username': user_info,
                        'first_name': user_info
                    })
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'online_users',
                    'users': users_data
                }
            )

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            # Convert token to bytes if it's a string
            if isinstance(token, str):
                token_bytes = token.encode('utf-8')
            else:
                token_bytes = token
                
            # Validate token first
            UntypedToken(token_bytes)
            
            # Decode token
            decoded = jwt_decode(token_bytes, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded.get("user_id")
            
            if user_id:
                user = User.objects.get(id=user_id)
                print(f"🔑 Token validated for user: {user.first_name} ({user.username})")
                return user
            else:
                print("❌ No user_id in token")
                return None
                
        except Exception as e:
            print(f"❌ Token validation error: {str(e)}")
            return None

    @database_sync_to_async
    def add_online_user(self, room_id, username, first_name):
        if room_id not in ONLINE_USERS:
            ONLINE_USERS[room_id] = set()
        
        # Store user info as a string with pipe separator
        user_info = f"{username}|{first_name or username}"
        ONLINE_USERS[room_id].add(user_info)
        print(f"👥 Added {first_name} to room {room_id}")

    @database_sync_to_async
    def remove_online_user(self, room_id, username):
        if room_id in ONLINE_USERS:
            # Remove any entry that starts with this username
            to_remove = None
            for user_info in ONLINE_USERS[room_id]:
                if user_info.startswith(f"{username}|"):
                    to_remove = user_info
                    break
            if to_remove:
                ONLINE_USERS[room_id].discard(to_remove)
                print(f"👥 Removed {username} from room {room_id}")
            
            # Clean up empty rooms
            if not ONLINE_USERS[room_id]:
                del ONLINE_USERS[room_id]