from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, datetime
from main.models import Task, Sprint
import json

# User-Test-Case 22: View Burndown
class SprintBurndownChartTests(TestCase):
    
    def setUp(self):
        
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        today = timezone.now().date()
        self.sprint = Sprint.objects.create(
            name='Test Sprint',
            status='ACTIVE',
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=7), 
            goal='Complete test features'
        )
        
        self.sprint_no_dates = Sprint.objects.create(
            name='Sprint Without Dates',
            status='PLANNING'
        )
        
        self.task1 = Task.objects.create(
            title='Task 1',
            description='Test task 1',
            status='COMPLETE',
            priority=2,
            story_points=5,
            created_by=self.user,
            sprint=self.sprint,
            completed_at=today - timedelta(days=5)
        )
        
        self.task2 = Task.objects.create(
            title='Task 2',
            description='Test task 2',
            status='COMPLETE',
            priority=2,
            story_points=3,
            created_by=self.user,
            sprint=self.sprint,
            completed_at=today - timedelta(days=3)
        )
        
        self.task3 = Task.objects.create(
            title='Task 3',
            description='Test task 3',
            status='SPRINT',
            priority=2,
            story_points=8,
            created_by=self.user,
            sprint=self.sprint
        )
        
        self.client = Client()
    
    # Burndown view requires authentication
    def test_view_requires_login(self):
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    # Burndown view displays burndown chart for sprint with dates
    def test_displays_burndown_chart_for_sprint(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/sprint_burndown.html')
        
        self.assertEqual(response.context['sprint'], self.sprint)
    
    # Burndown view shows error message for sprint without dates
    def test_shows_error_for_sprint_without_dates(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint_no_dates.pk]))
        
        self.assertIn('error', response.context)
        self.assertContains(response, 'start and end dates')
    
    # Burndown view calculates total story points
    def test_calculates_total_story_points(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        
        # Total: 5 + 3 + 8 = 16
        self.assertEqual(response.context['total_story_points'], 16)
    
    # Burndown view calculates ideal burndown
    def test_ideal_burndown_is_linear(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        
        ideal_burndown = json.loads(response.context['ideal_burndown'])
        
        self.assertGreater(len(ideal_burndown), 0)
        
        self.assertGreater(ideal_burndown[0], ideal_burndown[-1])
        self.assertLess(ideal_burndown[-1], 5)
    
    # Burndown view calculates actual burndown
    def test_actual_burndown_reflects_completed_tasks(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        
        actual_burndown = json.loads(response.context['actual_burndown'])
        
        self.assertGreater(len(actual_burndown), 0)
    
    # Burndown view chart labels cover all days in sprint
    def test_chart_labels_match_sprint_days(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        
        chart_labels = json.loads(response.context['chart_labels'])
        
        expected_days = 15 
        self.assertEqual(len(chart_labels), expected_days)
    
    # Burndown view identifies weekend days
    def test_identifies_weekend_days(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))

        weekend_indices = json.loads(response.context['weekend_indices'])
        
        self.assertIsInstance(weekend_indices, list)
    
    # Burndown view calculates sprint status (ahead/behind/on-track)
    def test_shows_sprint_ahead_behind_status(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        
        self.assertIn('status', response.context)
        self.assertIn(response.context['status'], ['ahead', 'behind', 'on-track'])
        

        self.assertIn('status_message', response.context)
    
    # Burndown view displays completion percentage
    def test_displays_completion_percentage(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        
        self.assertEqual(response.context['completed_tasks'], 2)
        self.assertEqual(response.context['total_tasks'], 3)
        self.assertAlmostEqual(response.context['completion_percentage'], 66.7, places=1)
    
    # Burndown view allows user to select different sprints
    def test_can_select_different_sprints(self):
        
        sprint2 = Sprint.objects.create(
            name='Sprint 2',
            status='COMPLETE',
            start_date=timezone.now().date() - timedelta(days=20),
            end_date=timezone.now().date() - timedelta(days=10),
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[sprint2.pk]))
        
        self.assertEqual(response.context['sprint'], sprint2)
        
        all_sprints = response.context['all_sprints']
        self.assertIn(self.sprint, all_sprints)
        self.assertIn(sprint2, all_sprints)
    
    # Burndown chart updates when a task is completed
    def test_chart_updates_when_task_completed(self):
        self.client.login(username='testuser', password='testpass123')
        
        response1 = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        initial_completed = response1.context['completed_tasks']
        
        self.task3.status = 'COMPLETE'
        self.task3.completed_at = timezone.now()
        self.task3.save()
        
        response2 = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        updated_completed = response2.context['completed_tasks']
        
        self.assertEqual(updated_completed, initial_completed + 1)
    
    # Burndown view includes sprint start/end dates
    def test_includes_sprint_timeline_info(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sprint_burndown', args=[self.sprint.pk]))
        
        self.assertContains(response, 'Start Date')
        self.assertContains(response, 'End Date')