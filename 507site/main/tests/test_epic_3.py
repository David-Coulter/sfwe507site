from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone
from main.models import Task, Sprint, Comment
from datetime import timedelta

# User-Test-Case 12: Mark Task Ready for Test
class MarkTaskReadyForTestTests(TestCase):

    def setUp(self):
        # Create users
        self.developer = User.objects.create_user(
            username='developer',
            password='testpass123'
        )
        
        # Create sprint
        self.sprint = Sprint.objects.create(
            name='Sprint 1',
            status='ACTIVE'
        )
        
        # Create task in sprint with DONE status
        self.task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            status='SPRINT',
            sprint_progress='DONE',
            priority='2',
            story_points=5,
            assigned_to=self.developer,
            sprint=self.sprint
        )
        
        self.client = Client()
    
    def test_button_available_for_sprint_task_when_done(self):

        self.client.login(username='developer', password='testpass123')
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        # Check that task detail page loads
        self.assertEqual(response.status_code, 200)
        
        # Check that task is in SPRINT status and DONE
        self.assertEqual(self.task.status, 'SPRINT')
        self.assertEqual(self.task.sprint_progress, 'DONE')
        
        # Check that mark_ready_for_test URL is in the page
        self.assertContains(response, reverse('mark_ready_for_test', args=[self.task.pk]))
    
    def test_status_changes_to_testing(self):

        self.client.login(username='developer', password='testpass123')
        
        # Mark task ready for test
        response = self.client.post(
            reverse('mark_ready_for_test', args=[self.task.pk]),
            follow=True
        )
        
        self.task.refresh_from_db()
        
        # Verify status changed to TESTING
        self.assertEqual(self.task.status, 'TESTING')
        
        # Verify sprint_progress was cleared
        self.assertEqual(self.task.sprint_progress, 'DONE')
        
        # Check for success message
        messages = list(response.context['messages'])
        self.assertTrue(any('Ready for Test' in str(m) for m in messages))
    
    def test_task_appears_in_testing_queue(self):

        # Create Testing Manager
        testing_group = Group.objects.create(name='Testing Manager')
        test_manager = User.objects.create_user(
            username='test_manager',
            password='testpass123'
        )
        test_manager.groups.add(testing_group)
        
        # Mark task ready for test
        self.task.status = 'TESTING'
        self.task.sprint_progress = None
        self.task.save()
        
        # Login as Testing Manager
        self.client.login(username='test_manager', password='testpass123')
        
        # Access Testing Queue
        response = self.client.get(reverse('testing_queue'))
        
        # Verify task appears in Testing Queue
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.task.title)
        self.assertIn(self.task, response.context['testing_tasks'])
    
    def test_action_logged_in_task_history(self):

        self.client.login(username='developer', password='testpass123')
        
        # Count comments before
        initial_comment_count = Comment.objects.filter(task=self.task).count()
        
        # Mark task ready for test
        response = self.client.post(
            reverse('mark_ready_for_test', args=[self.task.pk])
        )
        
        # Verify a comment was created
        final_comment_count = Comment.objects.filter(task=self.task).count()
        self.assertEqual(final_comment_count, initial_comment_count + 1)
        
        # Verify comment content mentions "Ready for Test"
        latest_comment = Comment.objects.filter(task=self.task).latest('created_at')
        self.assertIn('Ready for Test', latest_comment.text)
    
    def test_original_developer_still_assigned(self):
        self.client.login(username='developer', password='testpass123')
        
        original_assignee = self.task.assigned_to
        
        # Mark task ready for test
        response = self.client.post(
            reverse('mark_ready_for_test', args=[self.task.pk])
        )
        
        self.task.refresh_from_db()
        
        # Verify assigned_to didn't change
        self.assertEqual(self.task.assigned_to, original_assignee)
        self.assertEqual(self.task.assigned_to, self.developer)
    
    def test_cannot_mark_ready_if_not_sprint_status(self):

        self.client.login(username='developer', password='testpass123')
        
        # Set task to BACKLOG status
        self.task.status = 'BACKLOG'
        self.task.save()
        
        # Try to mark ready for test
        response = self.client.post(
            reverse('mark_ready_for_test', args=[self.task.pk]),
            follow=True
        )
        
        self.task.refresh_from_db()
        
        # Verify status didn't change
        self.assertEqual(self.task.status, 'BACKLOG')
        
        # Check for error message
        messages = list(response.context['messages'])
        self.assertTrue(any('must be in Sprint' in str(m) for m in messages))
    
    def test_sprint_assignment_preserved(self):

        self.client.login(username='developer', password='testpass123')
        
        original_sprint = self.task.sprint
        
        # Mark task ready for test
        response = self.client.post(
            reverse('mark_ready_for_test', args=[self.task.pk])
        )
        
        self.task.refresh_from_db()
        
        # Verify sprint assignment preserved
        self.assertEqual(self.task.sprint, original_sprint)


# User-Test-Case 13: Pass Task Testing
class PassTaskTestingTests(TestCase):
    
    def setUp(self):
        """Set up test data"""
        # Create Testing Manager group
        self.testing_group = Group.objects.create(name='Testing Manager')
        
        # Create users
        self.test_manager = User.objects.create_user(
            username='test_manager',
            password='testpass123'
        )
        self.test_manager.groups.add(self.testing_group)
        
        self.developer = User.objects.create_user(
            username='developer',
            password='testpass123'
        )
        
        # Create sprint
        self.sprint = Sprint.objects.create(
            name='Sprint 1',
            status='ACTIVE'
        )
        
        # Create task in TESTING status
        self.task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            status='TESTING',
            priority='3',
            story_points=8,
            assigned_to=self.developer,
            sprint=self.sprint
        )
        
        self.client = Client()
    
    def test_action_available_for_testing_status(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Access Testing Queue
        response = self.client.get(reverse('testing_queue'))
        
        # Verify Pass button/action is available
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('pass_testing', args=[self.task.pk]))
        self.assertContains(response, 'Pass')
    
    def test_status_changes_to_complete(self):
        """
        US-13 AC2: Status changes to 'COMPLETE'
        """
        self.client.login(username='test_manager', password='testpass123')
        
        # Pass the task
        response = self.client.post(
            reverse('pass_testing', args=[self.task.pk]),
            follow=True
        )
        
        
        self.task.refresh_from_db()
        
        # Verify status changed to COMPLETE
        self.assertEqual(self.task.status, 'COMPLETE')
        
        # Check for success message
        messages = list(response.context['messages'])
        self.assertTrue(any('passed testing' in str(m) for m in messages))
    
    def test_task_removed_from_testing_queue(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Verify task is in Testing Queue before passing
        response = self.client.get(reverse('testing_queue'))
        self.assertIn(self.task, response.context['testing_tasks'])
        
        # Pass the task
        self.client.post(reverse('pass_testing', args=[self.task.pk]))
        
        # Access Testing Queue again
        response = self.client.get(reverse('testing_queue'))
        
        # Verify task is no longer in Testing Queue
        self.assertNotIn(self.task, response.context['testing_tasks'])
    
    def test_task_appears_in_completed_view(self):
  
        self.client.login(username='test_manager', password='testpass123')
        
        # Pass the task
        self.client.post(reverse('pass_testing', args=[self.task.pk]))
        
        self.task.refresh_from_db()
        
        # Query for completed tasks
        completed_tasks = Task.objects.filter(status='COMPLETE')
        
        # Verify task appears in completed tasks
        self.assertIn(self.task, completed_tasks)
    
    def test_completion_timestamp_recorded(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Verify completed_at is None before passing
        self.assertIsNone(self.task.completed_at)
        
        # Pass the task
        before_pass = timezone.now()
        self.client.post(reverse('pass_testing', args=[self.task.pk]))
        after_pass = timezone.now()
        
        
        self.task.refresh_from_db()
        
        # Verify completed_at is set
        self.assertIsNotNone(self.task.completed_at)
        
        # Verify timestamp is between before and after
        self.assertGreaterEqual(self.task.completed_at, before_pass)
        self.assertLessEqual(self.task.completed_at, after_pass)
    
    def test_action_logged_in_history(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Count comments before
        initial_comment_count = Comment.objects.filter(task=self.task).count()
        
        # Pass the task
        response = self.client.post(reverse('pass_testing', args=[self.task.pk]))
        
        # Verify a comment was created
        final_comment_count = Comment.objects.filter(task=self.task).count()
        self.assertEqual(final_comment_count, initial_comment_count + 1)
        
        # Verify comment mentions "passed" and "testing"
        latest_comment = Comment.objects.filter(task=self.task).latest('created_at')
        self.assertIn('passed', latest_comment.text.lower())
        self.assertIn('testing', latest_comment.text.lower())
    
    def test_only_testing_manager_can_pass(self):

        # Login as regular developer (not Testing Manager)
        self.client.login(username='developer', password='testpass123')
        
        # Try to pass the task
        response = self.client.post(
            reverse('pass_testing', args=[self.task.pk]),
            follow=True
        )
        
        
        self.task.refresh_from_db()
        
        # Verify status didn't change
        self.assertEqual(self.task.status, 'TESTING')
        
        # Check for error message
        messages = list(response.context['messages'])
        self.assertTrue(any('Testing Manager' in str(m) for m in messages))
    
    def test_cannot_pass_if_not_testing_status(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Set task to SPRINT status
        self.task.status = 'SPRINT'
        self.task.save()
        
        # Try to pass the task
        response = self.client.post(
            reverse('pass_testing', args=[self.task.pk]),
            follow=True
        )
        
        
        self.task.refresh_from_db()
        
        # Verify status didn't change to COMPLETE
        self.assertEqual(self.task.status, 'SPRINT')
        
        # Check for error message
        messages = list(response.context['messages'])
        self.assertTrue(any('must be in Testing' in str(m) for m in messages))

# Testing Workflow Integration Tests - User Story 12 and 13
class TestingWorkflowIntegrationTests(TestCase):
    
    def setUp(self):
        """Set up test data"""
        # Create Testing Manager group
        self.testing_group = Group.objects.create(name='Testing Manager')
        
        # Create users
        self.developer = User.objects.create_user(
            username='developer',
            password='testpass123'
        )
        
        self.test_manager = User.objects.create_user(
            username='test_manager',
            password='testpass123'
        )
        self.test_manager.groups.add(self.testing_group)
        
        # Create sprint
        self.sprint = Sprint.objects.create(
            name='Sprint 1',
            status='ACTIVE'
        )
        
        # Create task in sprint
        self.task = Task.objects.create(
            title='Integration Test Task',
            description='Test Description',
            status='SPRINT',
            sprint_progress='DONE',
            priority='3',
            story_points=5,
            assigned_to=self.developer,
            sprint=self.sprint
        )
        
        self.client = Client()
    
    def test_complete_workflow_developer_to_testing_manager(self):

        # Step 1: Developer marks task ready for test
        self.client.login(username='developer', password='testpass123')
        response = self.client.post(
            reverse('mark_ready_for_test', args=[self.task.pk])
        )
        self.task.refresh_from_db()
        
        # Verify task is in TESTING
        self.assertEqual(self.task.status, 'TESTING')
        
        # Step 2: Testing Manager accesses Testing Queue
        self.client.logout()
        self.client.login(username='test_manager', password='testpass123')
        response = self.client.get(reverse('testing_queue'))
        
        # Verify task appears
        self.assertIn(self.task, response.context['testing_tasks'])
        
        # Step 3: Testing Manager passes the task
        response = self.client.post(
            reverse('pass_testing', args=[self.task.pk])
        )
        self.task.refresh_from_db()
        
        # Verify task is COMPLETE
        self.assertEqual(self.task.status, 'COMPLETE')
        self.assertIsNotNone(self.task.completed_at)
        
        # Verify 2 comments created (ready for test + passed)
        comments = Comment.objects.filter(task=self.task)
        self.assertEqual(comments.count(), 2)
    
    def test_task_not_on_sprint_board_when_in_testing(self):

        # Mark task ready for test
        self.task.status = 'TESTING'
        self.task.sprint_progress = None
        self.task.save()
        
        self.client.login(username='developer', password='testpass123')
        
        # Access sprint board
        response = self.client.get(reverse('sprint_board', args=[self.sprint.pk]))
        
        # Get all tasks from all columns
        not_started = response.context.get('not_started_tasks', [])
        in_progress = response.context.get('in_progress_tasks', [])
        in_review = response.context.get('in_review_tasks', [])
        done = response.context.get('done_tasks', [])
        
        all_sprint_board_tasks = list(not_started) + list(in_progress) + list(in_review) + list(done)
        
        # Verify task is NOT on sprint board
        self.assertNotIn(self.task, all_sprint_board_tasks)
    
    def test_developer_cannot_edit_task_in_testing(self):

        # Set task to TESTING
        self.task.status = 'TESTING'
        self.task.save()
        
        self.client.login(username='developer', password='testpass123')
        
        # Try to access edit page
        response = self.client.get(
            reverse('edit_task', args=[self.task.pk]),
            follow=True
        )
        
        # Should redirect with error
        messages = list(response.context['messages'])
        self.assertTrue(any('cannot edit' in str(m).lower() for m in messages))
    
    def test_developer_cannot_edit_task_when_complete(self):
 
        # Set task to COMPLETE
        self.task.status = 'COMPLETE'
        self.task.save()
        
        self.client.login(username='developer', password='testpass123')
        
        # Try to access edit page
        response = self.client.get(
            reverse('edit_task', args=[self.task.pk]),
            follow=True
        )
        
        # Should redirect with error
        messages = list(response.context['messages'])
        self.assertTrue(any('cannot edit' in str(m).lower() for m in messages))


class FailTaskTestingTests(TestCase):
    
    def setUp(self):

        # Create Testing Manager group
        self.testing_group = Group.objects.create(name='Testing Manager')
        
        # Create users
        self.test_manager = User.objects.create_user(
            username='test_manager',
            password='testpass123'
        )
        self.test_manager.groups.add(self.testing_group)
        
        self.developer = User.objects.create_user(
            username='developer',
            password='testpass123'
        )
        
        # Create sprint
        self.sprint = Sprint.objects.create(
            name='Sprint 1',
            status='ACTIVE'
        )
        
        # Create task in TESTING status
        self.task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            status='TESTING',
            priority=2,
            story_points=5,
            assigned_to=self.developer,
            sprint=self.sprint,
            failed_count=0,
            testing_notes='',
            moved_to_testing_at=timezone.now()
        )
        
        self.client = Client()
    
    def test_action_available_for_testing_status(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Access Testing Queue
        response = self.client.get(reverse('testing_queue'))
        
        # Verify Fail button/action is available
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('fail_testing', args=[self.task.pk]))
        self.assertContains(response, 'Fail')
    
    def test_failure_reason_required(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Try to fail without providing a reason
        response = self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': ''},  # Empty reason
            follow=True
        )
        
        
        self.task.refresh_from_db()
        
        # Verify status didn't change (still TESTING)
        self.assertEqual(self.task.status, 'TESTING')
        
        # Check for error message
        messages = list(response.context['messages'])
        self.assertTrue(any('provide a reason' in str(m).lower() for m in messages))
    
    def test_status_changes_back_to_sprint(self):
 
        self.client.login(username='test_manager', password='testpass123')
        
        # Fail the task with a reason
        response = self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': 'UI bugs found'},
            follow=True
        )
        
        
        self.task.refresh_from_db()
        
        # Verify status changed back to SPRINT
        self.assertEqual(self.task.status, 'SPRINT')
        
        # Verify sprint_progress set to IN_PROGRESS for rework
        self.assertEqual(self.task.sprint_progress, 'IN_PROGRESS')
    
    def test_failed_count_incremented(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Initial failed count
        initial_count = self.task.failed_count
        self.assertEqual(initial_count, 0)
        
        # Fail the task
        self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': 'First failure'},
        )
        
        # Refresh and check count
        self.task.refresh_from_db()
        self.assertEqual(self.task.failed_count, 1)
        
        # Mark ready for test again, then fail again
        self.task.status = 'TESTING'
        self.task.save()
        
        self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': 'Second failure'},
        )
        
        # Refresh and check count
        self.task.refresh_from_db()
        self.assertEqual(self.task.failed_count, 2)
    
    def test_testing_notes_appended(self):

        self.client.login(username='test_manager', password='testpass123')
        
        failure_reason = 'UI is broken and needs fixes'
        
        # Verify notes are empty initially
        self.assertEqual(self.task.testing_notes, '')
        
        # Fail the task
        self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': failure_reason},
        )
        
        
        self.task.refresh_from_db()
        
        # Verify testing notes contain failure reason
        self.assertIn(failure_reason, self.task.testing_notes)
        self.assertIn('Failed Testing #1', self.task.testing_notes)
    
    def test_task_returns_to_sprint_backlog(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Fail the task
        self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': 'Bugs found'},
        )
        
        
        self.task.refresh_from_db()
        
        # Verify task is back in sprint
        self.assertEqual(self.task.status, 'SPRINT')
        self.assertEqual(self.task.sprint, self.sprint)
        
        # Verify task appears on sprint board
        sprint_tasks = Task.objects.filter(sprint=self.sprint, status='SPRINT')
        self.assertIn(self.task, sprint_tasks)
    
    def test_action_logged_in_history(self):
 
        self.client.login(username='test_manager', password='testpass123')
        
        # Count comments before
        initial_comment_count = Comment.objects.filter(task=self.task).count()
        
        # Fail the task
        failure_reason = 'Critical bugs'
        self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': failure_reason},
        )
        
        # Verify a comment was created
        final_comment_count = Comment.objects.filter(task=self.task).count()
        self.assertEqual(final_comment_count, initial_comment_count + 1)
        
        # Verify comment mentions failed and reason
        latest_comment = Comment.objects.filter(task=self.task).latest('created_at')
        self.assertIn('failed', latest_comment.text.lower())
        self.assertIn(failure_reason, latest_comment.text)
    
    def test_only_testing_manager_can_fail(self):

        # Login as regular developer
        self.client.login(username='developer', password='testpass123')
        
        # Try to fail the task
        response = self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': 'Should not work'},
            follow=True
        )
        
        
        self.task.refresh_from_db()
        
        # Verify status didn't change
        self.assertEqual(self.task.status, 'TESTING')
        
        # Check for error message
        messages = list(response.context['messages'])
        self.assertTrue(any('Testing Manager' in str(m) for m in messages))
    
    def test_cannot_fail_if_not_testing_status(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Set task to SPRINT status
        self.task.status = 'SPRINT'
        self.task.save()
        
        # Try to fail the task
        response = self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': 'Should not work'},
            follow=True
        )
        
        
        self.task.refresh_from_db()
        
        # Verify failed_count didn't increment
        self.assertEqual(self.task.failed_count, 0)
        
        # Check for error message
        messages = list(response.context['messages'])
        self.assertTrue(any('must be in Testing' in str(m) for m in messages))
    
    def test_moved_to_testing_at_cleared_on_failure(self):

        self.client.login(username='test_manager', password='testpass123')
        
        # Verify moved_to_testing_at is set
        self.assertIsNotNone(self.task.moved_to_testing_at)
        
        # Fail the task
        self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': 'Bugs'},
        )
        
        
        self.task.refresh_from_db()
        
        # Verify moved_to_testing_at was cleared
        self.assertIsNone(self.task.moved_to_testing_at)


class ViewTestingQueueTests(TestCase):
    
    def setUp(self):
        # Create Testing Manager group
        self.testing_group = Group.objects.create(name='Testing Manager')
        
        # Create users
        self.test_manager = User.objects.create_user(
            username='test_manager',
            password='testpass123'
        )
        self.test_manager.groups.add(self.testing_group)
        
        self.developer1 = User.objects.create_user(
            username='developer1',
            password='testpass123'
        )
        
        self.developer2 = User.objects.create_user(
            username='developer2',
            password='testpass123'
        )
        
        # Create sprint
        self.sprint = Sprint.objects.create(
            name='Sprint 1',
            status='ACTIVE'
        )
        
        # Create multiple tasks in TESTING with different priorities and times
        now = timezone.now()
        
        # High priority, oldest
        self.task_high_old = Task.objects.create(
            title='High Priority Old',
            status='TESTING',
            priority=3,  # High
            story_points=8,
            assigned_to=self.developer1,
            sprint=self.sprint,
            failed_count=0,
            moved_to_testing_at=now - timedelta(days=3)
        )
        
        # High priority, newer
        self.task_high_new = Task.objects.create(
            title='High Priority New',
            status='TESTING',
            priority=3,  # High
            story_points=5,
            assigned_to=self.developer2,
            sprint=self.sprint,
            failed_count=0,
            moved_to_testing_at=now - timedelta(hours=2)
        )
        
        # Medium priority
        self.task_medium = Task.objects.create(
            title='Medium Priority',
            status='TESTING',
            priority=2,  # Medium
            story_points=3,
            assigned_to=self.developer1,
            sprint=self.sprint,
            failed_count=1,  # Failed once
            moved_to_testing_at=now - timedelta(days=1)
        )
        
        # Low priority
        self.task_low = Task.objects.create(
            title='Low Priority',
            status='TESTING',
            priority=1,  # Low
            story_points=2,
            assigned_to=self.developer2,
            sprint=self.sprint,
            failed_count=3,  # Failed multiple times
            moved_to_testing_at=now - timedelta(hours=6)
        )
        
        # Task not in testing (should not appear)
        self.task_sprint = Task.objects.create(
            title='Not in Testing',
            status='SPRINT',
            priority=3,
            story_points=5,
            assigned_to=self.developer1,
            sprint=self.sprint
        )
        
        self.client = Client()
    
    def test_shows_only_testing_tasks(self):

        self.client.login(username='test_manager', password='testpass123')
        
        response = self.client.get(reverse('testing_queue'))
        
        testing_tasks = response.context['testing_tasks']
        
        # Verify only TESTING tasks appear
        self.assertEqual(len(testing_tasks), 4)
        self.assertIn(self.task_high_old, testing_tasks)
        self.assertIn(self.task_high_new, testing_tasks)
        self.assertIn(self.task_medium, testing_tasks)
        self.assertIn(self.task_low, testing_tasks)
        
        # Verify SPRINT task does NOT appear
        self.assertNotIn(self.task_sprint, testing_tasks)
    
    def test_sorted_by_priority_then_date(self):

        self.client.login(username='test_manager', password='testpass123')
        
        response = self.client.get(reverse('testing_queue'))
        
        testing_tasks = list(response.context['testing_tasks'])
        
        # Expected order:
        # 1. High priority, older first (task_high_old)
        # 2. High priority, newer (task_high_new)
        # 3. Medium priority (task_medium)
        # 4. Low priority (task_low)
        
        self.assertEqual(testing_tasks[0], self.task_high_old)
        self.assertEqual(testing_tasks[1], self.task_high_new)
        self.assertEqual(testing_tasks[2], self.task_medium)
        self.assertEqual(testing_tasks[3], self.task_low)
    
    def test_shows_developer_who_completed_work(self):
  
        self.client.login(username='test_manager', password='testpass123')
        
        response = self.client.get(reverse('testing_queue'))
        
        # Verify developers are shown
        self.assertContains(response, self.developer1.username)
        self.assertContains(response, self.developer2.username)
    
    def test_shows_time_in_testing_queue(self):
   
        self.client.login(username='test_manager', password='testpass123')
        
        response = self.client.get(reverse('testing_queue'))
        
        testing_tasks = response.context['testing_tasks']
        
        # Verify time calculations
        for task in testing_tasks:
            self.assertTrue(hasattr(task, 'hours_in_testing'))
            self.assertTrue(hasattr(task, 'days_in_testing'))
            
            if task == self.task_high_old:
                # 3 days old
                self.assertEqual(task.days_in_testing, 3)
            elif task == self.task_medium:
                # 1 day old
                self.assertEqual(task.days_in_testing, 1)
    
    def test_quick_actions_pass_and_fail_buttons(self):

        self.client.login(username='test_manager', password='testpass123')
        
        response = self.client.get(reverse('testing_queue'))
        
        # Verify Pass buttons exist
        self.assertContains(response, 'Pass')
        self.assertContains(response, reverse('pass_testing', args=[self.task_high_old.pk]))
        
        # Verify Fail buttons exist
        self.assertContains(response, 'Fail')
        self.assertContains(response, reverse('fail_testing', args=[self.task_high_old.pk]))
    
    def test_highlights_tasks_failed_multiple_times(self):

        self.client.login(username='test_manager', password='testpass123')
        
        response = self.client.get(reverse('testing_queue'))
        
        # task_low has failed_count=3, should be highlighted
        # Check for warning class or badge
        self.assertContains(response, 'table-warning')  # Bootstrap warning row class
        
        # Verify failed count badge is shown
        self.assertContains(response, str(self.task_low.failed_count))
    
    def test_shows_story_points_for_capacity_planning(self):
 
        self.client.login(username='test_manager', password='testpass123')
        
        response = self.client.get(reverse('testing_queue'))
        
        # Verify story points are displayed
        total_story_points = response.context['total_story_points']
        expected_total = (self.task_high_old.story_points + 
                         self.task_high_new.story_points + 
                         self.task_medium.story_points + 
                         self.task_low.story_points)
        
        self.assertEqual(total_story_points, expected_total)
        
        # Verify individual story points shown
        for task in [self.task_high_old, self.task_medium, self.task_low]:
            self.assertContains(response, f'{task.story_points} pts')
    
    def test_only_testing_manager_can_access_queue(self):

        # Login as regular developer
        self.client.login(username='developer1', password='testpass123')
        
        response = self.client.get(reverse('testing_queue'), follow=True)
        
        # Should redirect
        self.assertRedirects(response, reverse('dashboard'))
        
        # Check for error message
        messages = list(response.context['messages'])
        self.assertTrue(any('Testing Manager' in str(m) for m in messages))
    
    def test_empty_queue_message(self):

        # Delete all testing tasks
        Task.objects.filter(status='TESTING').delete()
        
        self.client.login(username='test_manager', password='testpass123')
        
        response = self.client.get(reverse('testing_queue'))
        
        # Verify empty state message
        self.assertContains(response, 'Empty')
        self.assertEqual(response.context['total_tasks'], 0)


class TestingWorkflowIntegrationTests(TestCase):
    
    def setUp(self):

        # Create Testing Manager group
        self.testing_group = Group.objects.create(name='Testing Manager')
        
        # Create users
        self.developer = User.objects.create_user(
            username='developer',
            password='testpass123'
        )
        
        self.test_manager = User.objects.create_user(
            username='test_manager',
            password='testpass123'
        )
        self.test_manager.groups.add(self.testing_group)
        
        # Create sprint
        self.sprint = Sprint.objects.create(
            name='Sprint 1',
            status='ACTIVE'
        )
        
        # Create task
        self.task = Task.objects.create(
            title='Integration Test Task',
            description='Test Description',
            status='SPRINT',
            sprint_progress='DONE',
            priority=3,
            story_points=5,
            assigned_to=self.developer,
            sprint=self.sprint,
            failed_count=0
        )
        
        self.client = Client()
    
    def test_complete_fail_and_rework_cycle(self):

        # Step 1: Developer marks ready for test
        self.client.login(username='developer', password='testpass123')
        self.client.post(reverse('mark_ready_for_test', args=[self.task.pk]))
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'TESTING')
        self.assertIsNotNone(self.task.moved_to_testing_at)
        
        # Step 2: Testing Manager fails the task
        self.client.logout()
        self.client.login(username='test_manager', password='testpass123')
        
        self.client.post(
            reverse('fail_testing', args=[self.task.pk]),
            {'failure_reason': 'UI bugs found'}
        )
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'SPRINT')
        self.assertEqual(self.task.failed_count, 1)
        self.assertIn('UI bugs found', self.task.testing_notes)
        self.assertIsNone(self.task.moved_to_testing_at)
        
        # Step 3: Developer fixes and marks ready again
        self.client.logout()
        self.client.login(username='developer', password='testpass123')
        
        self.task.sprint_progress = 'DONE'
        self.task.save()
        
        self.client.post(reverse('mark_ready_for_test', args=[self.task.pk]))
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'TESTING')
        self.assertIsNotNone(self.task.moved_to_testing_at)
        
        # Step 4: Testing Manager passes the task
        self.client.logout()
        self.client.login(username='test_manager', password='testpass123')
        
        self.client.post(reverse('pass_testing', args=[self.task.pk]))
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'COMPLETE')
        self.assertEqual(self.task.failed_count, 1)  # Still shows it failed once
        
        # Verify comments were created for all actions
        comments = Comment.objects.filter(task=self.task)
        self.assertGreaterEqual(comments.count(), 4)  # ready, fail, ready, pass