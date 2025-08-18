

from django.urls import path
from . import views


urlpatterns = [
    path("authorize", views.google_calender_auth, name="google_calender_auth"),
    path("oauth2callback/", views.oauth2_callback, name="oauth2_callback"),
    path("events", views.calendar_events, name="calendar_events"),
    path('notifications/', views.calendar_notification, name='calendar_notification'),
    path('disconnect/', views.disconnect_google, name='disconnect_google'),
]