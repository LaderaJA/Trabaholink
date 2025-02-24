from django.urls import path
from .views import conversation_list, conversation_detail, send_message, start_conversation

urlpatterns = [
    path("", conversation_list, name="conversation_list"),
    path("<int:conversation_id>/", conversation_detail, name="conversation_detail"),
    path("<int:conversation_id>/send/", send_message, name="send_message"),
    path("new/", start_conversation, name="start_conversation"),
]
