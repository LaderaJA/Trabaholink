from django.urls import path
from .views import ConversationsListView
from .views import (
    conversation_detail, 
    send_message, 
    start_conversation,
    fetch_messages  
)


urlpatterns = [
    path("", ConversationsListView.as_view(), name="conversation_list"),
    path("messaging/<int:conversation_id>/", conversation_detail, name="conversation_detail"),
    path("<int:conversation_id>/send/", send_message, name="send_message"),
    path("new/", start_conversation, name="start_conversation"),
    
   
    path("api/conversations/<int:conversation_id>/messages/", fetch_messages, name="fetch_messages"), 
]
