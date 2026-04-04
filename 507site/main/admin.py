from django.contrib import admin
from .models import Task, Comment, Sprint


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority']
    search_fields = ['title', 'description']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('title', 'description', 'status', 'priority')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'created_by')
        }),
    )
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'text', 'created_at', 'text_preview']
    list_filter = ['author', 'created_at']
    search_fields = ['task__title', 'text']
    readonly_fields = ['created_at']

    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = "Comment"

@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'start_date', 'end_date', 'task_count', 'completed_tasks', 'created_at', 'updated_at']
    list_filter = ['status', 'status', 'start_date', 'end_date', 'created_at', 'updated_at']
    search_fields = ['name', 'goal', 'status']