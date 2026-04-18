from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('task_<int:pk>/view/', views.task_detail, name='task_detail'),
    path('task_<int:pk>/edit/', views.edit_task, name='edit_task'),
    path('task/create/', views.create_task, name='create_task'),
    path('task_<int:pk>/update-description/', views.update_task_description, name='update_task_description'),
    path('backlog/', views.product_backlog, name='product_backlog'),
    path('sprint_<int:sprint_pk>/board/', views.sprint_board, name='sprint_board'),
    path('sprint_backlog/', views.sprint_backlog, name='sprint_backlog'),
    path('task/<int:task_pk>/move-to-sprint/<int:sprint_pk>/', views.move_to_sprint, name='move_to_sprint'),
    path('task/<int:task_pk>/sprint-progress/<str:new_progress>/', views.update_sprint_progress, name='update_sprint_progress'),
    path('sprint/create/', views.create_sprint, name='create_sprint'),
    path('sprint_<int:sprint_pk>/edit/', views.edit_sprint, name='edit_sprint'),
    path('sprint_<int:sprint_pk>/complete/', views.complete_sprint, name='complete_sprint'),
    path('testing/', views.testing_queue, name='testing_queue'),
    path('tas_<int:pk>/ready-for-test/', views.mark_ready_for_test, name='mark_ready_for_test'),
    path('task_<int:pk>/pass-testing/', views.pass_testing, name='pass_testing'),
]
