from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Task(models.Model):
  
    # Status Choices - matching your workflow
    STATUS_CHOICES = [
        ('BACKLOG', 'Product Backlog'),
        ('SPRINT', 'Sprint Backlog'),
        ('TESTING', 'Ready for Test'),
        ('FAILED', 'Failed - Rework'),
        ('COMPLETE', 'Complete - Ready for Release'),
    ]
    
    # Priority Choices
    PRIORITY_CHOICES = [
        (1, 'Critical'),
        (2, 'High'),
        (3, 'Medium'),
        (4, 'Low'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='BACKLOG'
    )
    priority = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=3
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"
