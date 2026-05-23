from django.urls import path
from .views import ExamListCreateView, IntakeSemesterListView, ExamDetailView, ExamPaperComponentUploadView, ExamResultView, SubjectBulkResultView, ShareLinkCreateView, ShareLinkAccessView, ShareLinkResultSubmitView, IntakeYearResultsView, SemesterProgressResultView

urlpatterns = [
    path('exams/', ExamListCreateView.as_view(), name='exam-list-create'),
    path('exams/<str:pk>', ExamDetailView.as_view(), name='exam-detail'),
    path('exam-papers/<str:id>/upload-questions/', 
         ExamPaperComponentUploadView.as_view(),
         name='exampaper-upload-questions'),
    path('exam-components/<str:id>/upload-questions/', 
         ExamPaperComponentUploadView.as_view(), 
         name='exam-component-upload'),
    path('exam-result/', ExamResultView.as_view(), name='exam-result'),
    path('exam-result/by-subject/', SubjectBulkResultView.as_view(), name='exam-result-by-subject'),

    path('share-links/', ShareLinkCreateView.as_view(), name='share-link-create'),
    path('share-links/<uuid:code>', ShareLinkAccessView.as_view(), name='share-link-access'),
    path('share-links/<uuid:code>/results', ShareLinkResultSubmitView.as_view(), name='share-link-results'),

    path('intakes-semester/', IntakeSemesterListView.as_view(), name='intake-list'),
    path('intakes/<str:intake_id>/year-results/<int:year_number>/',
         IntakeYearResultsView.as_view(), name='intake-year-results'),
    path('intakes/<str:intake_id>/semesters/<str:semester_id>/progress-result/',
         SemesterProgressResultView.as_view(), name='semester-progress-result'),
]
    
