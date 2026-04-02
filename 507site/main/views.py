from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Task
from .forms import TaskForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


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

@login_required
def create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.status = 'BACKLOG'
            task.save()

            messages.success(request, f'Task "{task.title}" created successfully!')
            return redirect('dashboard')
    else:
            form = TaskForm()
        
    context = {
        'form': form,
        'page_title': 'Create a New Task',
    }
    
    return render(request, 'main/task_form.html', context)

@login_required
def task_detail(request, pk):
    task = Task.objects.get(pk=pk)
    context = {
        'task': task,
        'page_title': 'Task Details',
    }
    return render(request, 'main/task_detail.html', context)

@login_required
def edit_task(request, pk):
    task = Task.objects.get(pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            updated_task = form.save(commit=False)
            updated_task.status = task.status
            updated_task.save()
            messages.success(request, f'Task "{task.title}" updated successfully!')
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)
        
    context = {
        'form': form,
        'task': task,
        'page_title': 'Edit Task',
    }
    
    return render(request, 'main/task_form.html', context)


@login_required
def update_task_description(request, pk):

    if request.method == 'POST':
        try:
            task = Task.objects.get(pk=pk)
            data = json.loads(request.body)
            
            # Update the description with new checkbox states
            task.description = data.get('description')
            task.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


        
