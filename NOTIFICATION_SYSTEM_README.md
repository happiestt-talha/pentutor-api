# LMS Notification System Documentation

## Overview
This notification system provides real-time notifications for your Django LMS project. It automatically sends notifications for various events and provides a comprehensive API for managing notifications.

## Features
- ✅ **Video Upload Notifications**: Students get notified when teachers upload new videos
- ✅ **Quiz Creation Notifications**: Students get notified when new quizzes are created
- ✅ **Enrollment Notifications**: Admins and teachers get notified when students enroll
- ✅ **Live Class Notifications**: Students get notified when live classes are scheduled
- ✅ **Mark as Read/Unread**: Users can mark notifications as read or unread
- ✅ **Pagination**: Efficient pagination for large notification lists
- ✅ **Filtering**: Filter notifications by type and read status
- ✅ **Statistics**: Get notification counts and statistics

## API Endpoints

### Base URL
All notification endpoints are available under: `http://localhost:8000/api/notifications/`

### Authentication
All endpoints require JWT authentication. Include the Bearer token in the Authorization header:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

## API Endpoints Reference

### 1. Get All Notifications
**GET** `/api/notifications/`

**Description**: Get paginated list of all notifications for the logged-in user

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `is_read` (optional): Filter by read status (`true` or `false`)
- `notification_type` (optional): Filter by type (`video_upload`, `quiz_created`, `student_enrolled`, `live_class_scheduled`)

**Example Response**:
```json
{
    "count": 25,
    "next": "http://localhost:8000/api/notifications/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "notification_type": "video_upload",
            "notification_type_display": "New Video Uploaded",
            "title": "New Video: Introduction to Django",
            "message": "A new video \"Introduction to Django\" has been uploaded to the course \"Web Development Basics\". Check it out now!",
            "sender_name": "John Teacher",
            "course_title": "Web Development Basics",
            "is_read": false,
            "created_at": "2024-01-15T10:30:00Z",
            "time_since_created": "2 hours ago"
        }
    ]
}
```

### 2. Get Notification Details
**GET** `/api/notifications/{id}/`

**Description**: Get detailed information about a specific notification (automatically marks as read)

**Example Response**:
```json
{
    "id": 1,
    "notification_type": "video_upload",
    "notification_type_display": "New Video Uploaded",
    "title": "New Video: Introduction to Django",
    "message": "A new video \"Introduction to Django\" has been uploaded to the course \"Web Development Basics\". Check it out now!",
    "sender": {
        "id": "uuid-here",
        "username": "john_teacher",
        "email": "john@example.com",
        "full_name": "John Teacher",
        "role": "teacher"
    },
    "course": {
        "id": 1,
        "title": "Web Development Basics",
        "course_type": "free"
    },
    "video": {
        "id": 1,
        "title": "Introduction to Django",
        "duration": "15:30"
    },
    "quiz": null,
    "meeting": null,
    "is_read": true,
    "created_at": "2024-01-15T10:30:00Z",
    "read_at": "2024-01-15T12:30:00Z",
    "time_since_created": "2 hours ago"
}
```

### 3. Mark Notifications as Read
**POST** `/api/notifications/mark-as-read/`

**Description**: Mark specific notifications as read

**Request Body**:
```json
{
    "notification_ids": [1, 2, 3, 4]
}
```

**Example Response**:
```json
{
    "message": "Successfully marked 4 notifications as read.",
    "updated_count": 4
}
```

### 4. Mark All Notifications as Read
**POST** `/api/notifications/mark-all-as-read/`

**Description**: Mark all unread notifications as read for the current user

**Example Response**:
```json
{
    "message": "Successfully marked 15 notifications as read.",
    "updated_count": 15
}
```

### 5. Get Notification Statistics
**GET** `/api/notifications/stats/`

**Description**: Get notification statistics for the current user

**Example Response**:
```json
{
    "total_count": 50,
    "unread_count": 12,
    "read_count": 38,
    "notification_types": {
        "video_upload": 20,
        "quiz_created": 15,
        "student_enrolled": 10,
        "live_class_scheduled": 5
    }
}
```

### 6. Get Unread Count
**GET** `/api/notifications/unread-count/`

**Description**: Get the count of unread notifications (useful for badges)

**Example Response**:
```json
{
    "unread_count": 5
}
```

### 7. Get Recent Notifications
**GET** `/api/notifications/recent/`

**Description**: Get the 10 most recent notifications (useful for dropdown menus)

**Example Response**:
```json
{
    "notifications": [
        {
            "id": 1,
            "notification_type": "video_upload",
            "notification_type_display": "New Video Uploaded",
            "title": "New Video: Advanced Django",
            "message": "A new video has been uploaded...",
            "sender_name": "John Teacher",
            "course_title": "Web Development",
            "is_read": false,
            "created_at": "2024-01-15T10:30:00Z",
            "time_since_created": "Just now"
        }
    ],
    "count": 10
}
```

### 8. Delete Notification
**DELETE** `/api/notifications/{id}/delete/`

**Description**: Delete a specific notification

**Example Response**:
```json
{
    "message": "Notification deleted successfully."
}
```

### 9. Delete All Read Notifications
**DELETE** `/api/notifications/delete-all-read/`

**Description**: Delete all read notifications for the current user

**Example Response**:
```json
{
    "message": "Successfully deleted 25 read notifications.",
    "deleted_count": 25
}
```

## Postman Testing Guide

### Step 1: Set up Authentication
1. First, get a JWT token by logging in through your authentication endpoint
2. In Postman, create a new Collection called "LMS Notifications"
3. In Collection settings, add an Authorization tab with Bearer Token
4. Set the token value to `{{jwt_token}}`
5. Create an environment variable `jwt_token` with your actual token

### Step 2: Test Basic Functionality

#### Test 1: Get All Notifications
```
Method: GET
URL: http://localhost:8000/api/notifications/
Headers: 
- Authorization: Bearer {{jwt_token}}
- Content-Type: application/json
```

#### Test 2: Get Unread Notifications Only
```
Method: GET
URL: http://localhost:8000/api/notifications/?is_read=false
Headers: 
- Authorization: Bearer {{jwt_token}}
- Content-Type: application/json
```

#### Test 3: Get Video Upload Notifications
```
Method: GET
URL: http://localhost:8000/api/notifications/?notification_type=video_upload
Headers: 
- Authorization: Bearer {{jwt_token}}
- Content-Type: application/json
```

#### Test 4: Mark Notifications as Read
```
Method: POST
URL: http://localhost:8000/api/notifications/mark-as-read/
Headers: 
- Authorization: Bearer {{jwt_token}}
- Content-Type: application/json
Body (JSON):
{
    "notification_ids": [1, 2, 3]
}
```

#### Test 5: Get Notification Statistics
```
Method: GET
URL: http://localhost:8000/api/notifications/stats/
Headers: 
- Authorization: Bearer {{jwt_token}}
- Content-Type: application/json
```

#### Test 6: Get Unread Count (for Badge)
```
Method: GET
URL: http://localhost:8000/api/notifications/unread-count/
Headers: 
- Authorization: Bearer {{jwt_token}}
- Content-Type: application/json
```

### Step 3: Test Notification Triggers

To test if notifications are being created automatically, you need to trigger the events:

#### Trigger Video Upload Notification
1. Upload a new video through your video upload API
2. Check if enrolled students receive notifications
3. Use GET `/api/notifications/` to verify

#### Trigger Quiz Creation Notification  
1. Create a new quiz through your quiz creation API
2. Check if enrolled students receive notifications

#### Trigger Enrollment Notification
1. Complete a payment for a course
2. Check if admin and teacher receive notifications

#### Trigger Live Class Notification
1. Schedule a new meeting/live class
2. Check if enrolled students receive notifications

## Error Handling

### Common Error Responses

#### 401 Unauthorized
```json
{
    "detail": "Authentication credentials were not provided."
}
```

#### 404 Not Found
```json
{
    "error": "Notification not found."
}
```

#### 400 Bad Request
```json
{
    "notification_ids": [
        "This field is required."
    ]
}
```

## Database Migration

After setting up the notification system, run these commands:

```bash
python manage.py makemigrations notifications
python manage.py migrate
```

## Installation Steps

1. **Add to INSTALLED_APPS** (Already done):
   ```python
   INSTALLED_APPS = [
       # ... other apps
       'notifications',
       # ... other apps
   ]
   ```

2. **Add URLs** (Already done):
   ```python
   urlpatterns = [
       # ... other urls
       path('api/notifications/', include('notifications.urls')),
       # ... other urls
   ]
   ```

3. **Run Migrations**:
   ```bash
   python manage.py makemigrations notifications
   python manage.py migrate
   ```

4. **Test the System**:
   - Create some test users (students, teachers, admin)
   - Enroll students in courses
   - Upload videos, create quizzes, schedule meetings
   - Check if notifications are created

## Frontend Integration Tips

### React Example for Notification Badge
```javascript
const [unreadCount, setUnreadCount] = useState(0);

useEffect(() => {
    fetch('/api/notifications/unread-count/', {
        headers: {
            'Authorization': `Bearer ${token}`,
        }
    })
    .then(res => res.json())
    .then(data => setUnreadCount(data.unread_count));
}, []);

return (
    <div className="notification-badge">
        <BellIcon />
        {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
    </div>
);
```

### React Example for Notification List
```javascript
const [notifications, setNotifications] = useState([]);

useEffect(() => {
    fetch('/api/notifications/', {
        headers: {
            'Authorization': `Bearer ${token}`,
        }
    })
    .then(res => res.json())
    .then(data => setNotifications(data.results));
}, []);

const markAsRead = (notificationIds) => {
    fetch('/api/notifications/mark-as-read/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notification_ids: notificationIds })
    });
};
```

## Advanced Features

### Custom Notification Types
You can easily add new notification types by:
1. Adding to `NOTIFICATION_TYPES` in the model
2. Creating new signals for your custom events
3. The API will automatically support the new types

### Bulk Operations
The system supports bulk operations for better performance:
- Bulk create notifications using `bulk_create()`
- Bulk mark as read using the API endpoints

### Performance Optimization
- Database indexes are added for common queries
- `select_related()` is used to minimize database queries
- Pagination prevents large response sizes

## Troubleshooting

### Notifications Not Being Created
1. Check if signals are properly imported in `apps.py`
2. Verify that the triggering events are actually creating/updating objects
3. Check Django logs for any signal errors

### Authentication Issues
1. Ensure JWT token is valid and not expired
2. Check if user has proper permissions
3. Verify token format: `Bearer YOUR_TOKEN`

### Performance Issues
1. Use pagination for large notification lists
2. Consider adding database indexes for custom queries
3. Use the lightweight list serializer for better performance

This notification system is production-ready and provides a solid foundation for your LMS platform!