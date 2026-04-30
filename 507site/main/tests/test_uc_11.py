from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from main.models import Task, Sprint


class CompleteSprintTests(TestCase):
    """Tests for UC-11: Complete Sprint"""
    
    def setUp(self):
        """Create test data for sprint completion tests"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create a sprint that ended 2 days ago (definitely completable)
        self.sprint = Sprint.objects.create(
            name='Test Sprint',
            start_date=timezone.now().date() - timedelta(days=14),
            end_date=timezone.now().date() - timedelta(days=2),
            status='ACTIVE',
            goal='Test sprint completion'
        )
        
        # Create tasks in different states
        self.done_task_1 = Task.objects.create(
            title='Done Task 1',
            status='SPRINT',
            sprint=self.sprint,
            planned_sprint=self.sprint,
            sprint_progress='DONE',
            story_points=3,
            priority=3,
            assigned_to=self.user
        )
        
        self.done_task_2 = Task.objects.create(
            title='Done Task 2',
            status='SPRINT',
            sprint=self.sprint,
            planned_sprint=self.sprint,
            sprint_progress='DONE',
            story_points=5,
            priority=3,
            assigned_to=self.user
        )
        
        self.in_progress_task = Task.objects.create(
            title='In Progress Task',
            status='SPRINT',
            sprint=self.sprint,
            planned_sprint=self.sprint,
            sprint_progress='IN_PROGRESS',
            story_points=2,
            priority=3,
            assigned_to=self.user
        )
        
        self.not_started_task = Task.objects.create(
            title='Not Started Task',
            status='SPRINT',
            sprint=self.sprint,
            planned_sprint=self.sprint,
            sprint_progress='NOT_STARTED',
            story_points=1,
            priority=3,
            assigned_to=self.user
        )
    
    def test_done_tasks_marked_complete(self):
        """AC: Tasks with status = DONE are marked COMPLETE"""
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        self.done_task_1.refresh_from_db()
        self.done_task_2.refresh_from_db()
        
        self.assertEqual(self.done_task_1.status, 'COMPLETE')
        self.assertEqual(self.done_task_2.status, 'COMPLETE')
        self.assertIsNotNone(self.done_task_1.completed_at)
        self.assertIsNotNone(self.done_task_2.completed_at)
    
    def test_unfinished_tasks_returned_to_backlog(self):
        """AC: Unfinished tasks are returned to Product Backlog"""
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        self.in_progress_task.refresh_from_db()
        self.not_started_task.refresh_from_db()
        
        self.assertEqual(self.in_progress_task.status, 'BACKLOG')
        self.assertEqual(self.not_started_task.status, 'BACKLOG')
        self.assertIsNone(self.in_progress_task.sprint)
        self.assertIsNone(self.not_started_task.sprint)
    
    def test_sprint_status_changes_to_complete(self):
        """AC: Sprint status changes to COMPLETE"""
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.status, 'COMPLETE')
    
    def test_sprint_end_date_recorded(self):
        """AC: Sprint end_date is recorded (if not already)"""
        sprint_no_end = Sprint.objects.create(
            name='Sprint No End',
            start_date=timezone.now().date() - timedelta(days=14),
            end_date=timezone.now().date() - timedelta(days=2),
            status='ACTIVE',
            goal='Test'
        )
        
        # Clear end_date
        Sprint.objects.filter(pk=sprint_no_end.pk).update(end_date=None)
        sprint_no_end.refresh_from_db()
        
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': sprint_no_end.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        sprint_no_end.refresh_from_db()
        self.assertIsNotNone(sprint_no_end.end_date)
    
    def test_planned_sprint_preserved_for_completed_tasks(self):
        """AC: planned_sprint field preserved for completed tasks"""
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        self.done_task_1.refresh_from_db()
        self.assertEqual(self.done_task_1.planned_sprint, self.sprint)
        self.assertEqual(self.done_task_1.status, 'COMPLETE')
    
    def test_planned_sprint_preserved_for_backlog_tasks(self):
        """AC: planned_sprint field preserved for unfinished tasks"""
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        self.in_progress_task.refresh_from_db()
        self.assertEqual(self.in_progress_task.planned_sprint, self.sprint)
        self.assertEqual(self.in_progress_task.status, 'BACKLOG')
        self.assertIsNone(self.in_progress_task.sprint)
    
    def test_unfinished_task_can_be_reassigned(self):
        """AC: Unfinished tasks can be reassigned to new sprint"""
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        self.in_progress_task.refresh_from_db()
        self.assertIsNone(self.in_progress_task.sprint)
        self.assertEqual(self.in_progress_task.planned_sprint, self.sprint)
        
        new_sprint = Sprint.objects.create(
            name='New Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE',
            goal='Next sprint'
        )
        
        self.in_progress_task.sprint = new_sprint
        self.in_progress_task.status = 'SPRINT'
        self.in_progress_task.save()
        
        self.assertEqual(self.in_progress_task.sprint, new_sprint)
        self.assertEqual(self.in_progress_task.planned_sprint, self.sprint)
    
    def test_only_active_sprints_can_be_completed(self):
        """AC: Only sprints with status = ACTIVE can be completed"""
        completed_sprint = Sprint.objects.create(
            name='Already Complete',
            start_date=timezone.now().date() - timedelta(days=28),
            end_date=timezone.now().date() - timedelta(days=15),
            status='COMPLETE',
            goal='Already done'
        )
        
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': completed_sprint.pk}),
            {'unfinished_action': 'backlog'}
        )
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        completed_sprint.refresh_from_db()
        self.assertEqual(completed_sprint.status, 'COMPLETE')
    
    def test_cannot_complete_before_end_date(self):
        """AC: Cannot complete sprint before end date"""
        future_sprint = Sprint.objects.create(
            name='Future Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE',
            goal='Still running'
        )
        
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': future_sprint.pk}),
            {'unfinished_action': 'backlog'}
        )
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        future_sprint.refresh_from_db()
        self.assertEqual(future_sprint.status, 'ACTIVE')
    
    def test_confirmation_message_displayed(self):
        """AC: Confirmation message displayed"""
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        # Check for success response
        self.assertEqual(response.status_code, 200)
        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.status, 'COMPLETE')
    
    def test_changes_persist_to_database(self):
        """AC: Changes persist to the database"""
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        sprint = Sprint.objects.get(pk=self.sprint.pk)
        done_tasks = Task.objects.filter(planned_sprint=sprint, status='COMPLETE')
        backlog_tasks = Task.objects.filter(planned_sprint=sprint, status='BACKLOG')
        
        self.assertEqual(sprint.status, 'COMPLETE')
        self.assertEqual(done_tasks.count(), 2)
        self.assertEqual(backlog_tasks.count(), 2)
    
    def test_burndown_accuracy_after_completion(self):
        """Bug Fix: Burndown shows all planned tasks"""
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        planned_tasks = Task.objects.filter(planned_sprint=self.sprint)
        self.assertEqual(planned_tasks.count(), 4)
        
        total_points = sum(t.story_points for t in planned_tasks)
        completed_points = sum(t.story_points for t in planned_tasks if t.status == 'COMPLETE')
        
        self.assertEqual(total_points, 11)
        self.assertEqual(completed_points, 8)
    
    def test_other_sprints_unaffected(self):
        """Bug Fix: Other sprints remain unchanged"""
        other_sprint = Sprint.objects.create(
            name='Other Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE',
            goal='Should be untouched'
        )
        
        other_task = Task.objects.create(
            title='Other Sprint Task',
            status='SPRINT',
            sprint=other_sprint,
            planned_sprint=other_sprint,
            sprint_progress='NOT_STARTED',
            story_points=5,
            priority=3,
            assigned_to=self.user
        )
        
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        other_sprint.refresh_from_db()
        other_task.refresh_from_db()
        
        self.assertEqual(other_sprint.status, 'ACTIVE')
        self.assertEqual(other_task.status, 'SPRINT')
        self.assertEqual(other_task.sprint, other_sprint)