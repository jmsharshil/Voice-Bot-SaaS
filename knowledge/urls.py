from django.urls import path
from .views import KnowledgeUploadView

urlpatterns = [
    path("<uuid:agent_id>/upload/", KnowledgeUploadView.as_view()),
]