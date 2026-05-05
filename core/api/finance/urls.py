from django.urls import path
from .views import StudentListView, IntakeListView, SchoolFeeUpdateView

urlpatterns = [
    path('students/', StudentListView.as_view(), name='student-list'),
    path('intakes/', IntakeListView.as_view(), name='intake-list'),
    path('fee/<str:pk>/', SchoolFeeUpdateView.as_view(), name='school-fee-update'),

]