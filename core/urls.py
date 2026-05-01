"""API URL configuration."""
from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/login', views.LoginView.as_view()),
    path('auth/logout', views.LogoutView.as_view()),

    # Check token
    path('auth/validate', views.CheckTokenView.as_view()),

    # Users
    path('users', views.UserListCreateView.as_view()),
    path('users/<str:pk>', views.UserDetailView.as_view()),

    # Majors
    path('majors', views.MajorListCreateView.as_view()),
    path('majors/<str:pk>', views.MajorDetailView.as_view()),

    # # Intakes
    path('intakes', views.IntakeListCreateView.as_view()),
    path('intakes/<str:pk>', views.IntakeDetailView.as_view()),
    path('intakes/<str:intake_id>/enrollments', views.IntakeEnrollmentListView.as_view(), name='intake-students'),

    # # Students
    path('students', views.StudentListCreateView.as_view()),
    path('students/<str:pk>', views.StudentDetailView.as_view()),

    # # Enquiries
    path('enquiries', views.EnquiryListCreateView.as_view()),
    path('enquiries/<str:pk>', views.EnquiryDetailView.as_view()),
    path('enquiries/<str:enquiry_id>/followups', views.EnquiryFollowUpListCreateView.as_view()),

    # # Follow-ups
    path('followups/<str:pk>', views.FollowUpDetailView.as_view()),

    # # Reports
    # path('reports', views.ReportListCreateView.as_view()),
    # path('reports/stats', views.ReportStatsView.as_view()),
    # path('reports/<str:pk>', views.ReportDetailView.as_view()),

    # # Dropouts
    path('dropouts', views.DropoutListCreateView.as_view()),
    path('reactivate/', views.CreateEnrollmentView.as_view(), name='reactivate'),
    # path('dropouts/<str:pk>', views.DropoutDetailView.as_view()),

    # # Notifications
    path('notifications-all/mark-all-read/', 
        views.NotificationViewSet.as_view({'patch': 'mark_all_read'}), 
        name='notification-read-all'),
    path('notifications/', views.NotificationListCreateView.as_view(), name='notification-list'),
    path('notifications/<str:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),

    path('chart-data', views.DashboardSummaryView.as_view(), name='chart-data'),
    path('filter-data', views.FilterDataView.as_view(), name='filter-data'),
]
