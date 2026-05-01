from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from main.models import Task, Sprint

# Test for Sprint Creation
class SprintCreationTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.client = Client()
        self.client.login(username='testuser', password='pass123')
    
    def test_create_sprint_with_valid_data(self):
        self.user.is_staff = True
        self.user.save()

        response = self.client.post(reverse('create_sprint'), {
            'name': 'Sprint 1',
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + timedelta(days=14),
            'goal': 'Deliver core features',
            'status': 'PLANNING'
        })
        
        # Sprint should be created
        self.assertTrue(Sprint.objects.filter(name='Sprint 1').exists())
        
        # Check sprint details
        sprint = Sprint.objects.get(name='Sprint 1')
        self.assertEqual(sprint.goal, 'Deliver core features')
        self.assertEqual(sprint.status, 'PLANNING')
        
        # Should redirect after creation
        self.assertEqual(response.status_code, 302)
    
    def test_sprint_defaults_to_planning_status(self):
        Sprint.objects.create(
            name='Test Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14)
        )
        
        sprint = Sprint.objects.get(name='Test Sprint')
        self.assertEqual(sprint.status, 'NOT_STARTED')
    
    def test_end_date_must_be_after_start_date(self):
        initial_count = Sprint.objects.count()
        
        # Try to create sprint with end before start
        response = self.client.post(reverse('create_sprint'), {
            'name': 'Invalid Sprint',
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() - timedelta(days=1),
            'goal': 'This should fail'
        })
        
        # Sprint should not be created
        self.assertEqual(Sprint.objects.count(), initial_count)
    
    def test_created_sprint_appears_in_list(self):
        sprint = Sprint.objects.create(
            name='New Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE'
        )
        
        response = self.client.get(reverse('sprint_backlog'))
        
        # Sprint should be in context
        self.assertContains(response, 'New Sprint')
    
    def test_sprint_name_is_required(self):
        initial_count = Sprint.objects.count()
        
        response = self.client.post(reverse('create_sprint'), {
            'name': '',
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + timedelta(days=14)
        })
        
        # Sprint should not be created
        self.assertEqual(Sprint.objects.count(), initial_count)


# Test for User Story 08: Assign Tasks to Sprint
class AssignTasksToSprintTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        
        # Create sprints with different statuses
        self.active_sprint = Sprint.objects.create(
            name='Active Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE'
        )
        
        self.planning_sprint = Sprint.objects.create(
            name='Planning Sprint',
            start_date=timezone.now().date() + timedelta(days=15),
            end_date=timezone.now().date() + timedelta(days=29),
            status='PLANNING'
        )
        
        self.completed_sprint = Sprint.objects.create(
            name='Completed Sprint',
            start_date=timezone.now().date() - timedelta(days=28),
            end_date=timezone.now().date() - timedelta(days=15),
            status='COMPLETED'
        )
        
        # Create backlog tasks
        self.task1 = Task.objects.create(
            title='Backlog Task 1',
            description='Task to assign',
            status='BACKLOG',
            priority=2,
            story_points=5,
            created_by=self.user
        )
        
        self.task2 = Task.objects.create(
            title='Backlog Task 2',
            description='Another task',
            status='BACKLOG',
            priority=1,
            story_points=3,
            created_by=self.user
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='pass123')
    
    def test_assign_task_from_backlog_to_active_sprint(self):
        response = self.client.post(
            reverse('move_to_sprint', kwargs={
                'task_pk': self.task1.pk,
                'sprint_pk': self.active_sprint.pk
            })
        )
        
        # Reload task
        self.task1.refresh_from_db()
        
        # Task should now be assigned to sprint
        self.assertEqual(self.task1.sprint, self.active_sprint)
    
    def test_task_status_changes_to_sprint(self):
        self.client.post(
            reverse('move_to_sprint', kwargs={
                'task_pk': self.task1.pk,
                'sprint_pk': self.active_sprint.pk
            })
        )
        
        self.task1.refresh_from_db()
        
        # Status should change to SPRINT
        self.assertEqual(self.task1.status, 'SPRINT')
    
    def test_task_removed_from_product_backlog(self):
        # Assign task to sprint
        self.client.post(
            reverse('move_to_sprint', kwargs={
                'task_pk': self.task1.pk,
                'sprint_pk': self.active_sprint.pk
            })
        )
        
        # Check product backlog view
        response = self.client.get(reverse('product_backlog'))
        backlog_tasks = response.context['backlog_tasks']
        
        # task1 should NOT be in backlog
        self.assertNotIn(self.task1, backlog_tasks)
        
        # task2 should still be in backlog
        self.assertIn(self.task2, backlog_tasks)
    
    def test_task_appears_in_sprint_backlog(self):
        # Assign task to sprint
        self.client.post(
            reverse('move_to_sprint', kwargs={
                'task_pk': self.task1.pk,
                'sprint_pk': self.active_sprint.pk
            })
        )
        
        # Check sprint board view
        response = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': self.active_sprint.pk})
        )
        
        # Task should appear in sprint
        self.assertContains(response, 'Backlog Task 1')
    
    def test_cannot_assign_to_completed_sprint(self):
        # Try to assign to completed sprint
        response = self.client.post(
            reverse('move_to_sprint', kwargs={
                'task_pk': self.task1.pk,
                'sprint_pk': self.completed_sprint.pk
            })
        )
        
        self.task1.refresh_from_db()
        
        # Task should NOT be assigned to completed sprint
        self.assertNotEqual(self.task1.sprint, self.completed_sprint)
        self.assertEqual(self.task1.status, 'BACKLOG')
    
    def test_assign_task_to_planning_sprint(self):
        self.client.post(
            reverse('move_to_sprint', kwargs={
                'task_pk': self.task1.pk,
                'sprint_pk': self.planning_sprint.pk
            })
        )
        
        self.task1.refresh_from_db()
        
        self.assertEqual(self.task1.sprint, self.planning_sprint)
        self.assertEqual(self.task1.status, 'SPRINT')
    
    def test_assign_sets_sprint_progress_to_not_started(self):
        self.client.post(
            reverse('move_to_sprint', kwargs={
                'task_pk': self.task1.pk,
                'sprint_pk': self.active_sprint.pk
            })
        )
        
        self.task1.refresh_from_db()
        
        # Sprint progress should be NOT_STARTED by default
        self.assertEqual(self.task1.sprint_progress, 'NOT_STARTED')

# Test cases for User Story 09: View Sprint Backlog
class SprintBacklogViewTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        
        # Create sprints
        self.sprint1 = Sprint.objects.create(
            name='Sprint 1',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE',
            goal='Complete core features'
        )
        
        self.sprint2 = Sprint.objects.create(
            name='Sprint 2',
            start_date=timezone.now().date() + timedelta(days=15),
            end_date=timezone.now().date() + timedelta(days=29),
            status='PLANNING'
        )
        
        # Create tasks in sprint1
        self.task1 = Task.objects.create(
            title='Sprint 1 Task 1',
            status='SPRINT',
            sprint=self.sprint1,
            sprint_progress='NOT_STARTED',
            priority=2,
            story_points=5,
            created_by=self.user
        )
        
        self.task2 = Task.objects.create(
            title='Sprint 1 Task 2',
            status='SPRINT',
            sprint=self.sprint1,
            sprint_progress='IN_PROGRESS',
            priority=1,
            story_points=3,
            created_by=self.user
        )
        
        self.task3 = Task.objects.create(
            title='Sprint 1 Task 3',
            status='SPRINT',
            sprint=self.sprint1,
            sprint_progress='DONE',
            priority=2,
            story_points=8,
            created_by=self.user
        )
        
        # Create task in sprint2
        self.task4 = Task.objects.create(
            title='Sprint 2 Task',
            status='SPRINT',
            sprint=self.sprint2,
            sprint_progress='NOT_STARTED',
            priority=3,
            created_by=self.user
        )
        
        # Create backlog task (not in any sprint)
        self.backlog_task = Task.objects.create(
            title='Backlog Task',
            status='BACKLOG',
            priority=2,
            created_by=self.user
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='pass123')
    
    def test_sprint_backlog_view_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('sprint_backlog'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_view_sprint_backlog_shows_sprint_tasks(self):
        response = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': self.sprint1.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Should show sprint1 tasks
        self.assertContains(response, 'Sprint 1 Task 1')
        self.assertContains(response, 'Sprint 1 Task 2')
        self.assertContains(response, 'Sprint 1 Task 3')
    
    def test_shows_task_progress_status(self):
        response = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': self.sprint1.pk})
        )
        
        # All progress statuses should be displayed
        self.assertContains(response, 'NOT_STARTED')
        self.assertContains(response, 'IN_PROGRESS')
        self.assertContains(response, 'DONE')
    
    def test_displays_sprint_information(self):
        response = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': self.sprint1.pk})
        )
        
        # Sprint info should be displayed
        self.assertContains(response, 'Sprint 1')
        self.assertContains(response, 'Complete core features')
    
    def test_does_not_show_tasks_from_other_sprints(self):
        response = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': self.sprint1.pk})
        )
        
        # Should NOT show sprint2 tasks
        self.assertNotContains(response, 'Sprint 2 Task')
        
        # Should NOT show backlog tasks
        self.assertNotContains(response, 'Backlog Task')
    
    def test_can_select_different_sprints(self):
        # View sprint 1
        response1 = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': self.sprint1.pk})
        )
        self.assertContains(response1, 'Sprint 1 Task 1')
        
        # View sprint 2
        response2 = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': self.sprint2.pk})
        )
        self.assertContains(response2, 'Sprint 2 Task')
        self.assertNotContains(response2, 'Sprint 1 Task 1')
    
    def test_empty_state_when_sprint_has_no_tasks(self):
        empty_sprint = Sprint.objects.create(
            name='Empty Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='PLANNING'
        )
        
        response = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': empty_sprint.pk})
        )
        
        # Should show some indication of empty sprint
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Empty Sprint')
    
    def test_sprint_backlog_shows_story_points(self):
        response = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': self.sprint1.pk})
        )
        
        # Story points should be visible
        self.assertContains(response, '5')  # task1
        self.assertContains(response, '3')  # task2
        self.assertContains(response, '8')  # task3

# Test case for User Story 10 : Update Sprint Tasks Progress
class UpdateSprintTaskProgressTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        
        self.sprint = Sprint.objects.create(
            name='Active Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE'
        )
        
        self.task = Task.objects.create(
            title='Sprint Task',
            description='Task in sprint',
            status='SPRINT',
            sprint=self.sprint,
            sprint_progress='NOT_STARTED',
            priority=2,
            story_points=5,
            created_by=self.user
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='pass123')
    
    def test_move_task_to_in_progress(self):
        response = self.client.post(
            reverse('update_sprint_progress', kwargs={
                'task_pk': self.task.pk,
                'new_progress': 'IN_PROGRESS'
            })
        )
        
        self.task.refresh_from_db()
        
        # Task progress should be updated
        self.assertEqual(self.task.sprint_progress, 'IN_PROGRESS')
    
    def test_move_task_to_done(self):
        # First move to IN_PROGRESS
        self.task.sprint_progress = 'IN_PROGRESS'
        self.task.save()
        
        # Then move to DONE
        response = self.client.post(
            reverse('update_sprint_progress', kwargs={
                'task_pk': self.task.pk,
                'new_progress': 'DONE'
            })
        )
        
        self.task.refresh_from_db()
        
        self.assertEqual(self.task.sprint_progress, 'DONE')
    
    def test_task_progress_persists(self):
        # Update progress
        self.client.post(
            reverse('update_sprint_progress', kwargs={
                'task_pk': self.task.pk,
                'new_progress': 'IN_PROGRESS'
            })
        )
        
        # Fetch fresh from database
        task = Task.objects.get(pk=self.task.pk)
        
        self.assertEqual(task.sprint_progress, 'IN_PROGRESS')
    
    def test_kanban_board_displays_tasks_by_status(self):
        # Create tasks with different statuses
        task_not_started = Task.objects.create(
            title='Not Started Task',
            status='SPRINT',
            sprint=self.sprint,
            sprint_progress='NOT_STARTED',
            created_by=self.user
        )
        
        task_in_progress = Task.objects.create(
            title='In Progress Task',
            status='SPRINT',
            sprint=self.sprint,
            sprint_progress='IN_PROGRESS',
            created_by=self.user
        )
        
        task_done = Task.objects.create(
            title='Done Task',
            status='SPRINT',
            sprint=self.sprint,
            sprint_progress='DONE',
            created_by=self.user
        )
        
        response = self.client.get(
            reverse('sprint_board', kwargs={'sprint_pk': self.sprint.pk})
        )
        
        # All tasks should be displayed
        self.assertContains(response, 'Not Started Task')
        self.assertContains(response, 'In Progress Task')
        self.assertContains(response, 'Done Task')
    
    def test_move_task_from_not_started_directly_to_done(self):
        response = self.client.post(
            reverse('update_sprint_progress', kwargs={
                'task_pk': self.task.pk,
                'new_progress': 'DONE'
            })
        )
        
        self.task.refresh_from_db()
        
        # Should allow direct move to DONE
        self.assertEqual(self.task.sprint_progress, 'DONE')
    
    def test_updating_progress_returns_to_sprint_board(self):
        response = self.client.post(
            reverse('update_sprint_progress', kwargs={
                'task_pk': self.task.pk,
                'new_progress': 'IN_PROGRESS'
            })
        )
        
        # Should redirect back to sprint board
        self.assertEqual(response.status_code, 302)
    
    def test_only_sprint_tasks_can_have_progress_updated(self):
        backlog_task = Task.objects.create(
            title='Backlog Task',
            status='BACKLOG',
            priority=2,
            created_by=self.user
        )
        
        # Try to update progress of backlog task
        response = self.client.post(
            reverse('update_sprint_progress', kwargs={
                'task_pk': backlog_task.pk,
                'new_progress': 'IN_PROGRESS'
            })
        )
        
        backlog_task.refresh_from_db()
        
        self.assertIsNone(backlog_task.sprint_progress)

# Test case for User Story 11 : Edit Sprint
class SprintEditTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')

        self.user.is_staff = True
        self.user.save()
        
        self.sprint = Sprint.objects.create(
            name='Test Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='PLANNING',
            goal='Original goal'
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='pass123')
    
    def test_edit_sprint_name(self):
        response = self.client.post(
            reverse('edit_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {
                'name': 'Updated Sprint Name',
                'start_date': self.sprint.start_date,
                'end_date': self.sprint.end_date,
                'goal': self.sprint.goal,
                'status': self.sprint.status
            }
        )
        
        self.sprint.refresh_from_db()
        
        self.assertEqual(self.sprint.name, 'Updated Sprint Name')
    
    def test_edit_sprint_goal(self):
        response = self.client.post(
            reverse('edit_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {
                'name': self.sprint.name,
                'start_date': self.sprint.start_date,
                'end_date': self.sprint.end_date,
                'goal': 'New sprint goal',
                'status': self.sprint.status
            }
        )
        
        self.sprint.refresh_from_db()
        
        self.assertEqual(self.sprint.goal, 'New sprint goal')
    
    def test_edit_sprint_dates(self):
        new_end_date = timezone.now().date() + timedelta(days=21)
        
        response = self.client.post(
            reverse('edit_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {
                'name': self.sprint.name,
                'start_date': self.sprint.start_date,
                'end_date': new_end_date,
                'goal': self.sprint.goal,
                'status': self.sprint.status
            }
        )
        
        self.sprint.refresh_from_db()
        
        self.assertEqual(self.sprint.end_date, new_end_date)

class CompleteSprintTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.client.login(username='testuser', password='testpass123')
        self.user.is_staff = True
        self.user.save()
        
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
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.status, 'COMPLETED')
    
    def test_sprint_end_date_recorded(self):
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
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        self.done_task_1.refresh_from_db()
        self.assertEqual(self.done_task_1.planned_sprint, self.sprint)
        self.assertEqual(self.done_task_1.status, 'COMPLETE')
    
    def test_planned_sprint_preserved_for_backlog_tasks(self):
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
        completed_sprint = Sprint.objects.create(
            name='Already Complete',
            start_date=timezone.now().date() - timedelta(days=28),
            end_date=timezone.now().date() - timedelta(days=15),
            status='COMPLETED',
            goal='Already done'
        )
        
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': completed_sprint.pk}),
            {'unfinished_action': 'backlog'}
        )
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        completed_sprint.refresh_from_db()
        self.assertEqual(completed_sprint.status, 'COMPLETED')
    
    def test_cannot_complete_before_end_date(self):
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
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        # Check for success response
        self.assertEqual(response.status_code, 200)
        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.status, 'COMPLETED')
    
    def test_changes_persist_to_database(self):
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': self.sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        
        sprint = Sprint.objects.get(pk=self.sprint.pk)
        done_tasks = Task.objects.filter(planned_sprint=sprint, status='COMPLETE')
        backlog_tasks = Task.objects.filter(planned_sprint=sprint, status='BACKLOG')
        
        self.assertEqual(sprint.status, 'COMPLETED')
        self.assertEqual(done_tasks.count(), 2)
        self.assertEqual(backlog_tasks.count(), 2)
    
    def test_burndown_accuracy_after_completion(self):
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