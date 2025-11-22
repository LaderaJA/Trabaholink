from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.db.models import OuterRef, Subquery, Q
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from .models import Conversation, Message
from .forms import MessageForm, StartConversationForm
from django.views.generic import ListView
from admin_dashboard.moderation_utils import check_for_banned_words
from admin_dashboard.models import FlaggedChat

User = get_user_model()

class ConversationsListView(LoginRequiredMixin, ListView):
    model = Conversation
    template_name = "messaging/conversation_list.html"
    context_object_name = "conversations"

    def get_queryset(self):
        user = self.request.user
        
        # Subquery for the last message content and time
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

        return Conversation.objects.filter(Q(user1=user) | Q(user2=user)).annotate(
            last_message_content=last_message_subquery,
            last_message_created_at=last_message_time_subquery,  
        ).order_by('-last_message_created_at', '-updated_at')
    
    def render_to_response(self, context, **response_kwargs):
        """Override to add no-cache headers"""
        response = super().render_to_response(context, **response_kwargs)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


@login_required
def conversation_detail(request, conversation_id):
    """Fetch previous messages in JSON if requested via an API call."""
    conversation = get_object_or_404(Conversation, id=conversation_id)

    # Check if the user is part of the conversation
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

    # Prepare conversation list with last message content and timestamp
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

    conversations = Conversation.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).annotate(
        last_message_content=last_message_subquery,
        last_message_created_at=last_message_time_subquery
    ).order_by('-last_message_created_at', '-updated_at')

    receiver_id = conversation.user2.id if request.user == conversation.user1 else conversation.user1.id

    return render(request, "messaging/conversation_detail.html", {
        "conversation": conversation,
        "chat_messages": messages,
        "receiver_id": receiver_id,
        "conversations": conversations,  
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
            # Check if request has files (FormData) or JSON
            if request.FILES or request.POST:
                # Handle FormData (with file upload) or regular POST
                content = request.POST.get("content", "")
                file = request.FILES.get("file", None)
                print(f"Received FormData/POST - content: {content}, file: {file}")  # Debugging
            else:
                # Handle JSON data (text only)
                data = json.loads(request.body)
                content = data.get("content", "")
                file = None
                print(f"Received JSON - content: {content}")  # Debugging

            # Check for banned words
            is_flagged, flagged_words = check_for_banned_words(content)
            
            # Censor banned words if found
            if is_flagged:
                from admin_dashboard.moderation_utils import sanitize_text
                content = sanitize_text(content)
            
            # Create and save the new message
            new_message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content,
                file=file
            )
            
            # Auto-flag conversation if banned words detected
            if is_flagged:
                # Check if conversation is not already flagged
                if not FlaggedChat.objects.filter(chat_message=conversation, status='pending').exists():
                    FlaggedChat.objects.create(
                        chat_message=conversation,
                        flagged_by=request.user,  # System auto-flag
                        reason=f"Auto-flagged: Message contains banned words: {', '.join(flagged_words)}",
                        status='pending'
                    )
                    print(f"Conversation auto-flagged for banned words: {flagged_words}")
            
            print(f"Message saved: {new_message}")  # Debugging

            # Get the receiver from the conversation
            receiver = conversation.user1 if new_message.sender != conversation.user1 else conversation.user2

            response_data = {
                "id": new_message.id,
                "sender_id": new_message.sender.id,
                "sender_username": new_message.sender.username,
                "content": new_message.content,
                "timestamp": new_message.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            
            # Add file URL if file was uploaded
            if new_message.file:
                response_data["file_url"] = new_message.file.url
                response_data["file_name"] = new_message.file.name.split('/')[-1]
            
            return JsonResponse(response_data)
        
        except Exception as e:
            print(f"Error: {e}")  # Debugging
            import traceback
            traceback.print_exc()
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

            return redirect("messaging:conversation_detail", conversation_id=conversation.id) 

    return render(request, "messaging/start_conversation.html", {"form": StartConversationForm()})


@login_required
def start_conversation_with_user(request, username):
    """Start or get a conversation with a user via direct URL."""
    recipient = get_object_or_404(User, username=username)

    if recipient == request.user:
        return redirect("messaging:conversation_list")

    conversation, created = Conversation.objects.get_or_create(
        user1=min(request.user, recipient, key=lambda u: u.id),
        user2=max(request.user, recipient, key=lambda u: u.id)
    )

    return redirect("messaging:conversation_detail", conversation_id=conversation.id)
