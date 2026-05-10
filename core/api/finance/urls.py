from django.urls import path
from .views import IntakeListView, SchoolFeeToggleView, IntakeEnrollmentListView

urlpatterns = [
    path('intakes/', IntakeListView.as_view(), name='intake-list'),
    path('intakes/<str:intake_id>/enrollments', IntakeEnrollmentListView.as_view(), name='intake-students'),

    path('fee/', SchoolFeeToggleView.as_view(), name='school-fee-update'),

]