from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Task(models.Model):
  
    # Status Choices
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
    SPRINT_STATUS = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('IN_REVIEW', 'In Review'),
        ('COMPLETED', 'Completed'),
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
    story_points = models.PositiveIntegerField(default=1)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
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

    # Sprint Progress
    sprint = models.ForeignKey(
        'Sprint',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )
    class Meta:
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"
    
class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=1000, help_text="Maximum 1000 characters")
    created_at = models.DateTimeField(auto_now_add=True)
        
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author.username} commented on {self.task.title} at {self.created_at}"

class Sprint (models.Model):

    SPRINT_STATUS = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('IN_REVIEW', 'In Review'),
        ('COMPLETED', 'Completed'),
    ]
    name = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    goal = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Task.SPRINT_STATUS,
        default='NOT_STARTED'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def task_count(self):
        return self.tasks.count()
    
    @property
    def completed_tasks(self):
        return self.task_set.filter(status='COMPLETE').count()
    