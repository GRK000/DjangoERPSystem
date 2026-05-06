from django.urls import path

from . import views

app_name = "aurora_agent"

urlpatterns = [
    path("status/", views.status, name="status"),
    path("suggestions/", views.suggestions, name="suggestions"),
    path("conversations/", views.conversations, name="conversations"),
    path("conversations/<int:conversation_id>/", views.conversation_detail, name="conversation_detail"),
    path("run/", views.run, name="run"),
    path("feedback/", views.feedback, name="feedback"),
]
