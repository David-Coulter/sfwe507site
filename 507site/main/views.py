from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Task


@login_required
def dashboard(request):
   
    # Get counts by status
    backlog_count = Task.objects.filter(status='BACKLOG').count()
    sprint_count = Task.objects.filter(status='SPRINT').count()
    testing_count = Task.objects.filter(status='TESTING').count()
    complete_count = Task.objects.filter(status='COMPLETE').count()
    
    # Get user's assigned tasks
    my_tasks = Task.objects.filter(assigned_to=request.user).exclude(status='COMPLETE')
    
    context = {
        'backlog_count': backlog_count,
        'sprint_count': sprint_count,
        'testing_count': testing_count,
        'complete_count': complete_count,
        'my_tasks': my_tasks,
    }
    
    return render(request, 'main/dashboard.html', context)