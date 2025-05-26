<template>
  <div class="chat-container">
    <!-- Breadcrumb Navigation -->
    <div class="chat-header">
      <div class="breadcrumb-path">
        <a href="/messages" class="breadcrumb-item">Messages</a>
        <i class="bi bi-chevron-right breadcrumb-separator"></i>
        <span class="breadcrumb-item current">{{ receiverName }}</span>
      </div>
      <button class="scroll-bottom-btn" @click="scrollToBottom" title="Scroll to bottom">
        <i class="bi bi-arrow-down-circle"></i>
        <span>Latest</span>
      </button>
    </div>

    <!-- Messages Area with Scrolling -->
    <div class="messages-container">
      <div class="messages custom-scrollbar" ref="messagesContainer">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">
            <i class="bi bi-chat-dots"></i>
          </div>
          <p>No messages yet. Start the conversation!</p>
        </div>

        <template v-else>
          <!-- Message Groups by Date -->
          <div v-for="(group, date) in messageGroups" :key="date" class="message-group">
            <!-- Date Separator -->
            <div class="date-separator" :id="`date-${date}`">
              <span>{{ formatDateLabel(date) }}</span>
            </div>

            <!-- Message Bubbles -->
            <div 
              v-for="message in group" 
              :key="message.id" 
              :class="[
                'message-wrapper', 
                message.sender_id === currentUserId ? 'outgoing' : 'incoming'
              ]">
              
              <!-- Avatar (only for incoming) -->
              <div v-if="message.sender_id !== currentUserId" class="message-avatar">
                {{ message.sender_username ? message.sender_username.charAt(0).toUpperCase() : 'U' }}
              </div>
              
              <!-- Message Content -->
              <div class="message-content">
                <div class="message-bubble">
                  {{ message.content }}
                </div>
                <div class="message-info">
                  <span class="message-time">{{ formatTime(message.timestamp || message.created_at || new Date()) }}</span>
                  <span v-if="message.sender_id === currentUserId" class="message-status">
                    <i class="bi bi-check2-all"></i>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Input Area - Fixed at Bottom -->
    <div class="input-area">
      <button class="attachment-button">
        <i class="bi bi-plus"></i>
      </button>
      <div class="input-wrapper">
        <button class="emoji-button">
          <i class="bi bi-emoji-smile"></i>
        </button>
        <input 
          v-model="newMessage" 
          placeholder="Type a message..." 
          @keyup.enter="sendMessage"
        />
        <button class="attachment-button">
          <i class="bi bi-paperclip"></i>
        </button>
      </div>
      <button 
        class="send-button" 
        :class="{'active': newMessage.trim()}" 
        @click="sendMessage"
        :disabled="!newMessage.trim()">
        <i class="bi bi-send-fill"></i>
      </button>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      messages: [],
      messageGroups: {},
      newMessage: "",
      conversationId: window.chatConfig.conversationId,
      currentUserId: window.chatConfig.currentUserId,
      receiverId: window.chatConfig.receiverId,
      apiBaseUrl: window.chatConfig.apiBaseUrl,
      receiverName: "User", // Default value
      isScrolledToBottom: true
    };
  },
  mounted() {
    this.fetchMessages();
    this.getReceiverName();
    
    // Scroll to bottom when component mounts
    this.$nextTick(() => {
      this.scrollToBottom();
      this.setupScrollListener();
    });
  },
  updated() {
    // Maintain scroll position or scroll to bottom if already at bottom
    this.$nextTick(() => {
      if (this.isScrolledToBottom) {
        this.scrollToBottom();
      }
    });
  },
  methods: {
    async fetchMessages() {
      try {
        const response = await axios.get(this.apiBaseUrl, {
          headers: { Accept: "application/json" } 
        });

        console.log("Raw Response Data:", response.data); 

        if (!response.data || !Array.isArray(response.data.messages)) {
          console.error("Unexpected response format:", response.data);
          return;
        }

        this.messages = response.data.messages;
        this.groupMessagesByDate();
      } catch (error) {
        console.error("Error fetching messages:", error);
      }
    },

    async sendMessage() {
      if (!this.newMessage.trim()) return;

      try {
        console.log("Sending message:", this.newMessage);

        const response = await axios.post(
          `/messaging/${this.conversationId}/send/`, 
          {
            sender: this.currentUserId,
            content: this.newMessage
          },
          {
            headers: { "Content-Type": "application/json" } 
          }
        );

        console.log("Message sent:", response.data); 
        this.messages.push(response.data);
        this.groupMessagesByDate();
        this.newMessage = "";
        this.scrollToBottom();
      } catch (error) {
        console.error("Error sending message:", error.response ? error.response.data : error);
      }
    },

    getCSRFToken() {
      const cookieValue = document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1];
      return cookieValue || "";
    },
    
    scrollToBottom() {
      if (this.$refs.messagesContainer) {
        this.$refs.messagesContainer.scrollTop = this.$refs.messagesContainer.scrollHeight;
        this.isScrolledToBottom = true;
      }
    },
    
    setupScrollListener() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.addEventListener('scroll', () => {
          // Check if scrolled to bottom (with a small buffer)
          const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 50;
          this.isScrolledToBottom = isAtBottom;
        });
      }
    },
    
    formatTime(timestamp) {
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },
    
    formatDate(timestamp) {
      const date = new Date(timestamp);
      return date.toISOString().split('T')[0]; // YYYY-MM-DD format
    },
    
    formatDateLabel(dateStr) {
      const date = new Date(dateStr);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      
      if (date.toDateString() === today.toDateString()) {
        return 'Today';
      } else if (date.toDateString() === yesterday.toDateString()) {
        return 'Yesterday';
      } else {
        return date.toLocaleDateString([], { 
          weekday: 'long', 
          month: 'short', 
          day: 'numeric',
          year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
        });
      }
    },
    
    // Group messages by date for better organization
    groupMessagesByDate() {
      const groups = {};
      
      this.messages.forEach(message => {
        const timestamp = message.timestamp || new Date();
        const dateStr = this.formatDate(timestamp);
        
        if (!groups[dateStr]) {
          groups[dateStr] = [];
        }
        
        groups[dateStr].push(message);
      });
      
      this.messageGroups = groups;
    },
    
    // Get the receiver's name - you might want to fetch this from your API
    getReceiverName() {
      // For now, just use the receiverId, but you could fetch the actual name
      this.receiverName = `User ${this.receiverId}`;
    }
  }
};
</script>

<style scoped>
/* Main Container */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* Use viewport height */
  width: 100%;
  background-color: #ffffff;
  position: relative;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  overflow: hidden; /* Prevent scrolling of the entire container */
}

/* Chat Header */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background-color: #ffffff;
  border-bottom: 1px solid #e4e6eb;
  height: 60px; /* Fixed height */
  flex-shrink: 0; /* Prevent shrinking */
  z-index: 10;
}

.breadcrumb-path {
  display: flex;
  align-items: center;
}

.breadcrumb-item {
  color: #050505;
  text-decoration: none;
  font-weight: 600;
  font-size: 16px;
}

.breadcrumb-item:hover {
  color: #1877f2;
}

.breadcrumb-item.current {
  color: #050505;
  font-weight: 600;
}

.breadcrumb-separator {
  margin: 0 8px;
  color: #65676b;
  font-size: 12px;
}

.scroll-bottom-btn {
  display: flex;
  align-items: center;
  background-color: #e4e6eb;
  border: none;
  padding: 6px 12px;
  border-radius: 18px;
  font-size: 13px;
  cursor: pointer;
  color: #050505;
  font-weight: 500;
}

.scroll-bottom-btn:hover {
  background-color: #d8dadf;
}

.scroll-bottom-btn i {
  margin-right: 4px;
}

/* Messages Container */
.messages-container {
  flex: 1; /* Take up all available space */
  position: relative;
  overflow: hidden;
}

/* Messages Area */
.messages {
  height: 100%;
  padding: 16px;
  overflow-y: auto; /* Enable vertical scrolling */
  background-color: #ffffff;
}

.empty-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #65676b;
  padding: 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: #1877f2;
}

.empty-state p {
  font-size: 15px;
  text-align: center;
}

.message-group {
  margin-bottom: 16px;
}

.date-separator {
  text-align: center;
  margin: 16px 0;
  position: relative;
}

.date-separator span {
  background-color: #ffffff;
  padding: 0 12px;
  font-size: 12px;
  color: #65676b;
  position: relative;
  z-index: 1;
}

.date-separator:before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background-color: #e4e6eb;
  z-index: 0;
}

/* Message Wrapper */
.message-wrapper {
  display: flex;
  margin-bottom: 8px;
  clear: both;
  width: 100%;
}

.outgoing {
  flex-direction: row-reverse; /* Reverse direction for outgoing */
  justify-content: flex-end;
}

.incoming {
  flex-direction: row;
  justify-content: flex-start;
}

.message-avatar {
  width: 28px;
  height: 28px;
  background-color: #1877f2;
  color: #ffffff;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 8px;
  font-size: 14px;
  font-weight: 500;
  align-self: flex-end;
  flex-shrink: 0;
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 60%;
}

.outgoing .message-content {
  align-items: flex-end;
}

.incoming .message-content {
  align-items: flex-start;
}

.message-bubble {
  padding: 8px 12px;
  font-size: 14px;
  word-wrap: break-word;
  line-height: 1.4;
  border-radius: 18px;
  max-width: 100%;
}

.outgoing .message-bubble {
  background-color: #0084ff;
  color: white;
  border-radius: 18px 18px 0 18px;
}

.incoming .message-bubble {
  background-color: #f0f2f5;
  color: #050505;
  border-radius: 18px 18px 18px 0;
}

.message-info {
  display: flex;
  font-size: 11px;
  color: #65676b;
  margin-top: 2px;
  padding: 0 4px;
}

.outgoing .message-info {
  justify-content: flex-end;
}

.incoming .message-info {
  justify-content: flex-start;
}

.message-time {
  margin-right: 4px;
}

.message-status {
  color: #0084ff;
}

/* Input Area - Fixed at Bottom */
.input-area {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background-color: #ffffff;
  border-top: 1px solid #e4e6eb;
  height: 64px; /* Fixed height */
  flex-shrink: 0; /* Prevent shrinking */
  z-index: 10;
  box-shadow: 0 -1px 5px rgba(0, 0, 0, 0.05);
}

.attachment-button,
.emoji-button,
.send-button {
  border: none;
  background: none;
  color: #1877f2;
  font-size: 20px;
  cursor: pointer;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
  flex-shrink: 0;
}

.attachment-button:hover,
.emoji-button:hover {
  background-color: #f0f2f5;
}

.input-wrapper {
  display: flex;
  flex-grow: 1;
  align-items: center;
  background-color: #f0f2f5;
  border-radius: 20px;
  margin: 0 8px;
  padding: 0 4px;
  min-height: 40px;
}

.input-wrapper input {
  width: 100%;
  padding: 8px 12px;
  border: none;
  font-size: 14px;
  background-color: transparent;
  outline: none;
  color: #050505;
}

.input-wrapper input::placeholder {
  color: #65676b;
}

.send-button {
  color: #1877f2;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.send-button.active {
  opacity: 1;
}

.send-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Custom scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #bcc0c4;
  border-radius: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #8a8d91;
}

/* Media queries for responsive design */
@media (max-width: 768px) {
  .chat-header {
    height: 50px;
    padding: 8px 12px;
  }
  
  .messages {
    padding: 12px;
  }
  
  .message-content {
    max-width: 75%;
  }
  
  .input-area {
    height: 56px;
    padding: 8px 12px;
  }
  
  .breadcrumb-item {
    font-size: 14px;
  }
  
  .scroll-bottom-btn {
    padding: 4px 8px;
    font-size: 12px;
  }
  
  .scroll-bottom-btn span {
    display: none; /* Hide text on small screens */
  }
}

/* Fix for iOS Safari viewport height issues */
@supports (-webkit-touch-callout: none) {
  .chat-container {
    height: -webkit-fill-available;
  }
}
</style>