# job_board/filters.py

import django_filters
from django.db import models
from .models import JobPost


class JobPostFilter(django_filters.FilterSet):
    # Budget range filtering
    budget_min = django_filters.NumberFilter(field_name='budget_amount', lookup_expr='gte')
    budget_max = django_filters.NumberFilter(field_name='budget_amount', lookup_expr='lte')
    
    # Teaching mode
    teaching_mode = django_filters.ChoiceFilter(choices=JobPost.TEACHING_MODE_CHOICES)
    
    # Budget type
    budget_type = django_filters.ChoiceFilter(choices=JobPost.BUDGET_TYPE_CHOICES)
    
    # Status
    status = django_filters.ChoiceFilter(choices=JobPost.STATUS_CHOICES)
    
    # Course filtering
    course = django_filters.NumberFilter(field_name='course__id')
    course_name = django_filters.CharFilter(field_name='course__name', lookup_expr='icontains')
    
    # Subject text filtering
    subject = django_filters.CharFilter(field_name='subject_text', lookup_expr='icontains')
    
    # Location filtering (for physical jobs)
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    
    # Date range filtering
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Deadline filtering
    deadline_after = django_filters.DateTimeFilter(field_name='deadline', lookup_expr='gte')
    deadline_before = django_filters.DateTimeFilter(field_name='deadline', lookup_expr='lte')
    
    # Duration filtering
    duration_min = django_filters.NumberFilter(field_name='duration_value', lookup_expr='gte')
    duration_max = django_filters.NumberFilter(field_name='duration_value', lookup_expr='lte')
    duration_unit = django_filters.CharFilter(field_name='duration_unit', lookup_expr='icontains')
    
    # Application count filtering (jobs with more/fewer applications)
    has_applications = django_filters.BooleanFilter(method='filter_has_applications')
    min_applications = django_filters.NumberFilter(method='filter_min_applications')
    max_applications = django_filters.NumberFilter(method='filter_max_applications')
    
    class Meta:
        model = JobPost
        fields = [
            'budget_min', 'budget_max', 'teaching_mode', 'budget_type', 'status',
            'course', 'course_name', 'subject', 'location',
            'created_after', 'created_before', 'deadline_after', 'deadline_before',
            'duration_min', 'duration_max', 'duration_unit',
            'has_applications', 'min_applications', 'max_applications'
        ]
    
    def filter_has_applications(self, queryset, name, value):
        """Filter jobs that have or don't have applications"""
        if value is True:
            return queryset.annotate(
                app_count=models.Count('applications')
            ).filter(app_count__gt=0)
        elif value is False:
            return queryset.annotate(
                app_count=models.Count('applications')
            ).filter(app_count=0)
        return queryset
    
    def filter_min_applications(self, queryset, name, value):
        """Filter jobs with at least X applications"""
        if value is not None:
            return queryset.annotate(
                app_count=models.Count('applications')
            ).filter(app_count__gte=value)
        return queryset
    
    def filter_max_applications(self, queryset, name, value):
        """Filter jobs with at most X applications"""
        if value is not None:
            return queryset.annotate(
                app_count=models.Count('applications')
            ).filter(app_count__lte=value)
        return queryset