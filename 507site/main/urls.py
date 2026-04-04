from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('task_<int:pk>/view/', views.task_detail, name='task_detail'),
    path('task_<int:pk>/edit/', views.edit_task, name='edit_task'),
    path('task/create/', views.create_task, name='create_task'),
    path('task/<int:pk>/update-description/', views.update_task_description, name='update_task_description'),
    path('backlog/', views.product_backlog, name='product_backlog'),
    path('task/<int:task_pk>/move-to-sprint/<int:sprint_pk>/', views.move_to_sprint, name='move_to_sprint'),
]