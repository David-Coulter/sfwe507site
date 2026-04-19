from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from .models import Task, Comment, TaskHistory, Sprint
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
    backlog_count = Task.objects.filter(status='BACKLOG').count()
    sprint_count = Task.objects.filter(status='SPRINT').count()
    testing_count = Task.objects.filter(status='TESTING').count()
    complete_count = Task.objects.filter(status='COMPLETE').count()

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
        old_data = {
            'Title': task.title,
            'Description': task.description,
            'Priority': str(task.priority),
            'Assigned To': task.assigned_to.username if task.assigned_to else '',
            'Story Points': str(task.story_points) if task.story_points is not None else '',
            'Estimated Hours': str(task.estimated_hours) if task.estimated_hours is not None else '',
            'Status': task.status,
            'Sprint': task.sprint.name if task.sprint else '',
            'Sprint Progress': task.sprint_progress or '',
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
                'Priority': str(updated_task.priority),
                'Assigned To': updated_task.assigned_to.username if updated_task.assigned_to else '',
                'Story Points': str(updated_task.story_points) if updated_task.story_points is not None else '',
                'Estimated Hours': str(updated_task.estimated_hours) if updated_task.estimated_hours is not None else '',
                'Status': updated_task.status,
                'Sprint': updated_task.sprint.name if updated_task.sprint else '',
                'Sprint Progress': updated_task.sprint_progress or '',
            }

            for field in old_data:
                if old_data[field] != new_data[field]:
                    TaskHistory.objects.create(
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

            task.description = data.get('description')
            task.save()

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
                task.sprint_progress = 'DONE'
                task.save()
            done_tasks = all_tasks.filter(sprint_progress='DONE')
            unfinished_tasks = all_tasks.exclude(sprint_progress='DONE')

        for task in done_tasks:
            task.status = 'COMPLETE'
            task.sprint_progress = None
            task.save()

        if unfinished_action == 'backlog':
            for task in unfinished_tasks:
                task.sprint = None
                task.status = 'BACKLOG'
                task.sprint_progress = None
                task.save()
            unfinished_msg = "returned to Product Backlog"

        elif unfinished_action == 'sprint' and target_sprint_id:
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


@login_required
def move_to_sprint(request, task_pk, sprint_pk):
    task = Task.objects.get(pk=task_pk)
    sprint = Sprint.objects.get(pk=sprint_pk)

    if task.sprint and task.sprint.status in ['PLANNING', 'ACTIVE']:
        messages.error(request, f'Task "{task.title}" is already assigned to {task.sprint.name}!')
        return redirect('product_backlog')

    task.sprint = sprint
    task.status = 'SPRINT'
    task.sprint_progress = 'NOT_STARTED'
    task.save()

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

    old_progress = task.get_sprint_progress_display() if task.sprint_progress else 'Not Started'
    task.sprint_progress = new_progress
    task.save()

    Comment.objects.create(
        task=task,
        author=request.user,
        text=f"Task moved from {old_progress} to {task.get_sprint_progress_display()} by {request.user.username}"
    )

    messages.success(request, f'Task moved from {old_progress} to {task.get_sprint_progress_display()}!')

    return redirect('sprint_board', sprint_pk=task.sprint.pk)


@login_required
def testing_queue(request):
    if not request.user.groups.filter(name='Testing Manager').exists():
        messages.error(request, 'You must be a Testing Manager to access the Testing Queue.')
        return redirect('dashboard')

    testing_tasks = Task.objects.filter(status='TESTING').order_by('-updated_at')

    total_tasks = testing_tasks.count()
    total_story_points = sum(task.story_points for task in testing_tasks)

    sprints_with_tasks = {}
    for task in testing_tasks:
        if task.sprint:
            if task.sprint not in sprints_with_tasks:
                sprints_with_tasks[task.sprint] = []
            sprints_with_tasks[task.sprint].append(task)
        else:
            if 'No Sprint' not in sprints_with_tasks:
                sprints_with_tasks['No Sprint'] = []
            sprints_with_tasks['No Sprint'].append(task)

    context = {
        'testing_tasks': testing_tasks,
        'sprints_with_tasks': sprints_with_tasks,
        'total_tasks': total_tasks,
        'total_story_points': total_story_points,
    }

    return render(request, 'main/testing_queue.html', context)


@login_required
def mark_ready_for_test(request, pk):
    task = Task.objects.get(pk=pk)

    if task.status != 'SPRINT':
        messages.error(request, f'Task "{task.title}" must be in Sprint to mark ready for test.')
        return redirect('task_detail', pk=task.pk)

    task.status = 'TESTING'
    task.sprint_progress = None
    task.save()

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

    task.status = 'COMPLETE'
    task.completed_at = timezone.now()
    task.save()

    Comment.objects.create(
        task=task,
        author=request.user,
        text=f"Testing passed by {request.user.username}"
    )

    messages.success(request, f'Task "{task.title}" passed testing and is ready for release!')

    return redirect('testing_queue')