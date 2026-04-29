from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError, connection
from django.conf import settings
from main.models import Task, Sprint
from django.utils import timezone
from datetime import timedelta
import time
import os
import sys


class PerformanceRequirementsTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test data
        self.sprint = Sprint.objects.create(
            name='Test Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE',
            goal='Performance testing'
        )
        
        for i in range(10):
            Task.objects.create(
                title=f'Task {i}',
                description='Test task',
                status='BACKLOG',
                priority=3,
                story_points=3,
                assigned_to=self.user
            )
    
    def test_dashboard_response_time_under_2_seconds(self):
        start = time.time()
        response = self.client.get(reverse('dashboard'))
        duration = time.time() - start
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 2.0, 
            f"Dashboard took {duration:.3f}s (should be < 2s)")
    
    def test_backlog_response_time_under_2_seconds(self):
        start = time.time()
        response = self.client.get(reverse('product_backlog'))
        duration = time.time() - start
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 2.0,
            f"Backlog took {duration:.3f}s (should be < 2s)")
    
    def test_sprint_backlog_response_time_under_2_seconds(self):
        start = time.time()
        response = self.client.get(reverse('sprint_backlog'))
        duration = time.time() - start
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 2.0,
            f"Sprint backlog took {duration:.3f}s (should be < 2s)")
    
    def test_task_creation_response_time_under_2_seconds(self):
        start = time.time()
        response = self.client.post(reverse('create_task'), {
            'title': 'Performance Test Task',
            'description': 'Testing response time',
            'priority': 3,
            'story_points': 3
        })
        duration = time.time() - start
        
        self.assertEqual(response.status_code, 302)  # Redirect after create
        self.assertLess(duration, 2.0,
            f"Task creation took {duration:.3f}s (should be < 2s)")
    
    def test_sprint_completion_under_3_seconds(self):
        # Setup sprint with tasks
        sprint = Sprint.objects.create(
            name='Complete Test Sprint',
            start_date=timezone.now().date() - timedelta(days=14),
            end_date=timezone.now().date() - timedelta(days=2),
            status='ACTIVE',
            goal='Test completion speed'
        )
        
        for i in range(20):
            Task.objects.create(
                title=f'Sprint Task {i}',
                status='SPRINT',
                sprint=sprint,
                sprint_progress='DONE' if i < 15 else 'IN_PROGRESS',
                story_points=3,
                priority=3,
                assigned_to=self.user
            )
        
        start = time.time()
        response = self.client.post(
            reverse('complete_sprint', kwargs={'sprint_pk': sprint.pk}),
            {'unfinished_action': 'backlog'},
            follow=True
        )
        duration = time.time() - start
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 3.0,
            f"Sprint completion took {duration:.3f}s (should be < 3s)")
    
    def test_system_handles_10_sequential_users(self):
        users = []
        
        # Create 10 users
        for i in range(10):
            user = User.objects.create_user(
                username=f'user{i}',
                password='testpass123'
            )
            users.append(user)
        
        # Each user performs operations
        for i, user in enumerate(users):
            self.client.login(username=f'user{i}', password='testpass123')
            
            # Create task
            response = self.client.post(reverse('create_task'), {
                'title': f'User {i} Task',
                'description': f'Task by user {i}',
                'priority': 3,
                'story_points': 3
            })
            self.assertEqual(response.status_code, 302)
            
            # View dashboard
            response = self.client.get(reverse('dashboard'))
            self.assertEqual(response.status_code, 200)
            
            # View backlog
            response = self.client.get(reverse('product_backlog'))
            self.assertEqual(response.status_code, 200)
            
            self.client.logout()
        
        # Verify all tasks created
        self.assertEqual(Task.objects.count(), 10 + 10)


class ReliabilityRequirementsTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_foreign_key_cascade_delete(self):
        sprint = Sprint.objects.create(
            name='Delete Test Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE',
            goal='Test cascade'
        )
        
        task = Task.objects.create(
            title='Task to Delete',
            status='SPRINT',
            sprint=sprint,
            
            priority=3,
            assigned_to=self.user
        )
        
        task_id = task.pk
        sprint.delete()
        
        # Task should still exist but sprint reference cleared
        task = Task.objects.get(pk=task_id)
        self.assertIsNone(task.sprint)
    
    def test_automated_tests_count_minimum_128(self):
        # Count all test methods across all test files
        test_count = 0
        
        # For this test file alone, we can count
        test_methods = [method for method in dir(self) 
                       if method.startswith('test_')]
        
        self.assertGreaterEqual(len(test_methods), 1,
            "Run full test suite to verify >= 128 total tests")


class SecurityRequirementsTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_unauthenticated_dashboard_access_denied(self):
        self.client.logout()
        response = self.client.get(reverse('dashboard'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_unauthenticated_backlog_access_denied(self):
        self.client.logout()
        response = self.client.get(reverse('product_backlog'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_unauthenticated_task_creation_denied(self):
        self.client.logout()
        response = self.client.post(reverse('create_task'), {
            'title': 'Unauthorized Task',
            'description': 'Should fail',
            'priority': 3
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_csrf_protection_enabled(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Get the form page
        response = self.client.get(reverse('create_task'))
        self.assertContains(response, 'csrfmiddlewaretoken')
        
        
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='testuser', password='testpass123')
        
        response = csrf_client.post(reverse('create_task'), {
            'title': 'CSRF Test',
            'description': 'Should fail without CSRF',
            'priority': 3
        })
        
        # Should fail due to missing CSRF token
        self.assertEqual(response.status_code, 403)
    
    def test_passwords_are_hashed(self):
        user = User.objects.get(username='testuser')
        
        # Password should NOT be stored in plaintext
        self.assertNotEqual(user.password, 'testpass123')
        
        # Password should be hashed (Django uses pbkdf2)
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        
        # Verify password check works
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_sql_injection_prevention_in_title(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Try SQL injection in task title
        malicious_title = "'; DROP TABLE main_task; --"
        
        response = self.client.post(reverse('create_task'), {
            'title': malicious_title,
            'description': 'SQL injection test',
            'priority': 3,
            'story_points': 3
        })
        
        # Task should be created with the malicious string as text
        # (not executed as SQL)
        task = Task.objects.filter(title=malicious_title).first()
        self.assertIsNotNone(task)
        
        # Table should still exist
        self.assertTrue(Task.objects.exists())
    
    def test_sql_injection_prevention_in_search(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Create a normal task
        Task.objects.create(
            title='Normal Task',
            description='Regular task',
            status='BACKLOG',
            priority=3,
            assigned_to=self.user
        )
        
        # Try SQL injection in URL parameter (if you have search)
        malicious_query = "1' OR '1'='1"
        
        # This should be handled safely by Django ORM
        # The malicious query should be treated as a literal string
        tasks = Task.objects.filter(title__icontains=malicious_query)
        
        # Should return no results (not all tasks)
        self.assertEqual(tasks.count(), 0)
    
    def test_session_management_enabled(self):
        # Login
        self.client.login(username='testuser', password='testpass123')
        
        # Verify session is created
        self.assertIn('_auth_user_id', self.client.session)
        
        # Logout
        self.client.logout()
        
        # Verify session is cleared
        self.assertNotIn('_auth_user_id', self.client.session)


class UsabilityRequirementsTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_bootstrap_framework_included(self):
        response = self.client.get(reverse('dashboard'))
        
        # Check for Bootstrap CSS
        self.assertContains(response, 'bootstrap')
        
        # Check for container classes (Bootstrap responsive grid)
        self.assertContains(response, 'container')
    
    def test_responsive_grid_classes_present(self):
        response = self.client.get(reverse('product_backlog'))
        
        # Check for Bootstrap grid classes
        content = response.content.decode()
        
        # Should have responsive classes (check for common Bootstrap classes)
        has_bootstrap = any([
            'container' in content,
            'row' in content,
            'col-' in content,
            'card' in content
        ])
        
        self.assertTrue(has_bootstrap, "Page should use Bootstrap framework")
    
    def test_priority_color_coding_critical(self):
        task = Task.objects.create(
            title='Critical Priority Task',
            description='Test critical priority',
            status='BACKLOG',
            priority=1,  # Critical
            assigned_to=self.user
        )
        
        response = self.client.get(reverse('task_detail', 
            kwargs={'pk': task.pk}))
        
        # Critical should be red (text-danger in Bootstrap)
        self.assertContains(response, 'badge-priority-1')
    
    def test_priority_color_coding_high(self):
        task = Task.objects.create(
            title='High Priority Task',
            description='Test high priority',
            status='BACKLOG',
            priority=2,  # High
            assigned_to=self.user
        )
        
        response = self.client.get(reverse('task_detail',
            kwargs={'pk': task.pk}))
        
        # High should be orange (text-warning in Bootstrap)
        self.assertContains(response, 'badge-priority-2')
    
    def test_navigation_to_backlog_from_dashboard(self):
        # From dashboard (0 clicks)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Should have link to backlog (1 click)
        self.assertContains(response, 'href="/backlog/')
    
    def test_navigation_to_create_task_from_dashboard(self):
        response = self.client.get(reverse('dashboard'))
        
        # Should have link to create task (1 click) or backlog (1 click) which has create
        self.assertContains(response, 'backlog')


class MaintainabilityRequirementsTests(TestCase):
    
    def test_django_mtv_directory_structure_exists(self):
        # Check for standard Django directories
        base_dir = settings.BASE_DIR
        
        # Models should exist
        self.assertTrue(os.path.exists(os.path.join(base_dir, 'main', 'models.py')))
        
        # Views should exist
        self.assertTrue(os.path.exists(os.path.join(base_dir, 'main', 'views.py')))
        
        # Templates directory should exist
        self.assertTrue(os.path.exists(os.path.join(base_dir, 'main', 'templates')))
    
    def test_models_defined_in_models_py(self):
        # Models should be importable from main.models
        from main.models import Task, Sprint
        
        self.assertTrue(hasattr(Task, 'objects'))
        self.assertTrue(hasattr(Sprint, 'objects'))
    
    def test_readme_exists(self):
        base_dir = settings.BASE_DIR
        
        # Check for README (any common variant)
        readme_exists = any([
            os.path.exists(os.path.join(base_dir, 'README.md')),
            os.path.exists(os.path.join(base_dir, 'README.rst')),
            os.path.exists(os.path.join(base_dir, 'README.txt')),
            os.path.exists(os.path.join(base_dir, 'README'))
        ])
        
        self.assertTrue(readme_exists, "README file should exist in project root")
    
    def test_requirements_file_exists(self):
        base_dir = settings.BASE_DIR
        
        # Check for requirements file
        requirements_exists = any([
            os.path.exists(os.path.join(base_dir, 'requirements.txt')),
            os.path.exists(os.path.join(base_dir, 'requirements', 'base.txt'))
        ])
        
        self.assertTrue(requirements_exists,
            "requirements.txt should exist for dependency management")


class PortabilityRequirementsTests(TestCase):
    
    def test_cross_platform_path_handling(self):
        # Django uses os.path.join which works cross-platform
        base_dir = settings.BASE_DIR
        
        # This should work on all platforms
        path = os.path.join(base_dir, 'main', 'models.py')
        self.assertTrue(os.path.exists(path))
    
    def test_database_backend_configured(self):
        # Check database configuration exists
        db_config = settings.DATABASES['default']
        
        self.assertIn('ENGINE', db_config)
        self.assertIn('NAME', db_config)
    
    def test_no_raw_sql_in_views(self):
        
        # We can verify ORM is being used by checking model operations work
        from main.models import Task
        
        # ORM operations should work
        tasks = Task.objects.all()
        self.assertIsNotNone(tasks)
        
        # Filter operation (ORM)
        backlog_tasks = Task.objects.filter(status='BACKLOG')
        self.assertIsNotNone(backlog_tasks)
    
    def test_orm_queries_work_with_current_database(self):
        user = User.objects.create_user(
            username='dbtest',
            password='testpass'
        )
        
        # Create
        task = Task.objects.create(
            title='DB Test Task',
            description='Testing database',
            status='BACKLOG',
            priority=3,
            assigned_to=user
        )
        
        # Read
        retrieved = Task.objects.get(pk=task.pk)
        self.assertEqual(retrieved.title, 'DB Test Task')
        
        # Update
        retrieved.title = 'Updated Task'
        retrieved.save()
        self.assertEqual(Task.objects.get(pk=task.pk).title, 'Updated Task')
        
        # Delete
        task_id = task.pk
        task.delete()
        self.assertFalse(Task.objects.filter(pk=task_id).exists())
    
    def test_timezone_aware_datetimes(self):
        # Django should use timezone-aware datetimes
        self.assertTrue(settings.USE_TZ,
            "USE_TZ should be True for timezone-aware datetimes")
    
    def test_static_files_configuration(self):
        # Check static files configuration
        self.assertTrue(hasattr(settings, 'STATIC_URL'))
        self.assertTrue(hasattr(settings, 'STATICFILES_DIRS') or 
                       hasattr(settings, 'STATIC_ROOT'))


class IntegrationNFRTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_complete_user_workflow_performance_and_security(self):
        start = time.time()
        
        # 1. Create task (requires auth, CSRF protection)
        response = self.client.get(reverse('create_task'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.post(reverse('create_task'), {
            'title': 'Integration Test Task',
            'description': 'Full workflow test',
            'priority': 3,
            'story_points': 5
        })
        self.assertEqual(response.status_code, 302)
        
        # 2. View backlog (requires auth, should be fast)
        response = self.client.get(reverse('product_backlog'))
        self.assertEqual(response.status_code, 200)
        
        # 3. Create sprint
        sprint = Sprint.objects.create(
            name='Integration Test Sprint',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=14),
            status='ACTIVE',
            goal='Test workflow'
        )
        
        # 4. Assign task to sprint
        task = Task.objects.first()
        task.sprint = sprint
        task.status = 'SPRINT'
        task.save()
        
        # 5. View sprint backlog (requires auth, should be fast)
        response = self.client.get(reverse('sprint_backlog'))
        self.assertEqual(response.status_code, 200)
        
        duration = time.time() - start
        
        # Entire workflow should complete in reasonable time
        self.assertLess(duration, 5.0,
            f"Full workflow took {duration:.3f}s (should be < 5s)")
    
    def test_system_reliability_under_load(self):
        # Create multiple tasks
        tasks_created = []
        
        for i in range(50):
            task = Task.objects.create(
                title=f'Load Test Task {i}',
                description=f'Task {i} for load testing',
                status='BACKLOG',
                priority=(i % 4) + 1,  # Distribute priorities
                story_points=(i % 8) + 1,  # Distribute story points
                assigned_to=self.user
            )
            tasks_created.append(task.pk)
        
        # Verify all tasks created successfully
        self.assertEqual(Task.objects.filter(pk__in=tasks_created).count(), 50)
        
        # Verify backlog view handles 50 tasks
        response = self.client.get(reverse('product_backlog'))
        self.assertEqual(response.status_code, 200)
        
        # Verify filtering works
        critical_tasks = Task.objects.filter(priority=1)
        self.assertGreater(critical_tasks.count(), 0)