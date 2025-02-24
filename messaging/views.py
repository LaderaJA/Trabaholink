from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q 
from .models import Conversation, Message
from .forms import MessageForm
from django.contrib.auth import get_user_model
from .models import Conversation
from .forms import StartConversationForm

@login_required
def conversation_list(request):
    """Show all conversations where the user is a participant."""
    conversations = Conversation.objects.filter(user1=request.user) | Conversation.objects.filter(user2=request.user)
    return render(request, "messaging/conversation_list.html", {"conversations": conversations})

@login_required
def conversation_detail(request, conversation_id):
    """Display messages between two users in a conversation."""
    conversation = get_object_or_404(Conversation, id=conversation_id)

    # Ensure user is part of the conversation
    if request.user not in [conversation.user1, conversation.user2]:
        return redirect("conversation_list")

    messages = conversation.messages.all().order_by("created_at")
    form = MessageForm()

    return render(request, "messaging/conversation_detail.html", {
        "conversation": conversation,
        "messages": messages,
        "form": form
    })

@login_required
def send_message(request, conversation_id):
    """Handles sending messages in a conversation."""
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if request.user not in [conversation.user1, conversation.user2]:
        return redirect("conversation_list")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()

            # ✅ Redirect back to the conversation page
            return redirect("conversation_detail", conversation_id=conversation.id)

    return redirect("conversation_detail", conversation_id=conversation.id)

# start new convo
User = get_user_model()

@login_required
def start_conversation(request):
    """Start a conversation by searching for a user by username."""
    if request.method == "POST":
        form = StartConversationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            recipient = get_object_or_404(User, username=username)

            # Check if a conversation already exists
            conversation = Conversation.objects.filter(
                (Q(user1=request.user) & Q(user2=recipient)) | 
                (Q(user1=recipient) & Q(user2=request.user))
            ).first()

            if not conversation:
                conversation = Conversation.objects.create(user1=request.user, user2=recipient)

            return redirect("conversation_detail", conversation_id=conversation.id)

    else:
        form = StartConversationForm()

    return render(request, "messaging/start_conversation.html", {"form": form})