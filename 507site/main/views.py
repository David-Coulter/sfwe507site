from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from django.db import models
from main.models import Task, Comment, TaskHistory, Sprint, TimeEntry
from .forms import TaskForm, CommentForm, RegisterForm, SprintForm, TimeEntryForm
from django.template.loader import render_to_string
from collections import defaultdict
from django.contrib.auth.forms import SetPasswordForm
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
except ImportError:
    HTML = None
    CSS = None
    FontConfiguration = None
except OSError:
    HTML = None
    CSS = None
    FontConfiguration = None
import csv
import json


def log_task_history(task, field_changed, old_value, new_value, changed_by, notes=''):
    old_value = '' if old_value is None else str(old_value)
    new_value = '' if new_value is None else str(new_value)

    if old_value != new_value or notes:
        TaskHistory.objects.create(
            task=task,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            notes=notes
        )

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

def password_reset_demo_confirm(request):
    user = User.objects.first()

    if not user:
        messages.error(request, "No user available for password reset.")
        return redirect('login')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Your password has been reset successfully.'
            )
            return redirect('password_reset_complete')

    else:
        form = SetPasswordForm(user)

    return render(
        request,
        'registration/password_reset_confirm.html',
        {
            'form': form
        }
    )
    
@login_required
def dashboard(request):
    backlog_count = Task.objects.filter(status='BACKLOG').count()
    sprint_count = Task.objects.filter(status='SPRINT').count()
    testing_count = Task.objects.filter(status='TESTING').count()
    complete_count = Task.objects.filter(status='COMPLETE').count()

    my_tasks = Task.objects.filter(assigned_to=request.user).exclude(status='COMPLETE')

    active_sprint = Sprint.objects.filter(status='ACTIVE').first()

    active_sprint_tasks = Task.objects.none()
    active_sprint_total_tasks = 0
    active_sprint_complete_tasks = 0
    active_sprint_testing_tasks = 0
    
    testing_attention_tasks = Task.objects.filter(
        status='TESTING'
    ).order_by('moved_to_testing_at')[:5]

    if active_sprint:
        active_sprint_tasks = Task.objects.filter(sprint=active_sprint)
        active_sprint_total_tasks = active_sprint_tasks.count()
        active_sprint_complete_tasks = active_sprint_tasks.filter(status='COMPLETE').count()
        active_sprint_testing_tasks = active_sprint_tasks.filter(status='TESTING').count()

    context = {
        'backlog_count': backlog_count,
        'sprint_count': sprint_count,
        'testing_count': testing_count,
        'complete_count': complete_count,
        'my_tasks': my_tasks,
        'active_sprint': active_sprint,
        'active_sprint_total_tasks': active_sprint_total_tasks,
        'active_sprint_complete_tasks': active_sprint_complete_tasks,
        'active_sprint_testing_tasks': active_sprint_testing_tasks,
        'testing_attention_tasks': testing_attention_tasks,
    }
    return render(request, 'main/dashboard.html', context)
    
@login_required
def log_time_entry(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if task.assigned_to != request.user:
        messages.error(request, "Only the assigned user can log time.")
        return redirect('task_detail', pk=task.pk)

    if request.method == 'POST':
        form = TimeEntryForm(request.POST)

        if form.is_valid():
            entry = form.save(commit=False)
            entry.task = task
            entry.user = request.user
            entry.save()

            messages.success(request, "Time entry logged successfully.")
            return redirect('task_detail', pk=task.pk)

    else:
        form = TimeEntryForm()

    return render(
        request,
        'main/log_time_entry.html',
        {
            'task': task,
            'form': form
        }
    )


@login_required
def create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.status = 'BACKLOG'
            task.save()
            form.save_m2m()

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
    history = task.history.all()[:50]

    context = {
        'task': task,
        'page_title': 'Task Details',
        'comment_form': comment_form,
        'comments': comments,
        'history': history,
    }
    return render(request, 'main/task_detail.html', context)


@login_required
def edit_task(request, pk):
    task = Task.objects.get(pk=pk)

    if request.method == 'POST':
        old_data = {
            'Title': task.title,
            'Description': task.description,
            'Priority': task.get_priority_display(),
            'Assigned To': task.assigned_to.username if task.assigned_to else '',
            'Story Points': task.story_points if task.story_points is not None else '',
            'Estimated Hours': task.estimated_hours if task.estimated_hours is not None else '',
            'Status': task.get_status_display(),
            'Sprint': task.sprint.name if task.sprint else '',
            'Sprint Progress': task.get_sprint_progress_display() if task.sprint_progress else '',
        }

        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            updated_task = form.save(commit=False)

            old_sprint = task.sprint
            new_sprint = form.cleaned_data.get('sprint')

            if new_sprint and not old_sprint:
                updated_task.status = 'SPRINT'
                updated_task.sprint_progress = 'NOT_STARTED'
            elif new_sprint and old_sprint and new_sprint != old_sprint:
                updated_task.status = 'SPRINT'
                if not updated_task.sprint_progress:
                    updated_task.sprint_progress = 'NOT_STARTED'
            elif not new_sprint and old_sprint:
                updated_task.status = 'BACKLOG'
                updated_task.sprint_progress = None

            updated_task.save()
            form.save_m2m()

            new_data = {
                'Title': updated_task.title,
                'Description': updated_task.description,
                'Priority': updated_task.get_priority_display(),
                'Assigned To': updated_task.assigned_to.username if updated_task.assigned_to else '',
                'Story Points': updated_task.story_points if updated_task.story_points is not None else '',
                'Estimated Hours': updated_task.estimated_hours if updated_task.estimated_hours is not None else '',
                'Status': updated_task.get_status_display(),
                'Sprint': updated_task.sprint.name if updated_task.sprint else '',
                'Sprint Progress': updated_task.get_sprint_progress_display() if updated_task.sprint_progress else '',
            }

            for field in old_data:
                log_task_history(
                    task=updated_task,
                    field_changed=field,
                    old_value=old_data[field],
                    new_value=new_data[field],
                    changed_by=request.user
                )

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

            old_description = task.description
            new_description = data.get('description', '')

            task.description = new_description
            task.save()

            log_task_history(
                task=task,
                field_changed='Description',
                old_value=old_description,
                new_value=new_description,
                changed_by=request.user
            )

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def product_backlog(request):
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

    all_sprint_tasks = list(
        Task.objects.filter(sprint=sprint, status='SPRINT').order_by('priority', '-created_at')
    )

    not_started_tasks = [t for t in all_sprint_tasks if not t.sprint_progress or t.sprint_progress == 'NOT_STARTED']
    in_progress_tasks = [t for t in all_sprint_tasks if t.sprint_progress == 'IN_PROGRESS']
    in_review_tasks = [t for t in all_sprint_tasks if t.sprint_progress == 'IN_REVIEW']
    done_tasks = [t for t in all_sprint_tasks if t.sprint_progress == 'DONE']

    not_started_points = sum(t.story_points for t in not_started_tasks)
    in_progress_points = sum(t.story_points for t in in_progress_tasks)
    in_review_points = sum(t.story_points for t in in_review_tasks)
    done_points = sum(t.story_points for t in done_tasks)

    total_tasks = len(all_sprint_tasks)
    total_story_points = sum(t.story_points for t in all_sprint_tasks)

    completed_tasks_list = [t for t in all_sprint_tasks if t.sprint_progress == 'DONE']
    completed_tasks = len(completed_tasks_list)
    completed_story_points = sum(t.story_points for t in completed_tasks_list)

    context = {
        'sprint': sprint,
        'sprint_tasks': all_sprint_tasks,
        'not_started_tasks': not_started_tasks,
        'in_progress_tasks': in_progress_tasks,
        'in_review_tasks': in_review_tasks,
        'done_tasks': done_tasks,
        'not_started_points': not_started_points,
        'in_progress_points': in_progress_points,
        'in_review_points': in_review_points,
        'done_points': done_points,
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


@staff_member_required
def complete_sprint(request, sprint_pk):
    sprint = Sprint.objects.get(pk=sprint_pk)

    if sprint.status != 'ACTIVE':
        messages.error(request, f'Only active sprints can be completed. {sprint.name} is {sprint.get_status_display()}.')
        return redirect('sprint_board', sprint_pk=sprint.pk)
    
    today = timezone.now().date()
    if sprint.end_date and today < sprint.end_date:
        days_remaining = (sprint.end_date - today).days
        messages.error(
            request, 
            f'Cannot complete {sprint.name} yet. The sprint ends on {sprint.end_date.strftime("%B %d, %Y")} '
            f'({days_remaining} day{"s" if days_remaining != 1 else ""} remaining). '
            f'Please wait until the sprint end date or update the sprint dates if needed.'
        )
        return redirect('sprint_board', sprint_pk=sprint.pk)

    all_tasks = Task.objects.filter(sprint=sprint)
    done_tasks = all_tasks.filter(sprint_progress='DONE')
    unfinished_tasks = all_tasks.exclude(sprint_progress='DONE')

    if request.method == 'POST':
        unfinished_action = request.POST.get('unfinished_action')
        target_sprint_id = request.POST.get('target_sprint')
        mark_review_as_done = request.POST.get('mark_review_as_done') == 'on'

        if mark_review_as_done:
            in_review_tasks = all_tasks.filter(sprint_progress='IN_REVIEW')
            for task in in_review_tasks:
                old_progress = task.get_sprint_progress_display() if task.sprint_progress else ''
                task.sprint_progress = 'DONE'
                task.save()
                log_task_history(
                    task=task,
                    field_changed='Sprint Progress',
                    old_value=old_progress,
                    new_value=task.get_sprint_progress_display(),
                    changed_by=request.user
                )

            done_tasks = all_tasks.filter(sprint_progress='DONE')
            unfinished_tasks = all_tasks.exclude(sprint_progress='DONE')

        for task in done_tasks:
            old_status = task.get_status_display()
            old_progress = task.get_sprint_progress_display() if task.sprint_progress else ''

            task.status = 'COMPLETE'
            task.sprint_progress = None
            task.completed_at = timezone.now()
            task.save()

            log_task_history(task, 'Status', old_status, task.get_status_display(), request.user)
            log_task_history(task, 'Sprint Progress', old_progress, '', request.user)

        if unfinished_action == 'backlog':
            for task in unfinished_tasks:
                old_sprint = task.sprint.name if task.sprint else ''
                old_status = task.get_status_display()
                old_progress = task.get_sprint_progress_display() if task.sprint_progress else ''

                task.sprint = None
                task.status = 'BACKLOG'
                task.sprint_progress = None
                task.save()

                log_task_history(task, 'Sprint', old_sprint, '', request.user)
                log_task_history(task, 'Status', old_status, task.get_status_display(), request.user)
                log_task_history(task, 'Sprint Progress', old_progress, '', request.user)

            unfinished_msg = "returned to Product Backlog"

        elif unfinished_action == 'sprint' and target_sprint_id:
            target_sprint = Sprint.objects.get(pk=target_sprint_id)
            for task in unfinished_tasks:
                old_sprint = task.sprint.name if task.sprint else ''
                old_status = task.get_status_display()
                old_progress = task.get_sprint_progress_display() if task.sprint_progress else ''

                task.sprint = target_sprint
                task.status = 'SPRINT'
                task.sprint_progress = 'NOT_STARTED'
                task.save()

                log_task_history(task, 'Sprint', old_sprint, target_sprint.name, request.user)
                log_task_history(task, 'Status', old_status, task.get_status_display(), request.user)
                log_task_history(task, 'Sprint Progress', old_progress, task.get_sprint_progress_display(), request.user)

            unfinished_msg = f"moved to {target_sprint.name}"
        else:
            messages.error(request, 'Please select where to move unfinished tasks.')
            return redirect('complete_sprint', sprint_pk=sprint.pk)

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

    available_sprints = Sprint.objects.filter(
        status__in=['PLANNING', 'ACTIVE']
    ).exclude(pk=sprint.pk).order_by('-created_at')

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

@staff_member_required
def reopen_sprint(request, sprint_pk):
    sprint = get_object_or_404(Sprint, pk=sprint_pk)
    
    if sprint.status != 'COMPLETE':
        messages.error(request, f'{sprint.name} is not completed, cannot reopen.')
        return redirect('sprint_backlog')
    
    if request.method == 'POST':
        # Revert sprint status
        sprint.status = 'ACTIVE'
        sprint.save()
    
        # Find tasks that were marked complete during this sprint completion and change them back to the SPRINT status
        completed_tasks = Task.objects.filter(
            sprint=sprint,
            status='COMPLETE'
        )

        tasks_reverted = 0
                
        for task in completed_tasks:
            old_tasks_status = task.get_status_display()
            task.status = 'SPRINT'
            task.sprint_progress = 'DONE'
            task.completed_at = None
            task.save()

            log_task_history(
                task=task,
                field_changed='Status',
                old_value=old_tasks_status,
                new_value=task.get_status_display(),
                changed_by=request.user,
                notes=f'Sprint {sprint.name} was reopened'
            )

            tasks_reverted += 1
        
        messages.warning(
            request,
            f'{sprint.name} has been reopened. {tasks_reverted} task{"s" if tasks_reverted != 1 else ""} '
            f'reverted to SPRINT status with DONE progress.'
        )
        return redirect('sprint_board', sprint_pk=sprint.pk)
    
    completed_tasks = Task.objects.filter(
        sprint=sprint,
        status='COMPLETE'
    )

    context = {
        'sprint': sprint,
        'completed_tasks': completed_tasks.count(),
    }

    return render(request, 'main/reopen_sprint_confirm.html', context)

@login_required
def move_to_sprint(request, task_pk, sprint_pk):
    task = Task.objects.get(pk=task_pk)
    sprint = Sprint.objects.get(pk=sprint_pk)

    if task.sprint and task.sprint.status in ['PLANNING', 'ACTIVE']:
        messages.error(request, f'Task "{task.title}" is already assigned to {task.sprint.name}!')
        return redirect('product_backlog')

    old_sprint = task.sprint.name if task.sprint else ''
    old_status = task.get_status_display()
    old_progress = task.get_sprint_progress_display() if task.sprint_progress else ''

    task.sprint = sprint
    task.status = 'SPRINT'
    task.sprint_progress = 'NOT_STARTED'
    task.save()

    log_task_history(task, 'Sprint', old_sprint, sprint.name, request.user)
    log_task_history(task, 'Status', old_status, task.get_status_display(), request.user)
    log_task_history(task, 'Sprint Progress', old_progress, task.get_sprint_progress_display(), request.user)

    Comment.objects.create(
        task=task,
        author=request.user,
        text=f'Task moved to {sprint.name}'
    )

    messages.success(request, f'Task "{task.title}" moved to {sprint.name}!')

    return redirect('product_backlog')


@login_required
def update_sprint_progress(request, task_pk, new_progress):
    task = Task.objects.get(pk=task_pk)

    if task.status != 'SPRINT':
        messages.error(request, 'Task must be in sprint to update sprint progress!')
        return redirect('task_detail', pk=task.pk)

    valid_progress = ['NOT_STARTED', 'IN_PROGRESS', 'IN_REVIEW', 'DONE']
    if new_progress not in valid_progress:
        messages.error(request, 'Invalid sprint progress!')
        return redirect('task_detail', pk=task.pk)

    old_progress = task.get_sprint_progress_display() if task.sprint_progress else ''
    task.sprint_progress = new_progress
    task.save()

    log_task_history(
        task=task,
        field_changed='Sprint Progress',
        old_value=old_progress,
        new_value=task.get_sprint_progress_display(),
        changed_by=request.user
    )

    Comment.objects.create(
        task=task,
        author=request.user,
        text=f"Task moved from {old_progress or 'Not Started'} to {task.get_sprint_progress_display()} by {request.user.username}"
    )

    messages.success(request, f'Task moved from {old_progress or "Not Started"} to {task.get_sprint_progress_display()}!')

    return redirect('sprint_board', sprint_pk=task.sprint.pk)

@login_required
def sprint_burndown(request, sprint_pk):
    sprint = get_object_or_404(Sprint, pk=sprint_pk)

    # Get all tasks in SPRINT status
    all_sprints = Sprint.objects.all().order_by('-created_at')
    
    #Validate that the sprint has dates
    if not sprint.start_date or not sprint.end_date:
        context = {
            'sprint': sprint,
            'all_sprints': all_sprints,
            'error': 'Sprint must have start and end dates to view the display the sprint burdown chart.'}
        
        return render(request, 'main/sprint_burndown.html', context)
    
    # Calculate metrics
    total_story_points = Task.objects.filter(sprint=sprint).aggregate(
        total=models.Sum('story_points')
    )['total'] or 0

    # Create the date range for the sprint
    current_date = sprint.start_date
    sprint_days = []
    while current_date <= sprint.end_date:
        sprint_days.append(current_date)
        current_date += timedelta(days=1)

    total_days = len(sprint_days)

    # Calculate the ideal burndown
    ideal_burndown = []
    if total_days > 0:
        daily_decrease = total_story_points / total_days
        for i, day in enumerate(sprint_days):
            remaining = total_story_points - (daily_decrease * (i + 1))
            ideal_burndown.append(max(0, remaining))

    #Calculate the actual burndown based on the task completion
    actual_burndown = []

    for day in sprint_days:
        day_end = datetime.combine(day, datetime.max.time())
        day_end = timezone.make_aware(day_end) if timezone.is_naive(day_end) else day_end

        completed_points = Task.objects.filter(
            sprint=sprint,
            status='COMPLETE',
            completed_at__lte=day_end
        ).aggregate(total=models.Sum('story_points'))['total'] or 0

        remaining = total_story_points - completed_points
        actual_burndown.append(max(0, remaining))
        
    chart_labels = [day.strftime('%b %d') for day in sprint_days]

    weekend_indices = [i for i, day in enumerate(sprint_days) if day.weekday() >= 5]

    today = timezone.now().date()
    status = 'on-track'
    status_message = ''

    if today < sprint.start_date:
        # Sprint hasn't started yet
        status = 'not-started'
        days_until_start = (sprint.start_date - today).days
        status_message = f'Sprint has not started yet. It begins in {days_until_start} day{"s" if days_until_start != 1 else ""}.'

    elif today > sprint.end_date:
        # Sprint is complete
        status = 'completed'
        final_remaining = actual_burndown[-1] if actual_burndown else 0
        
        if final_remaining == 0:
            status_message = f'Sprint completed successfully! All {total_story_points} story points were delivered. 🎉'
        else:
            completed_points = total_story_points - final_remaining
            completion_rate = (completed_points / total_story_points * 100) if total_story_points > 0 else 0
            status_message = f'Sprint completed. Delivered {int(completed_points)} of {total_story_points} story points ({completion_rate:.1f}% completion).'

    else:
        # Sprint is active
        days_elapsed = (today - sprint.start_date).days
        if days_elapsed < len(ideal_burndown) and days_elapsed < len(actual_burndown):
            ideal_at_today = ideal_burndown[days_elapsed]
            actual_at_today = actual_burndown[days_elapsed]
            
            if actual_at_today > ideal_at_today + 5:  # 5 point buffer
                status = 'behind'
                status_message = f'Sprint is behind schedule by approximately {int(actual_at_today - ideal_at_today)} story points.'
            elif actual_at_today < ideal_at_today - 5:
                status = 'ahead'
                status_message = f'Sprint is ahead of schedule by approximately {int(ideal_at_today - actual_at_today)} story points.'
            else:
                status = 'on-track'
                status_message = 'Sprint is on track!'

    # Calculate sprint statistics
    completed_tasks = Task.objects.filter(sprint=sprint, status='COMPLETE').count()
    total_tasks = Task.objects.filter(sprint=sprint).count()
    completion_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0

    context = {
        'sprint': sprint,
        'all_sprints': all_sprints,
        'total_story_points': total_story_points,
        'completed_tasks': completed_tasks,
        'total_tasks': total_tasks,
        'completion_percentage': round(completion_percentage, 1),
        'chart_labels': json.dumps(chart_labels),
        'ideal_burndown': json.dumps(ideal_burndown),
        'actual_burndown': json.dumps(actual_burndown),
        'weekend_indices': json.dumps(weekend_indices),
        'status': status,
        'status_message': status_message
    }

    return render(request, 'main/sprint_burndown.html', context)  

@login_required
def testing_queue(request):
    if not request.user.groups.filter(name='Testing Manager').exists():
        messages.error(request, 'You must be a Testing Manager to access the Testing Queue.')
        return redirect('dashboard')
    
    # Get all tasks in TESTING status
    testing_tasks = Task.objects.filter(status='TESTING').select_related('assigned_to', 'sprint').order_by('-priority', 'moved_to_testing_at')
    
    # Calculate metrics
    now = timezone.now()
    for task in testing_tasks:
        if task.moved_to_testing_at:
            delta = now - task.moved_to_testing_at
            task.hours_in_testing = int(delta.total_seconds() / 3600)
            task.days_in_testing = delta.days
        else:
            task.days_in_testing = 0
            task.hours_in_testing = 0

    total_tasks = testing_tasks.count()
    total_story_points = sum(task.story_points for task in testing_tasks)

    sprints_with_tasks = {}
    for task in testing_tasks:
        sprint_name = task.sprint.name if task.sprint else 'No Sprint'
        if sprint_name not in sprints_with_tasks:
            sprints_with_tasks[sprint_name] = []
        sprints_with_tasks[sprint_name].append(task)

    context = {
        'testing_tasks': testing_tasks,
        'sprints_with_tasks': sprints_with_tasks,
        'total_tasks': total_tasks,
        'total_story_points': total_story_points,
    }

    return render(request, 'main/testing_queue.html', context)


@login_required
def mark_ready_for_test(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    # Only tasks in SPRINT status can be marked ready for test
    if task.status != 'SPRINT':
        messages.error(request, f'Task "{task.title}" must be in Sprint to mark ready for test.')
        return redirect('task_detail', pk=task.pk)

    old_status = task.get_status_display()
    old_progress = task.get_sprint_progress_display() if task.sprint_progress else ''

    task.status = 'TESTING'
    task.sprint_progress = None
    task.testing_started_at = timezone.now()
    task.moved_to_testing_at = timezone.now()
    task.save()

    log_task_history(task, 'Status', old_status, task.get_status_display(), request.user)
    log_task_history(task, 'Sprint Progress', old_progress, '', request.user)

    Comment.objects.create(
        task=task,
        author=request.user,
        text=f"Task marked as Ready for Test by {request.user.username}"
    )

    messages.success(request, f'Task "{task.title}" marked as Ready for Test!')

    return redirect('task_detail', pk=task.pk)


@login_required
def pass_testing(request, pk):
    if not request.user.groups.filter(name='Testing Manager').exists():
        messages.error(request, 'Only Testing Managers can pass tasks.')
        return redirect('task_detail', pk=pk)

    task = Task.objects.get(pk=pk)

    if task.status != 'TESTING':
        messages.error(request, f'Task "{task.title}" must be in Testing to mark as passed.')
        return redirect('task_detail', pk=task.pk)

    old_status = task.get_status_display()

    task.status = 'COMPLETE'
    task.completed_at = timezone.now()
    task.save()

    log_task_history(task, 'Status', old_status, task.get_status_display(), request.user)

    Comment.objects.create(
        task=task,
        author=request.user,
        text=f"Testing passed by {request.user.username}"
    )

    messages.success(request, f'Task "{task.title}" passed testing and is ready for release!')
    
    return redirect('testing_queue')

@login_required
def fail_testing(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if not request.user.groups.filter(name='Testing Manager').exists():
        messages.error(request, 'Only Testing Managers can fail tasks.')
        return redirect('task_detail', pk=task.pk)
    
    if task.status != 'TESTING':
        messages.error(request, f'Task "{task.title}" must be in Testing to mark as failed.')
        return redirect('task_detail', pk=task.pk)
    
    if request.method == 'POST':
        failure_reason = request.POST.get('failure_reason', '').strip()

        if not failure_reason:
            messages.error(request, 'Please provide a reason the test failed.')
            return redirect('testing_queue')
        
        # Store old values for history
        old_status = task.get_status_display()
        old_progress = task.get_sprint_progress_display() if task.sprint_progress else ''
        
        # Update task
        task.status = 'SPRINT'
        task.sprint_progress = 'IN_PROGRESS'
        task.failed_count += 1
        
        # Append failure notes
        failure_note = f"\n--- Failed Testing #{task.failed_count} on {timezone.now().strftime('%Y-%m-%d %H:%M')} ---\n{failure_reason}\n"
        task.testing_notes += failure_note
        task.moved_to_testing_at = None
        task.save()
        
        # Log task history
        log_task_history(
            task=task,
            field_changed='Status',
            old_value=old_status,
            new_value=task.get_status_display(),
            changed_by=request.user
        )
        
        log_task_history(
            task=task,
            field_changed='Sprint Progress',
            old_value=old_progress,
            new_value=task.get_sprint_progress_display(),
            changed_by=request.user
        )
        
        # Add comment
        Comment.objects.create(
            task=task,
            author=request.user,
            text=f"❌ Testing failed by {request.user.username}. Reason: {failure_reason}"
        )

        messages.warning(
            request, 
            f'Task "{task.title}" failed testing and returned to Sprint for rework. '
            f'Failed count: {task.failed_count}'
        )
        
        return redirect('testing_queue')

    return redirect('testing_queue')

@login_required
def completed_tasks(request):

    # Get all completed tasks
    tasks = Task.objects.filter(status='COMPLETE').select_related(
        'assigned_to', 'created_by', 'sprint'
    ).order_by('-completed_at')
    
    sprint_filter = request.GET.get('sprint', '')
    
    if sprint_filter:
        tasks = tasks.filter(sprint_id=sprint_filter)
    
    # Calculate metrics
    total_tasks = tasks.count()
    total_story_points = tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0
    
    # Get all sprints for filter dropdown
    sprints = Sprint.objects.all().order_by('-created_at')
    
    # Group tasks by sprint for display
    tasks_by_sprint = {}
    for task in tasks:
        sprint_name = task.sprint.name if task.sprint else 'No Sprint'
        if sprint_name not in tasks_by_sprint:
            tasks_by_sprint[sprint_name] = []
        tasks_by_sprint[sprint_name].append(task)
    
    context = {
        'tasks': tasks,
        'tasks_by_sprint': tasks_by_sprint,
        'total_tasks': total_tasks,
        'total_story_points': total_story_points,
        'sprints': sprints,
        'selected_sprint': sprint_filter,
    }
    
    return render(request, 'main/completed_tasks.html', context)

@login_required
def sprint_report(request, sprint_pk):
    sprint = get_object_or_404(Sprint, pk=sprint_pk)
    
    all_sprints = Sprint.objects.all().order_by('-created_at')

    all_tasks = Task.objects.filter(sprint=sprint). select_related('assigned_to', 'created_by')

    completed_tasks = all_tasks.filter(status='COMPLETE').order_by('-completed_at')
    incomplete_tasks = all_tasks.exclude(status='COMPLETE').order_by('priority', 'created_at')

    total_story_points = all_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0
    completed_story_points = completed_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0
    incomplete_story_points = total_story_points - completed_story_points
    
    completion_rate = (completed_story_points / total_story_points * 100) if total_story_points > 0 else 0

    status_breakdown = {
        'BACKLOG': all_tasks.filter(status='BACKLOG').count(),
        'SPRINT': all_tasks.filter(status='SPRINT').count(),
        'TESTING': all_tasks.filter(status='TESTING').count(),
        'COMPLETE': all_tasks.filter(status='COMPLETE').count(),
    }

    # Calculate team member contributions
    team_contributions = []

    # Get distinct assigned users
    assigned_user_ids = set(all_tasks.exclude(assigned_to__isnull=True).values_list('assigned_to', flat=True))

    for user_id in assigned_user_ids:
            user = User.objects.get(pk=user_id)
            
            member_tasks = all_tasks.filter(assigned_to=user)
            member_completed = member_tasks.filter(status='COMPLETE')
            
            team_contributions.append({
                'name': user.username,
                'total_tasks': member_tasks.count(),
                'completed_tasks': member_completed.count(),
                'total_points': member_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0,
                'completed_points': member_completed.aggregate(Sum('story_points'))['story_points__sum'] or 0,
            })

    # Sort team contributions by completed story points
    team_contributions.sort(key=lambda x: x['completed_points'], reverse=True)

    # Calculate velocity
    velocity = completed_story_points if sprint.status == 'COMPLETE' else None

    # Create the chart 
    chart_labels = []
    chart_data = []
    chart_colors = []

    status_colors = {
        'COMPLETE': '#28a745',
        'TESTING': '#17a2b8',  
        'SPRINT': '#ffc107',    
        'BACKLOG': '#6c757d', 
    }

    for status, count in status_breakdown.items():
        if count > 0:
            chart_labels.append(status.capitalize())
            chart_data.append(count)
            chart_colors.append(status_colors.get(status, '#6c757d'))
    
    context = {
        'sprint': sprint,
        'all_sprints': all_sprints,
        'all_tasks': all_tasks,
        'completed_tasks': completed_tasks,
        'incomplete_tasks': incomplete_tasks,
        'total_story_points': total_story_points,
        'completed_story_points': completed_story_points,
        'incomplete_story_points': incomplete_story_points,
        'completion_rate': round(completion_rate, 1),
        'status_breakdown': status_breakdown,
        'team_contributions': team_contributions,
        'velocity': velocity,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'chart_colors': json.dumps(chart_colors),
    }
    
    return render(request, 'main/sprint_report.html', context)

@login_required
def export_sprint_report_csv(request, sprint_pk):
    sprint = get_object_or_404(Sprint, pk=sprint_pk)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sprint_report_{sprint.name.replace(" ", "_")}.csv"'
    
    writer = csv.writer(response)
    
    # Sprint Summary
    writer.writerow(['Sprint Report'])
    writer.writerow(['Sprint Name', sprint.name])
    writer.writerow(['Status', sprint.get_status_display()])
    if sprint.start_date and sprint.end_date:
        writer.writerow(['Start Date', sprint.start_date.strftime('%Y-%m-%d')])
        writer.writerow(['End Date', sprint.end_date.strftime('%Y-%m-%d')])
    if sprint.goal:
        writer.writerow(['Goal', sprint.goal])
    writer.writerow([])
    
    # Story Points Summary
    all_tasks = Task.objects.filter(sprint=sprint)
    completed_tasks = all_tasks.filter(status='COMPLETE')
    
    total_points = all_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0
    completed_points = completed_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0
    
    writer.writerow(['Story Points Summary'])
    writer.writerow(['Total Planned', total_points])
    writer.writerow(['Completed', completed_points])
    writer.writerow(['Incomplete', total_points - completed_points])
    writer.writerow(['Completion Rate', f"{(completed_points/total_points*100):.1f}%" if total_points > 0 else "0%"])
    writer.writerow([])
    
    # Completed Tasks
    writer.writerow(['Completed Tasks'])
    writer.writerow(['Title', 'Story Points', 'Priority', 'Assigned To', 'Completed At'])
    for task in completed_tasks.order_by('-completed_at'):
        writer.writerow([
            task.title,
            task.story_points,
            task.get_priority_display(),
            task.assigned_to.username if task.assigned_to else 'Unassigned',
            task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else 'N/A'
        ])
    writer.writerow([])
    
    # Incomplete Tasks
    incomplete_tasks = all_tasks.exclude(status='COMPLETE')
    if incomplete_tasks.exists():
        writer.writerow(['Incomplete Tasks'])
        writer.writerow(['Title', 'Story Points', 'Priority', 'Status', 'Assigned To'])
        for task in incomplete_tasks.order_by('priority'):
            writer.writerow([
                task.title,
                task.story_points,
                task.get_priority_display(),
                task.get_status_display(),
                task.assigned_to.username if task.assigned_to else 'Unassigned'
            ])
        writer.writerow([])
    
    # Team Contributions
    writer.writerow(['Team Member Contributions'])
    writer.writerow(['Team Member', 'Total Tasks', 'Completed Tasks', 'Total Points', 'Completed Points'])
    
    team_members = all_tasks.values('assigned_to').distinct()
    for member in team_members:
        if member['assigned_to']:
            user = User.objects.get(pk=member['assigned_to'])
            
            member_tasks = all_tasks.filter(assigned_to=user)
            member_completed = member_tasks.filter(status='COMPLETE')
            
            writer.writerow([
                user.username,
                member_tasks.count(),
                member_completed.count(),
                member_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0,
                member_completed.aggregate(Sum('story_points'))['story_points__sum'] or 0,
            ])
    
    return response
 
 
@login_required
def export_sprint_report_pdf(request, sprint_pk):
    
    sprint = get_object_or_404(Sprint, pk=sprint_pk)
    
    # Get all the same data as the regular report
    all_tasks = Task.objects.filter(sprint=sprint).select_related('assigned_to', 'created_by')
    completed_tasks = all_tasks.filter(status='COMPLETE').order_by('-completed_at')
    incomplete_tasks = all_tasks.exclude(status='COMPLETE').order_by('priority', '-created_at')
    
    total_story_points = all_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0
    completed_story_points = completed_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0
    completion_rate = (completed_story_points / total_story_points * 100) if total_story_points > 0 else 0
    
    # Team contributions
    team_contributions = []
    team_members = all_tasks.values('assigned_to').distinct()
    
    for member in team_members:
        if member['assigned_to']:
            user = User.objects.get(pk=member['assigned_to'])
            
            member_tasks = all_tasks.filter(assigned_to=user)
            member_completed = member_tasks.filter(status='COMPLETE')
            
            team_contributions.append({
                'name': user.username,
                'total_tasks': member_tasks.count(),
                'completed_tasks': member_completed.count(),
                'total_points': member_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0,
                'completed_points': member_completed.aggregate(Sum('story_points'))['story_points__sum'] or 0,
            })
    
    team_contributions.sort(key=lambda x: x['completed_points'], reverse=True)
    
    context = {
        'sprint': sprint,
        'completed_tasks': completed_tasks,
        'incomplete_tasks': incomplete_tasks,
        'total_story_points': total_story_points,
        'completed_story_points': completed_story_points,
        'completion_rate': round(completion_rate, 1),
        'team_contributions': team_contributions,
        'generated_date': timezone.now(),
    }
    
    # Render HTML template
    html_string = render_to_string('main/sprint_report_pdf.html', context)
    
    # Create PDF
    font_config = FontConfiguration()
    html = HTML(string=html_string)
    
    # Generate PDF
    pdf = html.write_pdf(font_config=font_config)
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sprint_report_{sprint.name.replace(" ", "_")}.pdf"'
    
    return response

@login_required
def email_sprint_report(request, sprint_pk):

    if request.method != 'POST':
        return redirect('sprint_report', sprint_pk=sprint_pk)
    
    sprint = get_object_or_404(Sprint, pk=sprint_pk)
    
    # Get email addresses
    recipient_emails = request.POST.get('recipient_email', '').strip()
    if not recipient_emails:
        messages.error(request, 'Please provide at least one recipient email address.')
        return redirect('sprint_report', sprint_pk=sprint_pk)
    
    recipients = [email.strip() for email in recipient_emails.split(',')]
    
    # Get email message
    user_message = request.POST.get('email_message', '').strip()
    
    try:
        # Get report data
        all_tasks = Task.objects.filter(sprint=sprint).select_related('assigned_to', 'created_by')
        completed_tasks = all_tasks.filter(status='COMPLETE').order_by('-completed_at')
        incomplete_tasks = all_tasks.exclude(status='COMPLETE').order_by('priority')
        
        total_story_points = all_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0
        completed_story_points = completed_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0
        completion_rate = (completed_story_points / total_story_points * 100) if total_story_points > 0 else 0
        
        # Team contributions
        team_contributions = []
        team_members = all_tasks.values('assigned_to').distinct()
        
        for member in team_members:
            if member['assigned_to']:
                user = User.objects.get(pk=member['assigned_to'])
                
                member_tasks = all_tasks.filter(assigned_to=user)
                member_completed = member_tasks.filter(status='COMPLETE')
                
                team_contributions.append({
                    'name': user.username,
                    'total_tasks': member_tasks.count(),
                    'completed_tasks': member_completed.count(),
                    'total_points': member_tasks.aggregate(Sum('story_points'))['story_points__sum'] or 0,
                    'completed_points': member_completed.aggregate(Sum('story_points'))['story_points__sum'] or 0,
                })
        
        team_contributions.sort(key=lambda x: x['completed_points'], reverse=True)
        
        context = {
            'sprint': sprint,
            'completed_tasks': completed_tasks,
            'incomplete_tasks': incomplete_tasks,
            'total_story_points': total_story_points,
            'completed_story_points': completed_story_points,
            'completion_rate': round(completion_rate, 1),
            'team_contributions': team_contributions,
            'generated_date': timezone.now(),
        }
        
        # Render PDF
        html_string = render_to_string('main/sprint_report_pdf.html', context)
        font_config = FontConfiguration()
        html = HTML(string=html_string)
        pdf = html.write_pdf(font_config=font_config)
        
        # Create email
        subject = f'Sprint Report: {sprint.name}'
        
        # Email body
        body = f"""
            Sprint Report: {sprint.name}
            
            Sprint Summary:
            - Status: {sprint.get_status_display()}
            - Story Points Completed: {completed_story_points}/{total_story_points} ({completion_rate:.1f}%)
            - Tasks Completed: {completed_tasks.count()}/{all_tasks.count()}
            """
        
        if sprint.start_date and sprint.end_date:
            body += f"- Duration: {sprint.start_date.strftime('%B %d, %Y')} - {sprint.end_date.strftime('%B %d, %Y')}\n"
        
        if sprint.goal:
            body += f"\nSprint Goal:\n{sprint.goal}\n"
        
        if user_message:
            body += f"\n---\nMessage from {request.user.username}:\n{user_message}\n"
        
        body += f"""
            ---
            See attached PDF for complete sprint report.
            
            Generated by PDMS - Project Development Management System
            """
        
        # Create email with PDF attachment
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
            reply_to=[request.user.email] if request.user.email else None,
        )
        
        # Attach PDF
        email.attach(
            f'sprint_report_{sprint.name.replace(" ", "_")}.pdf',
            pdf,
            'application/pdf'
        )
        
        # Send email
        email.send(fail_silently=False)
        
        messages.success(
            request,
            f'Sprint report emailed successfully to {len(recipients)} recipient(s)!'
        )
        
    except Exception as e:
        messages.error(
            request,
            f'Failed to send email: {str(e)}. Please check your email configuration.'
        )
    
    return redirect('sprint_report', sprint_pk=sprint_pk)