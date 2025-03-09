import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()

# Set up logging
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
            if not self.conversation_id:
                logger.error("Missing conversation ID in URL route.")
                await self.close()
                return

            self.room_group_name = f"chat_{self.conversation_id}"
            logger.debug(f"Connecting to room: {self.room_group_name}")

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            logger.debug("WebSocket connection accepted.")

        except Exception as e:
            logger.error(f"Error in connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.debug("WebSocket connection closed.")
        except Exception as e:
            logger.error(f"Error in disconnect: {e}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get("message")
            sender_id = data.get("sender")

            if not message:
                logger.error("Received empty message.")
                return await self.send(text_data=json.dumps({"error": "Message cannot be empty."}))

            if not isinstance(sender_id, int):
                logger.error(f"Invalid sender_id: {sender_id}. Expected an integer.")
                return await self.send(text_data=json.dumps({"error": "Invalid sender ID."}))

            logger.debug(f"Received message from sender_id: {sender_id}")

            # Fetch sender and conversation
            sender = await User.objects.filter(id=sender_id).afirst()
            conversation = await Conversation.objects.filter(id=self.conversation_id).afirst()

            if not sender:
                logger.error(f"Sender with ID {sender_id} does not exist.")
                return await self.send(text_data=json.dumps({"error": "Sender not found."}))

            if not conversation:
                logger.error(f"Conversation with ID {self.conversation_id} does not exist.")
                return await self.send(text_data=json.dumps({"error": "Conversation not found."}))

            # Save message
            new_message = await Message.objects.acreate(conversation=conversation, sender=sender, content=message)

            # Send message to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": new_message.content,
                    "sender": sender.username,
                }
            )
            logger.debug("Message sent to group.")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received.")
            await self.send(text_data=json.dumps({"error": "Invalid JSON format."}))

        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({"error": "An error occurred."}))

    async def chat_message(self, event):
        try:
            await self.send(text_data=json.dumps({
                "message": event["message"],
                "sender": event["sender"],
            }))
        except Exception as e:
            logger.error(f"Error in chat_message: {e}")
