"""API URL configuration."""
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
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
    path('students/<str:pk>/update-school-id', views.UpdateSchoolIdView.as_view()),  
    

    # # Enquiries
    path('enquiries', views.EnquiryListCreateView.as_view()),
    path('enquiries/<str:pk>', views.EnquiryDetailView.as_view()),
    path('enquiries/<str:enquiry_id>/followups', views.EnquiryFollowUpListCreateView.as_view()),

    # # Follow-ups
    path('followups/<str:pk>', views.FollowUpDetailView.as_view()),


    # # Dropouts
    path('dropouts', views.DropoutListCreateView.as_view()),
    path('reactivate/', views.CreateEnrollmentView.as_view(), name='reactivate'),
    # path('dropouts/<str:pk>', views.DropoutDetailView.as_view()),

    path('chart-data', views.DashboardSummaryView.as_view(), name='chart-data'),
    path('filter-data', views.FilterDataView.as_view(), name='filter-data'),
    
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
