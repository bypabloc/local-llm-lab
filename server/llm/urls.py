from django.urls import path

from llm import views

urlpatterns = [
    path("models", views.list_models, name="list_models"),
    path("shell/confirm", views.shell_confirm, name="shell_confirm"),
    path("bench", views.bench, name="bench"),
    path("chat", views.chat, name="chat"),
]
