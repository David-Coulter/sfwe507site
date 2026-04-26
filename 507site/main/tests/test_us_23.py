from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from main.models import Task, Sprint
import json

# User-Test-Case 23: View Sprint Report
class SprintReportTests(TestCase):
    
    def setUp(self):
        
        # Create users
        self.user1 = User.objects.create_user(
            username='dev1',
            password='testpass123',
            email='dev1@example.com'
        )
        
        self.user2 = User.objects.create_user(
            username='dev2',
            password='testpass123',
            email='dev2@example.com'
        )
        
        # Create completed sprint
        self.sprint = Sprint.objects.create(
            name='Sprint 1',
            status='COMPLETE',
            start_date=timezone.now().date() - timedelta(days=14),
            end_date=timezone.now().date() - timedelta(days=1),
            goal='Deliver core features'
        )
        
        # Create completed tasks
        self.completed_task1 = Task.objects.create(
            title='Completed Task 1',
            description='Test task',
            status='COMPLETE',
            priority=2,
            story_points=5,
            created_by=self.user1,
            assigned_to=self.user1,
            sprint=self.sprint,
            completed_at=timezone.now() - timedelta(days=2)
        )
        
        self.completed_task2 = Task.objects.create(
            title='Completed Task 2',
            description='Test task',
            status='COMPLETE',
            priority=1,
            story_points=8,
            created_by=self.user2,
            assigned_to=self.user2,
            sprint=self.sprint,
            completed_at=timezone.now() - timedelta(days=1)
        )
        
        # Create incomplete task
        self.incomplete_task = Task.objects.create(
            title='Incomplete Task',
            description='Not finished',
            status='SPRINT',
            priority=2,
            story_points=3,
            created_by=self.user1,
            assigned_to=self.user1,
            sprint=self.sprint
        )
        
        self.client = Client()
    
    # Sprint Report requires user authentication
    def test_requires_login(self):
        response = self.client.get(reverse('sprint_report', args=[self.sprint.pk]))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    # Sprint Report displays sprint info
    def test_displays_sprint_summary(self):
        self.client.login(username='dev1', password='testpass123')
        
        response = self.client.get(reverse('sprint_report', args=[self.sprint.pk]))
        
        # Verify sprint info is displayed
        self.assertContains(response, self.sprint.name)
        self.assertContains(response, self.sprint.goal)
        self.assertContains(response, 'Sprint Summary')
    
    # Sprint Report displays total and completed story points
    def test_shows_story_points_planned_vs_completed(self):
        self.client.login(username='dev1', password='testpass123')
        
        response = self.client.get(reverse('sprint_report', args=[self.sprint.pk]))
        
        # Total: 5 + 8 + 3 = 16
        # Completed: 5 + 8 = 13
        self.assertEqual(response.context['total_story_points'], 16)
        self.assertEqual(response.context['completed_story_points'], 13)
        self.assertEqual(response.context['incomplete_story_points'], 3)
        
        # Verify displayed in template
        self.assertContains(response, '16')  # Total
        self.assertContains(response, '13')  # Completed
    
    # Sprint Report lists completed tasks
    def test_lists_completed_tasks(self):
        self.client.login(username='dev1', password='testpass123')
        
        response = self.client.get(reverse('sprint_report', args=[self.sprint.pk]))
        
        # Verify completed tasks in context
        completed_tasks = response.context['completed_tasks']
        self.assertEqual(completed_tasks.count(), 2)
        
        # Verify tasks shown in template
        self.assertContains(response, 'Completed Task 1')
        self.assertContains(response, 'Completed Task 2')
        self.assertContains(response, '5 pts')
        self.assertContains(response, '8 pts')
    
    # Sprint Report lists incomplete tasks
    def test_lists_incomplete_tasks_separately(self):
        self.client.login(username='dev1', password='testpass123')
        
        response = self.client.get(reverse('sprint_report', args=[self.sprint.pk]))
        
        # Verify incomplete tasks in context
        incomplete_tasks = response.context['incomplete_tasks']
        self.assertEqual(incomplete_tasks.count(), 1)
        
        # Verify shown in template
        self.assertContains(response, 'Incomplete Task')
        self.assertContains(response, 'Incomplete Tasks')
    
    # Sprint Report shows task status breakdown in a pie chart
    def test_shows_task_status_breakdown(self):
        self.client.login(username='dev1', password='testpass123')
        
        response = self.client.get(reverse('sprint_report', args=[self.sprint.pk]))
        
        # Verify status breakdown data
        chart_labels = json.loads(response.context['chart_labels'])
        chart_data = json.loads(response.context['chart_data'])
        
        # Should have data for COMPLETE and SPRINT statuses
        self.assertIn('Complete', chart_labels)
        self.assertIn('Sprint', chart_labels)
        
        # Verify counts
        complete_index = chart_labels.index('Complete')
        sprint_index = chart_labels.index('Sprint')
        
        self.assertEqual(chart_data[complete_index], 2)  # 2 completed
        self.assertEqual(chart_data[sprint_index], 1)    # 1 in sprint
    
    # Sprint Report lists team member contributions
    def test_displays_team_member_contributions(self):
        self.client.login(username='dev1', password='testpass123')
        
        response = self.client.get(reverse('sprint_report', args=[self.sprint.pk]))
        
        # Verify team contributions in context
        team_contributions = response.context['team_contributions']
        self.assertEqual(len(team_contributions), 2)
        
        # Verify data for dev1
        dev1_contrib = next((c for c in team_contributions if c['name'] == 'dev1'), None)
        self.assertIsNotNone(dev1_contrib)
        self.assertEqual(dev1_contrib['total_tasks'], 2)      # 1 complete + 1 incomplete
        self.assertEqual(dev1_contrib['completed_tasks'], 1)  # 1 completed
        self.assertEqual(dev1_contrib['completed_points'], 5)
        
        # Verify data for dev2
        dev2_contrib = next((c for c in team_contributions if c['name'] == 'dev2'), None)
        self.assertIsNotNone(dev2_contrib)
        self.assertEqual(dev2_contrib['completed_points'], 8)
    
    # Sprint Report exports to CSV
    def test_can_export_csv(self):
        self.client.login(username='dev1', password='testpass123')
        
        response = self.client.get(reverse('export_sprint_report_csv', args=[self.sprint.pk]))
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        
        # Verify CSV contains sprint data
        content = response.content.decode('utf-8')
        self.assertIn('Sprint Report', content)
        self.assertIn(self.sprint.name, content)
        self.assertIn('Completed Task 1', content)
        self.assertIn('Completed Task 2', content)
    
    # Sprint Report CSV export includes all sections
    def test_csv_includes_all_sections(self):
        self.client.login(username='dev1', password='testpass123')
        
        response = self.client.get(reverse('export_sprint_report_csv', args=[self.sprint.pk]))
        content = response.content.decode('utf-8')
        
        # Verify all sections present
        self.assertIn('Story Points Summary', content)
        self.assertIn('Completed Tasks', content)
        self.assertIn('Incomplete Tasks', content)
        self.assertIn('Team Member Contributions', content)
    
    # Sprint Report can select different sprints
    def test_can_select_different_sprints(self):
        # Create another sprint
        sprint2 = Sprint.objects.create(
            name='Sprint 2',
            status='COMPLETE',
            start_date=timezone.now().date() - timedelta(days=28),
            end_date=timezone.now().date() - timedelta(days=15)
        )
        
        self.client.login(username='dev1', password='testpass123')
        
        # View sprint 2 report
        response = self.client.get(reverse('sprint_report', args=[sprint2.pk]))
        
        # Verify correct sprint
        self.assertEqual(response.context['sprint'], sprint2)
        
        # Verify sprint selector has both sprints
        all_sprints = response.context['all_sprints']
        self.assertIn(self.sprint, all_sprints)
        self.assertIn(sprint2, all_sprints)
    
    # Sprint Report shows completion rate
    def test_calculates_completion_rate(self):
        self.client.login(username='dev1', password='testpass123')
        
        response = self.client.get(reverse('sprint_report', args=[self.sprint.pk]))
        
        # 13 completed / 16 total = 81.25%
        completion_rate = response.context['completion_rate']
        self.assertAlmostEqual(completion_rate, 81.3, places=0)

# Sprint Report PDF export tests
class SprintReportPDFExportTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.sprint = Sprint.objects.create(
            name='Test Sprint',
            status='COMPLETE',
            start_date=timezone.now().date() - timedelta(days=14),
            end_date=timezone.now().date() - timedelta(days=1),
            goal='Test goal'
        )
        
        Task.objects.create(
            title='Test Task',
            status='COMPLETE',
            priority=2,
            story_points=5,
            created_by=self.user,
            sprint=self.sprint,
            completed_at=timezone.now()
        )
        
        self.client = Client()
    
    # PDF export requires user authentication
    def test_pdf_export_requires_login(self):
        response = self.client.get(reverse('export_sprint_report_pdf', args=[self.sprint.pk]))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    # PDF export returns PDF
    def test_pdf_export_returns_pdf(self):
        self.client.login(username='testuser', password='testpass123')
        
        try:
            response = self.client.get(reverse('export_sprint_report_pdf', args=[self.sprint.pk]))
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertIn('attachment', response['Content-Disposition'])
            self.assertIn('.pdf', response['Content-Disposition'])
        except ImportError:
            # WeasyPrint not installed - skip test
            self.skipTest('WeasyPrint not installed')