from django.urls import path

from llm import views

urlpatterns = [
    path("models", views.list_models, name="list_models"),
    path("settings", views.list_settings, name="list_settings"),
    path("settings/update", views.update_settings, name="update_settings"),
    path("shell/confirm", views.shell_confirm, name="shell_confirm"),
    path("bench", views.bench, name="bench"),
    path("chat", views.chat, name="chat"),
]
