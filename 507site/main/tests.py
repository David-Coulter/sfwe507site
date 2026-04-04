from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from main.models import Task, Comment


class UserAuthenticationTests(TestCase):
    #Test cases for User Story 16 (Registration) and User Story 18 (Login)
    
    def setUp(self):
        #Set up test client and test user
        self.client = Client()
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPW123!'
        )
    
    def test_user_registration_success(self):
        #TC001: Successful user registration with valid data
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'MultiPass123!',
            'password2': 'MultiPass123!',
        })
        
        # Check user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        # Check redirect to login
        self.assertEqual(response.status_code, 302)
        
    def test_user_registration_password_mismatch(self):
        #TC002: Registration fails with mismatched passwords
        response = self.client.post(reverse('register'), {
            'username': 'sfwe507team6',
            'email': 'sfwe507team6@gmail.com',
            'password1': 'davidrules123!',
            'password2': 'davidstinks456!',
        })
        
        # User should not be created
        self.assertFalse(User.objects.filter(username='newuser').exists())
        
    def test_user_login_success(self):
        #TC003: Successful login with valid credentials
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'TestPW123!',
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        
        # User should be authenticated
        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)
        
    def test_user_login_invalid_credentials(self):
        #TC04: Login fails with invalid credentials
        response = self.client.post(reverse('login'), {
            'username': 'fakeuser',
            'password': 'WrongPassword123!',
        })
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        
        # User should not be authenticated
        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)


class TaskCreationTests(TestCase):
    #Test cases for User Story 01 (Create Task)

    def setUp(self):
        #Set up test user and client
        self.user = User.objects.create_user(
            username='testuser2',
            password='testpass123$'
        )
        self.client = Client()
        self.client.login(username='testuser2', password='testpass123$')
    
    def test_create_task_valid_data(self):
        #TC005: Create task with all valid fields
        response = self.client.post(reverse('create_task'), {
            'title': 'User Story 25: Add user profile page',
            'description': '## User Story\nAs a user, I want to view my profile',
            'priority': 2,
            'story_points': 5,
            'estimated_hours': 8.5,
        })
        
        # Check task was created
        self.assertTrue(Task.objects.filter(title='User Story 25: Add user profile page').exists())
        
        # Check task fields
        task = Task.objects.get(title='User Story 25: Add user profile page')
        self.assertEqual(task.priority, 2)
        self.assertEqual(task.story_points, 5)
        self.assertEqual(task.estimated_hours, 8.5)
        self.assertEqual(task.status, 'BACKLOG')
        self.assertEqual(task.created_by, self.user)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        
    def test_create_task_missing_required_fields(self):
        #TC006: Task creation fails without required title
        initial_count = Task.objects.count()
        
        response = self.client.post(reverse('create_task'), {
            'title': '',
            'description': 'Test description',
        })
        
        # No new task created
        self.assertEqual(Task.objects.count(), initial_count)
        
        # Form should have errors
        self.assertEqual(response.status_code, 200)


class TaskEditingTests(TestCase):
    #Test cases for User Story 02 (Priority), User Story 03 (Edit), User Story 04 (Assign)
    
    def setUp(self):
        #Set up test users and task
        self.user1 = User.objects.create_user(username='alice', password='pass123')
        self.user2 = User.objects.create_user(username='bob', password='pass123')
        
        self.task = Task.objects.create(
            title='Original Title',
            description='Original description',
            priority=3,
            story_points=3,
            status='BACKLOG',
            created_by=self.user1
        )
        
        self.client = Client()
        self.client.login(username='alice', password='pass123')
    
    def test_edit_task_changes_persist(self):
        #TC007: Task edits save correctly
        response = self.client.post(reverse('edit_task', args=[self.task.pk]), {
            'title': 'Updated Title - Bug Fix',
            'description': self.task.description,
            'priority': 1,
            'story_points': 8,
            'status': 'BACKLOG',
        })
        
        # Reload task from database
        self.task.refresh_from_db()
        
        # Check changes
        self.assertEqual(self.task.title, 'Updated Title - Bug Fix')
        self.assertEqual(self.task.priority, 1)
        self.assertEqual(self.task.story_points, 8)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        
    def test_change_priority_updates_field(self):
        #TC008: Priority changes save correctly
        self.client.post(reverse('edit_task', args=[self.task.pk]), {
            'title': self.task.title,
            'description': self.task.description,
            'priority': 1,  # Critical
            'story_points': self.task.story_points,
        })
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.priority, 1)
        
    def test_assign_task_to_user(self):
        #TC009: Task assignment works correctly
        self.client.post(reverse('edit_task', args=[self.task.pk]), {
            'title': self.task.title,
            'description': self.task.description,
            'priority': self.task.priority,
            'story_points': self.task.story_points,
            'estimated_hours': self.task.estimated_hours if self.task.estimated_hours else '',
            'assigned_to': self.user2.pk,
        })
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to, self.user2)
        
    def test_reassign_task_to_different_user(self):
        #TC010: Task can be reassigned
        # First assign to bob
        self.task.assigned_to = self.user2
        self.task.save()
        
        # Then reassign to alice
        self.client.post(reverse('edit_task', args=[self.task.pk]), {
            'title': self.task.title,
            'description': self.task.description,
            'priority': self.task.priority,
            'story_points': self.task.story_points,
            'estimated_hours': self.task.estimated_hours if self.task.estimated_hours else '',
            'assigned_to': self.user1.pk,
        })
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to, self.user1)
        
    def test_unassign_task(self):
        #TC011: Task can be unassigned
        self.task.assigned_to = self.user2
        self.task.save()
        
        self.client.post(reverse('edit_task', args=[self.task.pk]), {
            'title': self.task.title,
            'description': self.task.description,
            'priority': self.task.priority,
            'story_points': self.task.story_points,
            'estimated_hours': self.task.estimated_hours if self.task.estimated_hours else '',
            'assigned_to': '',
        })
        
        self.task.refresh_from_db()
        self.assertIsNone(self.task.assigned_to)


class CommentTests(TestCase):
    #Test cases for User Story 06 (Comments)
    
    def setUp(self):
        #Set up test user and task
        self.user = User.objects.create_user(username='david', password='pass123')
        self.task = Task.objects.create(
            title='Test Task',
            description='Test description',
            created_by=self.user
        )
        
        self.client = Client()
        self.client.login(username='david', password='pass123')
    
    def test_add_comment_to_task(self):
        #TC012: Post new comment on task
        response = self.client.post(reverse('task_detail', args=[self.task.pk]), {
            'text': 'This task is ready for testing. All acceptance criteria met.'
        })
        
        # Check comment was created
        self.assertEqual(Comment.objects.filter(task=self.task).count(), 1)
        
        # Check comment content
        comment = Comment.objects.get(task=self.task)
        self.assertEqual(comment.text, 'This task is ready for testing. All acceptance criteria met.')
        self.assertEqual(comment.author, self.user)
        
    def test_comment_character_limit(self):
        #TC013: Comments respect 1000 character limit
        long_text = 'x' * 1500  # 1500 characters
        
        response = self.client.post(reverse('task_detail', args=[self.task.pk]), {
            'text': long_text
        })
        
        # Comment should not be created
        self.assertEqual(Comment.objects.filter(task=self.task).count(), 0)
        
    def test_comments_display_chronologically(self):
        #TC014: Comments ordered by creation time (newest first)
        Comment.objects.create(task=self.task, author=self.user, text='First comment')
        Comment.objects.create(task=self.task, author=self.user, text='Second comment')
        Comment.objects.create(task=self.task, author=self.user, text='Third comment')
        
        # Get comments in order
        comments = Comment.objects.filter(task=self.task)
        
        # Check order (newest first)
        self.assertEqual(comments[0].text, 'Third comment')
        self.assertEqual(comments[1].text, 'Second comment')
        self.assertEqual(comments[2].text, 'First comment')


class TaskDetailViewTests(TestCase):
    #Test cases for User Story 05 (View Task Details)
    
    def setUp(self):
        #Set up test data
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.task = Task.objects.create(
            title='Test Task',
            description='## Description\n- [ ] Item 1\n- [x] Item 2',
            priority=2,
            story_points=5,
            estimated_hours=8.5,
            status='BACKLOG',
            created_by=self.user,
            assigned_to=self.user
        )
        Comment.objects.create(task=self.task, author=self.user, text='Test comment')
        
        self.client = Client()
        self.client.login(username='testuser', password='pass123')
    
    def test_view_complete_task_information(self):
        #TC015: All task fields visible on detail page
        response = self.client.get(reverse('task_detail', args=[self.task.pk]))
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Check context contains task
        self.assertEqual(response.context['task'], self.task)
        
        # Check all fields present in response
        self.assertContains(response, 'Test Task')
        self.assertContains(response, 'High') 
        self.assertContains(response, '5') 
        self.assertContains(response, '8.5') 
        self.assertContains(response, 'testuser')
        self.assertContains(response, 'Comments (1)') 


class DashboardTests(TestCase):
    #Test cases for User Story 17 (Dashboard)
    
    def setUp(self):
        #Set up test data
        self.user1 = User.objects.create_user(username='alice', password='pass123')
        self.user2 = User.objects.create_user(username='bob', password='pass123')
        
        # Create tasks with different statuses
        Task.objects.create(title='Backlog 1', status='BACKLOG', created_by=self.user1)
        Task.objects.create(title='Backlog 2', status='BACKLOG', created_by=self.user1)
        Task.objects.create(title='Sprint 1', status='SPRINT', created_by=self.user1)
        Task.objects.create(title='Testing 1', status='TESTING', created_by=self.user1)
        Task.objects.create(title='Complete 1', status='COMPLETE', created_by=self.user1)
        
        # Create tasks assigned to alice
        Task.objects.create(
            title='Alice Task 1', 
            status='BACKLOG', 
            created_by=self.user1,
            assigned_to=self.user1
        )
        Task.objects.create(
            title='Alice Task 2', 
            status='SPRINT', 
            created_by=self.user1,
            assigned_to=self.user1
        )
        
        # Create task assigned to bob
        Task.objects.create(
            title='Bob Task', 
            status='BACKLOG', 
            created_by=self.user2,
            assigned_to=self.user2
        )
        
        self.client = Client()
        self.client.login(username='alice', password='pass123')
    
    def test_dashboard_task_count_accuracy(self):
        #TC016: Dashboard shows correct task counts
        response = self.client.get(reverse('dashboard'))
        
        # Check status code
        self.assertEqual(response.status_code, 200)
        
        # Check counts in context
        backlog_count = Task.objects.filter(status='BACKLOG').count()
        sprint_count = Task.objects.filter(status='SPRINT').count()
        testing_count = Task.objects.filter(status='TESTING').count()
        complete_count = Task.objects.filter(status='COMPLETE').count()
        
        self.assertEqual(backlog_count, 4)
        self.assertEqual(sprint_count, 2)
        self.assertEqual(testing_count, 1)
        self.assertEqual(complete_count, 1)
        
    def test_my_tasks_shows_assigned_only(self):
        #TC017: User sees only their assigned tasks
        response = self.client.get(reverse('dashboard'))
        
        # Get alice's assigned tasks
        my_tasks = Task.objects.filter(assigned_to=self.user1)
        
        # Should have exactly 2 tasks
        self.assertEqual(my_tasks.count(), 2)
        
        # Check tasks are correct
        self.assertTrue(my_tasks.filter(title='Alice Task 1').exists())
        self.assertTrue(my_tasks.filter(title='Alice Task 2').exists())
        
        # Bob's task should not be included
        self.assertFalse(my_tasks.filter(title='Bob Task').exists())


class TaskModelTests(TestCase):
    #Test Task model methods and properties
    
    def setUp(self):
        #Set up test user#
        self.user = User.objects.create_user(username='testuser', password='pass123')
    
    def test_task_string_representation(self):
        #Test __str__ method
        task = Task.objects.create(
            title='Test Task',
            description='Description',
            status='BACKLOG',
            created_by=self.user
        )
        
        expected = 'Test Task [Product Backlog]'
        self.assertEqual(str(task), expected)
        
    def test_task_default_values(self):
        #Test default field values
        task = Task.objects.create(
            title='Test Task',
            description='Description',
            created_by=self.user
        )
        
        # Check defaults
        self.assertEqual(task.status, 'BACKLOG')
        self.assertEqual(task.priority, 3)  # Medium
        self.assertEqual(task.story_points, 1)
        self.assertIsNone(task.assigned_to)
        
    def test_task_ordering(self):
        #Test tasks ordered by priority then created date
        task1 = Task.objects.create(
            title='Low Priority',
            description='Desc',
            priority=4,
            created_by=self.user
        )
        task2 = Task.objects.create(
            title='Critical Priority',
            description='Desc',
            priority=1,
            created_by=self.user
        )
        task3 = Task.objects.create(
            title='High Priority',
            description='Desc',
            priority=2,
            created_by=self.user
        )
        
        tasks = Task.objects.all()
        
        # Should be ordered: Critical, High, Low
        self.assertEqual(tasks[0], task2)
        self.assertEqual(tasks[1], task3)
        self.assertEqual(tasks[2], task1)


class CommentModelTests(TestCase):
    #Test Comment model
    
    def setUp(self):
        #Set up test data
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.task = Task.objects.create(
            title='Test Task',
            description='Description',
            created_by=self.user,
        )
    
    def test_comment_string_representation(self):
        comment = Comment.objects.create(
            task=self.task,
            author=self.user,
            text='Test comment'
        )
        
        result = str(comment)
        self.assertIn('testuser', result)
        self.assertIn('commented on', result)
        self.assertIn('Test Task', result)
        
    def test_comment_relationship_to_task(self):
        #Test related_name 'comments' works
        Comment.objects.create(task=self.task, author=self.user, text='Comment 1')
        Comment.objects.create(task=self.task, author=self.user, text='Comment 2')
        
        # Access via related name
        comments = self.task.comments.all()
        
        self.assertEqual(comments.count(), 2)
