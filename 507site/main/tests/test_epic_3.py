from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone
from main.models import Task, Sprint, Comment

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
        
        # Refresh task from database
        self.task.refresh_from_db()
        
        # Verify status changed to TESTING
        self.assertEqual(self.task.status, 'TESTING')
        
        # Verify sprint_progress was cleared
        self.assertIsNone(self.task.sprint_progress)
        
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
        
        # Refresh task
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
        
        # Refresh task
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
        
        # Refresh task
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
        
        # Refresh task
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
        
        # Refresh task
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
        
        # Refresh task
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
        
        # Refresh task
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
        
        # Refresh task
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