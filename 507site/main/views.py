from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Task, Comment, Sprint
from .forms import TaskForm, CommentForm, RegisterForm
from django.http import JsonResponse
import json


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})


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
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            
            messages.success(request, 'Comment added!')
            return redirect('task_detail', pk=task.pk)
    else:
        comment_form = CommentForm()
    
    comments = task.comments.all()
    context = {
        'task': task,
        'page_title': 'Task Details',
        'comment_form': comment_form,
        'comments': comments
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
            form.save_m2m()
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
            
            task.description = data.get('description')
            task.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def product_backlog(request):
    # Retrieve tasks and sprints
    backlog_tasks = Task.objects.filter(status='BACKLOG').order_by('priority', '-created_at')

    active_sprints = Sprint.objects.filter(status='ACTIVE').order_by('name')
    planning_sprints = Sprint.objects.filter(status='PLANNING').order_by('name')
    sprints = list(active_sprints) + list(planning_sprints)
    
    context = {
        'backlog_tasks': backlog_tasks,
        'sprints': sprints,
        'total_story_points': sum(t.story_points for t in backlog_tasks),
    }
    
    return render(request, 'main/product_backlog.html', context)

@login_required
def sprint_board(request, sprint_pk):
    sprint = Sprint.objects.get(pk=sprint_pk)
    
    # Get all tasks in sprint
    all_sprint_tasks = list(
        Task.objects.filter(sprint=sprint).order_by('priority', '-created_at')
    )
    
    # Separate tasks by sprint_progress
    not_started_tasks = [t for t in all_sprint_tasks if not t.sprint_progress or t.sprint_progress == 'NOT_STARTED']
    in_progress_tasks = [t for t in all_sprint_tasks if t.sprint_progress == 'IN_PROGRESS']
    in_review_tasks = [t for t in all_sprint_tasks if t.sprint_progress == 'IN_REVIEW']
    done_tasks = [t for t in all_sprint_tasks if t.sprint_progress == 'DONE']

    # Calculate story points per column
    not_started_points = sum(t.story_points for t in not_started_tasks)
    in_progress_points = sum(t.story_points for t in in_progress_tasks)
    in_review_points = sum(t.story_points for t in in_review_tasks)
    done_points = sum(t.story_points for t in done_tasks)
    
    # Calculate sprint metrics
    total_tasks = len(all_sprint_tasks)
    total_story_points = sum(t.story_points for t in all_sprint_tasks)
    
    # Completed tasks (Done status)
    completed_tasks_list = [t for t in all_sprint_tasks if t.sprint_progress == 'DONE']
    completed_tasks = len(completed_tasks_list)
    completed_story_points = sum(t.story_points for t in completed_tasks_list)
    
    context = {
        'sprint': sprint,
        'sprint_tasks': all_sprint_tasks,
        
        # Sprint Progress columns
        'not_started_tasks': not_started_tasks,
        'in_progress_tasks': in_progress_tasks,
        'in_review_tasks': in_review_tasks,
        'done_tasks': done_tasks,

        # Column metrics
        'not_started_points': not_started_points,
        'in_progress_points': in_progress_points,
        'in_review_points': in_review_points,
        'done_points': done_points,
        
        # Metrics
        'total_story_points': total_story_points,
        'completed_story_points': completed_story_points,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
    }
    
    return render(request, 'main/sprint_board.html', context)

@login_required
def sprint_list(request):
    sprints = Sprint.objects.all().order_by('-created_at')

    context = {
        'sprints': sprints,
    }

    return render(request, 'main/sprint_list.html', context)

@login_required
def move_to_sprint(request, task_pk, sprint_pk):
    # Move task to sprint
    task = Task.objects.get(pk=task_pk)
    sprint = Sprint.objects.get(pk=sprint_pk)

    # Check if task is already in a sprint
    if task.sprint and task.sprint.status in ['PLANNING', 'ACTIVE']:
        messages.error(request, f'Task "{task.title}" is already assigned to {task.sprint.name}!')
        return redirect('product_backlog')
    
    # Move task to sprint
    task.sprint = sprint
    task.status = 'SPRINT'
    task.SPRINT_PROGRESS = 'NOT_STARTED'
    task.save()
    
    messages.success(request, f'Task "{task.title}" moved to {sprint.name}!')
    
    return redirect('product_backlog')

@login_required
def update_sprint_progress(request, task_pk, new_progress):

    task = Task.objects.get(pk=task_pk)
    
    # Only update if task is in a sprint
    if task.status != 'SPRINT':
        messages.error(request, 'Task must be in sprint to update sprint progress!')
        return redirect('task_detail', pk=task.pk)
    
    # Validate allowed transitions
    valid_progress = ['NOT_STARTED', 'IN_PROGRESS', 'IN_REVIEW', 'DONE']
    if new_progress not in valid_progress:
        messages.error(request, 'Invalid sprint progress!')
        return redirect('task_detail', pk=task.pk)
    
    # Update sprint status
    old_progress = task.get_sprint_progress_display() if task.sprint_progress else 'Not Started'
    task.sprint_progress = new_progress
    task.save()
    
    messages.success(request, f'Task moved from {old_progress} to {task.get_sprint_progress_display()}!')
    
    return redirect('sprint_board', sprint_pk=task.sprint.pk)