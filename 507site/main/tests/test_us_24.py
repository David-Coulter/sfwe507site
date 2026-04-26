from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from main.models import Task, Sprint


class CompletedTasksViewTests(TestCase):    
    # Set up test data
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.developer = User.objects.create_user(
            username='developer',
            password='testpass123'
        )
        
        # Create sprints
        self.sprint1 = Sprint.objects.create(
            name='Sprint 1',
            status='COMPLETED'
        )
        
        self.sprint2 = Sprint.objects.create(
            name='Sprint 2',
            status='ACTIVE'
        )
        
        now = timezone.now()
        
        self.task1 = Task.objects.create(
            title='Completed Task 1',
            description='First completed task',
            status='COMPLETE',
            priority=2,
            story_points=5,
            assigned_to=self.developer,
            created_by=self.user,
            sprint=self.sprint1,
            completed_at=now - timedelta(days=2)
        )
        
        self.task2 = Task.objects.create(
            title='Completed Task 2',
            description='Second completed task',
            status='COMPLETE',
            priority=1,
            story_points=8,
            assigned_to=self.developer,
            created_by=self.user,
            sprint=self.sprint1,
            completed_at=now - timedelta(days=1)
        )
        
        self.task3 = Task.objects.create(
            title='Completed Task 3',
            description='Third completed task',
            status='COMPLETE',
            priority=3,
            story_points=3,
            assigned_to=self.user,
            created_by=self.user,
            sprint=self.sprint2,
            completed_at=now
        )
        
        self.task_backlog = Task.objects.create(
            title='Backlog Task',
            status='BACKLOG',
            priority=2,
            story_points=5,
            created_by=self.user
        )
        
        self.task_sprint = Task.objects.create(
            title='Sprint Task',
            status='SPRINT',
            priority=2,
            story_points=5,
            created_by=self.user,
            sprint=self.sprint2
        )
        
        self.client = Client()
    
    def test_view_requires_login(self):
        # Test that the view requires authentication
        response = self.client.get(reverse('completed_tasks'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_displays_only_completed_tasks(self):
        # Test that only completed tasks are shown
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('completed_tasks'))
        
        self.assertEqual(response.status_code, 200)
        
        # Verify only completed tasks appear
        tasks = response.context['tasks']
        self.assertEqual(tasks.count(), 3)
        
        # Verify completed tasks are present
        self.assertIn(self.task1, tasks)
        self.assertIn(self.task2, tasks)
        self.assertIn(self.task3, tasks)
        
        # Verify non-completed tasks are NOT present
        self.assertNotIn(self.task_backlog, tasks)
        self.assertNotIn(self.task_sprint, tasks)
    
    def test_sorted_by_completion_date_desc(self):
        # Test tasks are sorted by completion date (most recent first)
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('completed_tasks'))
        
        tasks = list(response.context['tasks'])
        
        # Verify order (most recent first)
        self.assertEqual(tasks[0], self.task3)  # Completed now
        self.assertEqual(tasks[1], self.task2)  # Completed 1 day ago
        self.assertEqual(tasks[2], self.task1)  # Completed 2 days ago
    
    def test_displays_summary_metrics(self):
        # Test that summary metrics are calculated correctly
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('completed_tasks'))
        
        # Verify metrics in context
        self.assertEqual(response.context['total_tasks'], 3)
        self.assertEqual(response.context['total_story_points'], 16)  # 5 + 8 + 3
        
        # Verify metrics appear in template
        self.assertContains(response, '3')  # Total tasks
        self.assertContains(response, '16')  # Total story points
    
    def test_filter_by_sprint(self):
        # Test filtering completed tasks by sprint
        self.client.login(username='testuser', password='testpass123')
        
        # Filter by Sprint 1
        response = self.client.get(
            reverse('completed_tasks'),
            {'sprint': self.sprint1.id}
        )
        
        tasks = response.context['tasks']
        
        # Should only show Sprint 1 tasks
        self.assertEqual(tasks.count(), 2)
        self.assertIn(self.task1, tasks)
        self.assertIn(self.task2, tasks)
        self.assertNotIn(self.task3, tasks)
        
        # Verify metrics reflect filtered data
        self.assertEqual(response.context['total_tasks'], 2)
        self.assertEqual(response.context['total_story_points'], 13)  # 5 + 8
    
    def test_shows_completion_timestamps(self):
        # Test that completion timestamps are displayed
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('completed_tasks'))
        
        # Verify completed_at appears for tasks
        for task in [self.task1, self.task2, self.task3]:
            self.assertTrue(task.completed_at is not None)
    
    def test_shows_assigned_user(self):
        # Test that assigned users are displayed
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('completed_tasks'))
        
        # Verify usernames appear
        self.assertContains(response, self.developer.username)
        self.assertContains(response, self.user.username)
    
    def test_links_to_task_detail(self):
        # Test that tasks link to their detail pages
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('completed_tasks'))
        
        # Verify task detail links exist
        self.assertContains(response, reverse('task_detail', args=[self.task1.pk]))
        self.assertContains(response, reverse('task_detail', args=[self.task2.pk]))
        self.assertContains(response, reverse('task_detail', args=[self.task3.pk]))
    
    def test_empty_state_when_no_completed_tasks(self):
        # Test empty state message when no completed tasks exist
        # Delete all completed tasks
        Task.objects.filter(status='COMPLETE').delete()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('completed_tasks'))
        
        # Verify empty state
        self.assertEqual(response.context['total_tasks'], 0)
        self.assertContains(response, 'No Completed Tasks')
    
    def test_groups_tasks_by_sprint(self):
        # Test that tasks are grouped by sprint in context
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('completed_tasks'))
        
        tasks_by_sprint = response.context['tasks_by_sprint']
        
        # Verify Sprint 1 group
        self.assertIn('Sprint 1', tasks_by_sprint)
        self.assertEqual(len(tasks_by_sprint['Sprint 1']), 2)
        
        # Verify Sprint 2 group
        self.assertIn('Sprint 2', tasks_by_sprint)
        self.assertEqual(len(tasks_by_sprint['Sprint 2']), 1)