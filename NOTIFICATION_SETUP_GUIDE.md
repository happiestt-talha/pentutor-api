# Quick Setup Guide for LMS Notification System

## 🚀 Installation Steps

### 1. Database Migration
Run these commands to create the notification tables:

```bash
# Create migration files
python manage.py makemigrations notifications

# Apply migrations
python manage.py migrate
```

### 2. Verify Installation
Check if everything is working:

```bash
# Start Django development server
python manage.py runserver

# Check if notifications app is loaded (should not show any errors)
python manage.py check
```

### 3. Create Test Data (Optional)
```bash
# Create superuser to access admin
python manage.py createsuperuser

# Access admin at http://localhost:8000/admin/
# You can view and manage notifications from the admin panel
```

## 🧪 Testing the System

### Method 1: Using Postman
1. Import the `LMS_Notifications_Postman_Collection.json` file into Postman
2. Set up your JWT token in the collection variables
3. Test all endpoints as described in the documentation

### Method 2: Using Django Admin
1. Go to http://localhost:8000/admin/
2. Navigate to "Notifications" section
3. You can create, view, and manage notifications manually

### Method 3: Trigger Automatic Notifications
1. **Video Upload**: Create a new video through your video API
2. **Quiz Creation**: Create a new quiz through your quiz API  
3. **Student Enrollment**: Complete a payment for a course
4. **Live Class**: Schedule a new meeting with `meeting_type='lecture'`

## 📋 Quick Test Checklist

- [ ] Migrations applied successfully
- [ ] Server starts without errors
- [ ] Can access `/api/notifications/` endpoint
- [ ] JWT authentication works
- [ ] Notifications are created when videos are uploaded
- [ ] Notifications are created when quizzes are created
- [ ] Notifications are created when students enroll
- [ ] Notifications are created when live classes are scheduled
- [ ] Mark as read functionality works
- [ ] Pagination works correctly
- [ ] Filtering by type and read status works

## 🔧 Troubleshooting

### Common Issues:

1. **ImportError: No module named 'notifications'**
   - Make sure `'notifications'` is added to `INSTALLED_APPS`
   - Restart your Django server

2. **Signals not working**
   - Check that `notifications.signals` is imported in `apps.py`
   - Verify the `ready()` method is implemented in `NotificationsConfig`

3. **JWT Authentication errors**
   - Ensure you're sending the correct Bearer token
   - Check if your JWT token hasn't expired

4. **No notifications being created**
   - Check Django logs for any signal errors
   - Verify that the triggering events (video upload, etc.) are actually happening
   - Make sure there are enrolled students in the course

## 📁 File Structure Created

```
notifications/
├── __init__.py
├── admin.py          # Django admin configuration
├── apps.py           # App configuration with signal imports
├── models.py         # Notification model
├── serializers.py    # API serializers
├── signals.py        # Automatic notification triggers
├── urls.py           # URL patterns
└── views.py          # API views
```

## 🔗 API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/` | Get all notifications |
| GET | `/api/notifications/{id}/` | Get notification details |
| POST | `/api/notifications/mark-as-read/` | Mark specific notifications as read |
| POST | `/api/notifications/mark-all-as-read/` | Mark all notifications as read |
| GET | `/api/notifications/stats/` | Get notification statistics |
| GET | `/api/notifications/unread-count/` | Get unread count |
| GET | `/api/notifications/recent/` | Get recent notifications |
| DELETE | `/api/notifications/{id}/delete/` | Delete a notification |
| DELETE | `/api/notifications/delete-all-read/` | Delete all read notifications |

## 🎯 Next Steps

1. **Frontend Integration**: Use the provided React examples to integrate with your frontend
2. **Real-time Updates**: Consider adding WebSocket support for real-time notifications
3. **Email Notifications**: Extend the system to send email notifications
4. **Push Notifications**: Add mobile push notification support
5. **Custom Notification Types**: Add more notification types as needed

## 📞 Support

If you encounter any issues:
1. Check the `NOTIFICATION_SYSTEM_README.md` for detailed documentation
2. Review the Postman collection for API examples
3. Check Django logs for error messages
4. Verify your JWT authentication setup

The notification system is now ready to use! 🎉