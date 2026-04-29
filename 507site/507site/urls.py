from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from main.views import RememberMeLoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    path(
        'accounts/login/',
        RememberMeLoginView.as_view(),
        name='login'
    ),

    path(
        'accounts/logout/',
        LogoutView.as_view(),
        name='logout'
    ),

    path('', include('main.urls')),
]