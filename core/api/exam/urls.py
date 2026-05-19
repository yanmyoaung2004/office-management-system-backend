from django.urls import path
from .views import ExamListCreateView, IntakeSemesterListView, ExamDetailView, ExamPaperUploadView, ExamResultView

urlpatterns = [
    path('exams/', ExamListCreateView.as_view(), name='exam-list-create'),
    path('exams/<str:pk>', ExamDetailView.as_view(), name='exam-list-create'),
    path('exam-papers/<str:id>/upload-questions/', 
         ExamPaperUploadView.as_view(), 
         name='exampaper-upload-questions'),
    path('exam-result/', ExamResultView.as_view(), name='exam-result'),
        

    path('intakes-semester/', IntakeSemesterListView.as_view(), name='intake-list'),
]