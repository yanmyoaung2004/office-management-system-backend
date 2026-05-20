from django.urls import path
from .views import ExamListCreateView, IntakeSemesterListView, ExamDetailView, ExamPaperComponentUploadView, ExamResultView, ShareLinkCreateView, ShareLinkAccessView, ShareLinkResultSubmitView

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

    path('share-links/', ShareLinkCreateView.as_view(), name='share-link-create'),
    path('share-links/<uuid:code>', ShareLinkAccessView.as_view(), name='share-link-access'),
    path('share-links/<uuid:code>/results', ShareLinkResultSubmitView.as_view(), name='share-link-results'),

    path('intakes-semester/', IntakeSemesterListView.as_view(), name='intake-list'),
]
    
