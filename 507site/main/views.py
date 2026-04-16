from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from .models import Task, Comment, Sprint
from .forms import TaskForm, CommentForm, RegisterForm, SprintForm
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
    old_sprint = task.sprint  # Remember original sprint
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            updated_task = form.save(commit=False)
            
            new_sprint = form.cleaned_data.get('sprint')
            
            if new_sprint and not old_sprint:
                print("ADDING SPRINT - Setting status to SPRINT")
                updated_task.status = 'SPRINT'
                updated_task.sprint_progress = 'NOT_STARTED'
                
            elif new_sprint and old_sprint and new_sprint != old_sprint:
                print("CHANGING SPRINT - Keeping status SPRINT")
                updated_task.status = 'SPRINT'
                if not updated_task.sprint_progress:
                    updated_task.sprint_progress = 'NOT_STARTED'
                    
            elif not new_sprint and old_sprint:  
                print("REMOVING SPRINT - Setting status to BACKLOG")
                updated_task.status = 'BACKLOG'
                updated_task.sprint_progress = None
            else:
                print("NO CHANGE DETECTED")
                print(f"  new_sprint is truthy? {bool(new_sprint)}")
                print(f"  old_sprint is truthy? {bool(old_sprint)}")
            
            print(f"BEFORE SAVE: status={updated_task.status}, sprint={updated_task.sprint}, sprint_progress={updated_task.sprint_progress}")
            updated_task.save()
            form.save_m2m()
            
            updated_task.refresh_from_db()
            print(f"AFTER SAVE: status={updated_task.status}, sprint={updated_task.sprint}, sprint_progress={updated_task.sprint_progress}")
            
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
    backlog_tasks = Task.objects.filter(status='BACKLOG', sprint__isnull=True).order_by('priority', '-created_at')
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
def sprint_backlog(request):
    sprints = Sprint.objects.all().order_by('-created_at')

    context = {
        'sprints': sprints,
    }

    return render(request, 'main/sprint_backlog.html', context)

@staff_member_required
def create_sprint(request):

    if request.method == 'POST':
        form = SprintForm(request.POST)
        if form.is_valid():
            sprint = form.save()
            messages.success(request, f'{sprint.name} created successfully!')
            return redirect('sprint_board', sprint_pk=sprint.pk)
    else:
        form = SprintForm()
    
    context = {
        'form': form,
        'sprint': None, 
        'page_title': 'Create Sprint',
    }
    
    return render(request, 'main/sprint_form.html', context)

@staff_member_required
def edit_sprint(request, sprint_pk):
    sprint = Sprint.objects.get(pk=sprint_pk)
    
    # Prevent editing completed sprints
    if sprint.status == 'COMPLETE':
        messages.error(request, f'{sprint.name} is completed and cannot be edited.')
        return redirect('sprint_board', sprint_pk=sprint.pk)
    
    if request.method == 'POST':
        form = SprintForm(request.POST, instance=sprint)
        if form.is_valid():
            form.save()
            messages.success(request, f'{sprint.name} updated successfully!')
            return redirect('sprint_board', sprint_pk=sprint.pk)
    else:
        form = SprintForm(instance=sprint)
    
    context = {
        'form': form,
        'sprint': sprint,
        'page_title': 'Edit Sprint',
    }
    
    return render(request, 'main/sprint_form.html', context)

@login_required
def move_to_sprint(request, task_pk, sprint_pk):
    task = Task.objects.get(pk=task_pk)
    sprint = Sprint.objects.get(pk=sprint_pk)

    # Check if task is already in a sprint
    if task.sprint and task.sprint.status in ['PLANNING', 'ACTIVE']:
        messages.error(request, f'Task "{task.title}" is already assigned to {task.sprint.name}!')
        return redirect('product_backlog')
    
    # Move task to sprint
    task.sprint = sprint
    task.status = 'SPRINT'
    task.sprint_progress = 'NOT_STARTED'
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

@staff_member_required
def complete_sprint(request, sprint_pk):
    sprint = Sprint.objects.get(pk=sprint_pk)
    
    # Only ACTIVE sprints can be completed
    if sprint.status != 'ACTIVE':
        messages.error(request, f'Only active sprints can be completed. {sprint.name} is {sprint.get_status_display()}.')
        return redirect('sprint_board', sprint_pk=sprint.pk)
    
    # Get task counts
    all_tasks = Task.objects.filter(sprint=sprint)
    done_tasks = all_tasks.filter(sprint_progress='DONE')
    unfinished_tasks = all_tasks.exclude(sprint_progress='DONE')
    
    if request.method == 'POST':
        # Get user's choice for unfinished tasks
        unfinished_action = request.POST.get('unfinished_action')
        target_sprint_id = request.POST.get('target_sprint')
        mark_review_as_done = request.POST.get('mark_review_as_done') == 'on'

        if mark_review_as_done:
            in_review_tasks = all_tasks.filter(sprint_progress='IN_REVIEW')

            for task in in_review_tasks:
                task.sprint_progress = 'DONE'
                task.save()
            done_tasks = all_tasks.filter(sprint_progress='DONE')
            unfinished_tasks = all_tasks.exclude(sprint_progress='DONE')
        
        # Handle DONE tasks - mark as complete
        for task in done_tasks:
            task.status = 'COMPLETE'
            task.sprint_progress = None 
            task.save()
        
    # Handle any unfinished tasks
        # Move to the product backlog
        if unfinished_action == 'backlog':
            for task in unfinished_tasks:
                task.sprint = None
                task.status = 'BACKLOG'
                task.sprint_progress = None
                task.save()
            unfinished_msg = "returned to Product Backlog"
            
        elif unfinished_action == 'sprint' and target_sprint_id:
            
            # Move to another sprint
            target_sprint = Sprint.objects.get(pk=target_sprint_id)
            for task in unfinished_tasks:
                task.sprint = target_sprint
                task.status = 'SPRINT'
                task.sprint_progress = 'NOT_STARTED'
                task.save()
            unfinished_msg = f"moved to {target_sprint.name}"
        else:
            messages.error(request, 'Please select where to move unfinished tasks.')
            return redirect('complete_sprint_confirm', sprint_pk=sprint.pk)
        
        # Complete the sprint
        sprint.status = 'COMPLETE'
        if not sprint.end_date:
            sprint.end_date = timezone.now().date()
        sprint.save()
        
        messages.success(
            request,
            f'{sprint.name} completed! {done_tasks.count()} tasks marked complete, '
            f'{unfinished_tasks.count()} tasks {unfinished_msg}.'
        )
        
        return redirect('sprint_backlog')
    
    # Get available sprints
    available_sprints = Sprint.objects.filter(
        status__in=['PLANNING', 'ACTIVE']
    ).exclude(pk=sprint.pk).order_by('-created_at')

    # Get tasks by status 
    in_review_tasks = all_tasks.filter(sprint_progress='IN_REVIEW')
    
    context = {
        'sprint': sprint,
        'all_tasks': all_tasks,
        'done_tasks': done_tasks,
        'unfinished_tasks': unfinished_tasks,
        'in_review_tasks': in_review_tasks,
        'available_sprints': available_sprints,
    }
    
    return render(request, 'main/complete_sprint.html', context)