from django import forms
from .models import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'story_points', 'assigned_to', 'estimated_hours']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter task title', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter task description', 'rows': 4, 'required': True}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'story_points': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1, 2, 3, 5, 8, 13...', 'min': 1}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'estimated_hours': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 4.5', 'step': '0.5', 'min': 0}),
        }
        labels = {
            'title': 'Task Title',
            'description': 'Description',
            'priority': 'Priority Level',
            'story_points': 'Story Points',
            'assigned_to': 'Assigned To',
            'estimated_hours': 'Estimated Hours (optional)',
        }