from django.urls import path
from .views import ExamListCreateView, IntakeSemesterListView, ExamDetailView

urlpatterns = [
    path('exams/', ExamListCreateView.as_view(), name='exam-list-create'),
    path('exams/<str:pk>', ExamDetailView.as_view(), name='exam-list-create'),
    path('intakes-semester/', IntakeSemesterListView.as_view(), name='intake-list'),
]