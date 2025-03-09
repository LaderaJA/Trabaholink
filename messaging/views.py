from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
import json
from .models import Conversation, Message
from .forms import MessageForm, StartConversationForm
from django.db.models import OuterRef, Subquery, Q
from django.contrib.auth.mixins import LoginRequiredMixin

User = get_user_model()

class ConversationsListView(LoginRequiredMixin, ListView):
    model = Conversation
    template_name = "messaging/conversation_list.html"
    context_object_name = "conversations"

    def get_queryset(self):
        user = self.request.user
        
        last_message_subquery = Subquery(
            Message.objects.filter(conversation=OuterRef("pk"))
            .order_by("-created_at")
            .values("content")[:1]
        )

        last_message_time_subquery = Subquery(
            Message.objects.filter(conversation=OuterRef("pk"))
            .order_by("-created_at")
            .values("created_at")[:1]
        )

        conversations = Conversation.objects.filter(Q(user1=user) | Q(user2=user)).annotate(
            last_message_content=last_message_subquery,
            last_message_created_at=last_message_time_subquery,  
        )
        
        return conversations

@login_required
def conversation_detail(request, conversation_id):
    """Fetch previous messages in JSON if requested via an API call."""
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if request.user not in [conversation.user1, conversation.user2]:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    messages = conversation.messages.all().order_by("created_at")

    if request.headers.get("Accept") == "application/json":  
        return JsonResponse({
            "messages": [
                {
                    "id": msg.id,
                    "sender_id": msg.sender.id,
                    "sender_username": msg.sender.username,
                    "content": msg.content,
                    "timestamp": msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for msg in messages
            ]
        }, safe=False) 

    # Otherwise, return the HTML page
    receiver_id = conversation.user2.id if request.user == conversation.user1 else conversation.user1.id
    return render(request, "messaging/conversation_detail.html", {
        "conversation": conversation,
        "messages": messages,
        "receiver_id": receiver_id,
    })

@login_required
def fetch_messages(request, conversation_id):
    """Returns JSON data of messages in a conversation."""
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if request.user not in [conversation.user1, conversation.user2]:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    messages = conversation.messages.order_by("created_at")

    response_data = {
        "messages": [
            {
                "id": msg.id,
                "sender_id": msg.sender.id,
                "sender_username": msg.sender.username,
                "content": msg.content,
                "timestamp": msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for msg in messages
        ]
    }

    return JsonResponse(response_data) 

@csrf_exempt  
@login_required
def send_message(request, conversation_id):
    """Handles sending messages in a conversation."""
    print(f"Received message request for conversation {conversation_id}")  # Debugging
    
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if request.user not in [conversation.user1, conversation.user2]:
        print("Unauthorized access attempt")  # Debugging
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Handle raw JSON data from Axios
            print(f"Received data: {data}")  # Debugging

            new_message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=data.get("content", "")
            )
            
            print(f"Message saved: {new_message}")  # Debugging

            return JsonResponse({
                "success": True,
                "id": new_message.id,
                "sender_id": new_message.sender.id,
                "sender_username": new_message.sender.username,
                "content": new_message.content,
                "created_at": new_message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            })
        
        except Exception as e:
            print(f"Error: {e}")  # Debugging
            return JsonResponse({"error": "Invalid request", "details": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=400)

@login_required
def start_conversation(request):
    """Start a conversation by searching for a user by username."""
    if request.method == "POST":
        form = StartConversationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            recipient = get_object_or_404(User, username=username)

            if recipient == request.user:
                form.add_error("username", "You cannot start a conversation with yourself.")
                return render(request, "messaging/start_conversation.html", {"form": form})

            conversation, created = Conversation.objects.get_or_create(
                user1=min(request.user, recipient, key=lambda u: u.id),
                user2=max(request.user, recipient, key=lambda u: u.id)
            )

            return redirect("conversation_detail", conversation_id=conversation.id) 

    return render(request, "messaging/start_conversation.html", {"form": StartConversationForm()})
