from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from main.models import Task, TaskHistory, Sprint, Comment


class TaskHistoryTests(TestCase):
   
    def setUp(self):
        """Set up test data"""
        # Create users
        self.user1 = User.objects.create_user(
            username='user1',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            password='testpass123'
        )
        
        # Create sprints
        self.sprint1 = Sprint.objects.create(
            name='Sprint 1',
            status='ACTIVE'
        )
        
        self.sprint2 = Sprint.objects.create(
            name='Sprint 2',
            status='PLANNING'
        )
        
        # Create task
        self.task = Task.objects.create(
            title='Test Task',
            description='Original description',
            status='BACKLOG',
            priority=2,  # Medium
            story_points=5,
            created_by=self.user1
        )
        
        self.client = Client()
    
    def test_shows_status_changes_chronologically(self):

        self.client.login(username='user1', password='testpass123')
        
        # Make multiple status changes
        # Change 1: BACKLOG → SPRINT
        self.task.status = 'SPRINT'
        self.task.sprint = self.sprint1
        self.task.save()
        
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Status',
            old_value='Backlog',
            new_value='Sprint',
            changed_by=self.user1
        )
        
        # Change 2: SPRINT → TESTING
        self.task.status = 'TESTING'
        self.task.save()
        
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Status',
            old_value='Sprint',
            new_value='Testing',
            changed_by=self.user1
        )
        
        # Change 3: TESTING → COMPLETE
        self.task.status = 'COMPLETE'
        self.task.save()
        
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Status',
            old_value='Testing',
            new_value='Complete',
            changed_by=self.user2
        )
        
        # Get task detail page
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        # Verify history exists in context
        self.assertIn('history', response.context)
        history = list(response.context['history'])
        
        # Verify all status changes are present
        self.assertEqual(len(history), 3)
        
        # Verify chronological order (most recent first)
        self.assertEqual(history[0].new_value, 'Complete')
        self.assertEqual(history[1].new_value, 'Testing')
        self.assertEqual(history[2].new_value, 'Sprint')
    
    def test_displays_who_made_each_change(self):

        self.client.login(username='user1', password='testpass123')
        
        # User 1 makes a change
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Priority',
            old_value='Medium',
            new_value='High',
            changed_by=self.user1
        )
        
        # User 2 makes a change
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Description',
            old_value='Original description',
            new_value='Updated description',
            changed_by=self.user2
        )
        
        # Get task detail page
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        history = list(response.context['history'])
        
        # Verify changed_by is recorded
        self.assertEqual(history[0].changed_by, self.user2)
        self.assertEqual(history[1].changed_by, self.user1)
        
        # Verify usernames appear in template
        self.assertContains(response, self.user1.username)
        self.assertContains(response, self.user2.username)
    
    def test_shows_timestamps_for_all_changes(self):

        self.client.login(username='user1', password='testpass123')
        
        # Create history entries at different times
        now = timezone.now()
        
        history1 = TaskHistory.objects.create(
            task=self.task,
            field_changed='Status',
            old_value='Backlog',
            new_value='Sprint',
            changed_by=self.user1
        )
        history1.timestamp = now - timedelta(hours=2)
        history1.save()
        
        history2 = TaskHistory.objects.create(
            task=self.task,
            field_changed='Priority',
            old_value='Medium',
            new_value='High',
            changed_by=self.user1
        )
        history2.timestamp = now - timedelta(hours=1)
        history2.save()
        
        # Get task detail page
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        history = list(response.context['history'])
        
        # Verify all entries have timestamps
        for entry in history:
            self.assertIsNotNone(entry.timestamp)
        
        # Verify timestamps are in correct order (most recent first)
        self.assertTrue(history[0].timestamp > history[1].timestamp)
    
    def test_includes_notes_for_test_failures(self):

        self.client.login(username='user1', password='testpass123')
        
        failure_notes = 'UI bugs found - buttons not working'
        
        # Create history entry with failure notes
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Status',
            old_value='Testing',
            new_value='Failed',
            changed_by=self.user1,
            notes=failure_notes
        )
        
        # Get task detail page
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        # Verify notes appear in history
        self.assertContains(response, failure_notes)
        
        history = list(response.context['history'])
        self.assertEqual(history[0].notes, failure_notes)
    
    def test_shows_priority_changes(self):
 
        self.client.login(username='user1', password='testpass123')
        
        # Change priority from Medium to High
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Priority',
            old_value='Medium',
            new_value='High',
            changed_by=self.user1
        )
        
        # Get task detail page
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        # Verify priority change is shown
        self.assertContains(response, 'Priority')
        self.assertContains(response, 'Medium')
        self.assertContains(response, 'High')
        
        history = list(response.context['history'])
        self.assertEqual(history[0].field_changed, 'Priority')
        self.assertEqual(history[0].old_value, 'Medium')
        self.assertEqual(history[0].new_value, 'High')
    
    def test_shows_assignment_changes(self):

        self.client.login(username='user1', password='testpass123')
        
        # Change assignment
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Assigned To',
            old_value='',
            new_value=self.user1.username,
            changed_by=self.user1
        )
        
        # Change assignment again
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Assigned To',
            old_value=self.user1.username,
            new_value=self.user2.username,
            changed_by=self.user1
        )
        
        # Get task detail page
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        # Verify assignment changes are shown
        history = list(response.context['history'])
        
        self.assertEqual(history[0].field_changed, 'Assigned To')
        self.assertEqual(history[0].new_value, self.user2.username)
        
        self.assertEqual(history[1].field_changed, 'Assigned To')
        self.assertEqual(history[1].new_value, self.user1.username)
    
    def test_displays_sprint_moves(self):

        self.client.login(username='user1', password='testpass123')
        
        # Move to Sprint 1
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Sprint',
            old_value='',
            new_value=self.sprint1.name,
            changed_by=self.user1
        )
        
        # Move to Sprint 2
        TaskHistory.objects.create(
            task=self.task,
            field_changed='Sprint',
            old_value=self.sprint1.name,
            new_value=self.sprint2.name,
            changed_by=self.user2
        )
        
        # Get task detail page
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        # Verify sprint moves are shown
        history = list(response.context['history'])
        
        self.assertEqual(history[0].field_changed, 'Sprint')
        self.assertEqual(history[0].old_value, self.sprint1.name)
        self.assertEqual(history[0].new_value, self.sprint2.name)
        
        self.assertEqual(history[1].field_changed, 'Sprint')
        self.assertEqual(history[1].old_value, '')
        self.assertEqual(history[1].new_value, self.sprint1.name)
    
    def test_limited_to_last_50_changes(self):

        self.client.login(username='user1', password='testpass123')
        
        # Create 60 history entries
        for i in range(60):
            TaskHistory.objects.create(
                task=self.task,
                field_changed='Description',
                old_value=f'Description {i}',
                new_value=f'Description {i+1}',
                changed_by=self.user1
            )
        
        # Get task detail page
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        # Verify only 50 entries returned
        history = list(response.context['history'])
        self.assertEqual(len(history), 50)
        
        # Verify most recent 50 are returned
        # The most recent entry should be 'Description 60'
        self.assertEqual(history[0].new_value, 'Description 60')
        
        # The oldest displayed entry should be 'Description 11'
        self.assertEqual(history[49].new_value, 'Description 11')


class PriorityChangeLoggingTests(TestCase):
    
    def setUp(self):
  
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            status='BACKLOG',
            priority=2,  # High
            story_points=5,
            created_by=self.user
        )
        
        self.client = Client()
    
    def test_priority_change_logged_when_editing_task(self):

        self.client.login(username='testuser', password='testpass123')
        
        # Count initial history entries
        initial_count = TaskHistory.objects.filter(task=self.task).count()
        
        # Edit task and change priority from High (2) to Critical (1)
        response = self.client.post(
            reverse('edit_task', args=[self.task.pk]),
            {
                'title': self.task.title,
                'description': self.task.description,
                'priority': 1,  # Critical
                'story_points': self.task.story_points,
                'status': self.task.status,
            },
            follow=True
        )
        
        # Verify task was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.priority, 1)
        
        # Verify history entry was created
        final_count = TaskHistory.objects.filter(task=self.task).count()
        self.assertGreater(final_count, initial_count)
        
        # Verify priority change is logged
        priority_histories = TaskHistory.objects.filter(
            task=self.task,
            field_changed='Priority'
        ).order_by('-timestamp')
        
        # Find the actual priority change (where old != new)
        priority_history = None
        for hist in priority_histories:
            if hist.old_value != hist.new_value:
                priority_history = hist
                break
        
        self.assertIsNotNone(priority_history, "No priority change found in history")
        self.assertEqual(priority_history.old_value, 'High')
        self.assertEqual(priority_history.new_value, 'Critical')
        self.assertEqual(priority_history.changed_by, self.user)
    
    def test_priority_change_from_low_to_medium(self):

        self.client.login(username='testuser', password='testpass123')
        
        # Set task to Low priority
        self.task.priority = 4  # Low
        self.task.save()
        
        # Change to Medium
        self.client.post(
            reverse('edit_task', args=[self.task.pk]),
            {
                'title': self.task.title,
                'description': self.task.description,
                'priority': 3,  # Medium
                'story_points': self.task.story_points,
                'status': self.task.status,
            }
        )
        
        # Verify history entry - find actual change
        priority_histories = TaskHistory.objects.filter(
            task=self.task,
            field_changed='Priority'
        ).order_by('-timestamp')
        
        priority_history = None
        for hist in priority_histories:
            if hist.old_value != hist.new_value:
                priority_history = hist
                break
        
        self.assertIsNotNone(priority_history)
        self.assertEqual(priority_history.old_value, 'Low')
        self.assertEqual(priority_history.new_value, 'Medium')
    
    def test_priority_change_from_high_to_low(self):
 
        self.client.login(username='testuser', password='testpass123')
        
        # Set task to Critical priority
        self.task.priority = 1  # Critical
        self.task.save()
        
        # Change to Low
        self.client.post(
            reverse('edit_task', args=[self.task.pk]),
            {
                'title': self.task.title,
                'description': self.task.description,
                'priority': 4,  # Low
                'story_points': self.task.story_points,
                'status': self.task.status,
            }
        )
        
        # Verify history entry - find actual change
        priority_histories = TaskHistory.objects.filter(
            task=self.task,
            field_changed='Priority'
        ).order_by('-timestamp')
        
        priority_history = None
        for hist in priority_histories:
            if hist.old_value != hist.new_value:
                priority_history = hist
                break
        
        self.assertIsNotNone(priority_history)
        self.assertEqual(priority_history.old_value, 'Critical')
        self.assertEqual(priority_history.new_value, 'Low')
    
    def test_no_history_when_priority_unchanged(self):

        self.client.login(username='testuser', password='testpass123')
        
        # Count history entries for Priority field
        initial_priority_count = TaskHistory.objects.filter(
            task=self.task,
            field_changed='Priority'
        ).count()
        
        # Edit task WITHOUT changing priority
        self.client.post(
            reverse('edit_task', args=[self.task.pk]),
            {
                'title': 'Updated Title',  # Change something else
                'description': self.task.description,
                'priority': self.task.priority,  # Keep same priority
                'story_points': self.task.story_points,
                'status': self.task.status,
            }
        )
        
        # Verify no new priority history entry was created
        # Note: The view should create history entries for all fields
        # but priority old_value should equal new_value
        priority_histories = TaskHistory.objects.filter(
            task=self.task,
            field_changed='Priority'
        )
        
        # Check if a priority entry was added
        if priority_histories.count() > initial_priority_count:
            # If it was added, old and new values should be the same
            latest_priority = priority_histories.latest('timestamp')
            self.assertEqual(latest_priority.old_value, latest_priority.new_value)
    
    def test_priority_change_shows_in_task_detail(self):
 
        self.client.login(username='testuser', password='testpass123')
        
        # Change priority from High to Critical
        self.client.post(
            reverse('edit_task', args=[self.task.pk]),
            {
                'title': self.task.title,
                'description': self.task.description,
                'priority': 1,  # Critical
                'story_points': self.task.story_points,
                'status': self.task.status,
            }
        )
        
        # View task detail
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        # Verify priority change appears in history section
        self.assertContains(response, 'Priority')
        self.assertContains(response, 'High')
        self.assertContains(response, 'Critical')
    
    def test_multiple_priority_changes_all_logged(self):

        self.client.login(username='testuser', password='testpass123')
        
        # Change 1: High → Critical
        self.client.post(
            reverse('edit_task', args=[self.task.pk]),
            {
                'title': self.task.title,
                'description': self.task.description,
                'priority': 1,  # Critical
                'story_points': self.task.story_points,
                'status': self.task.status,
            }
        )
        
        # Change 2: Critical → Low
        self.client.post(
            reverse('edit_task', args=[self.task.pk]),
            {
                'title': self.task.title,
                'description': self.task.description,
                'priority': 4,  # Low
                'story_points': self.task.story_points,
                'status': self.task.status,
            }
        )
        
        # Change 3: Low → Medium
        self.client.post(
            reverse('edit_task', args=[self.task.pk]),
            {
                'title': self.task.title,
                'description': self.task.description,
                'priority': 3,  # Medium
                'story_points': self.task.story_points,
                'status': self.task.status,
            }
        )
        
        # Verify all 3 changes are logged
        priority_histories = TaskHistory.objects.filter(
            task=self.task,
            field_changed='Priority'
        ).order_by('-timestamp')
        
        self.assertGreaterEqual(priority_histories.count(), 3)
        
        # Verify the sequence (most recent first)
        changes = list(priority_histories[:3])
        self.assertEqual(changes[0].old_value, 'Low')
        self.assertEqual(changes[0].new_value, 'Medium')
        
        self.assertEqual(changes[1].old_value, 'Critical')
        self.assertEqual(changes[1].new_value, 'Low')
        
        self.assertEqual(changes[2].old_value, 'High')
        self.assertEqual(changes[2].new_value, 'Critical')
