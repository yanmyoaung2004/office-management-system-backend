"""API URL configuration."""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Auth
    path('auth/login', views.LoginView.as_view()),
    path('auth/logout', views.LogoutView.as_view()),
    path('auth/validate', views.CheckTokenView.as_view()),

    # Users
    path('users', views.UserListCreateView.as_view()),
    path('users/<str:pk>', views.UserDetailView.as_view()),

    # # Notifications
    path('notifications-all/mark-all-read/', 
        views.NotificationViewSet.as_view({'patch': 'mark_all_read'}), 
        name='notification-read-all'),
    path('notifications/', views.NotificationListCreateView.as_view(), name='notification-list'),
    path('notifications/<str:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),

    path('finance/', include('core.api.finance.urls')),
    path('admission/', include('core.api.admission.urls')),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
