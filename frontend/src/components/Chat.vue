<template>
  <div class="chat-container">
    <!-- Chat Header -->
    <!-- <div class="chat-header">
      <div class="user-info">
        <div class="avatar">{{ receiverName.charAt(0).toUpperCase() }}</div>
        <div class="user-details">
          <h3>{{ receiverName }}</h3>
          <span class="status">Online</span>
        </div>
      </div>
      <div class="header-actions">
        <button class="icon-button">
          <i class="bi bi-telephone"></i>
        </button>
        <button class="icon-button">
          <i class="bi bi-info-circle"></i>
        </button>
      </div>
    </div> -->

    <!-- Breadcrumb Navigation -->
    <div class="breadcrumb-nav">
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

    <!-- Messages Area with Fixed Height and Scrolling -->
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
            class="message-wrapper"
            :class="{'outgoing': message.sender_id === currentUserId, 'incoming': message.sender_id !== currentUserId}">
            
            <!-- Avatar (only for incoming) -->
            <div v-if="message.sender_id !== currentUserId" class="message-avatar">
              {{ message.sender_username.charAt(0).toUpperCase() }}
            </div>
            
            <!-- Message Content -->
            <div class="message-content">
              <div class="message-bubble">
                {{ message.content }}
              </div>
              <div class="message-info">
                <span class="message-time">{{ formatTime(message.timestamp || new Date()) }}</span>
                <span v-if="message.sender_id === currentUserId" class="message-status">
                  <i class="bi bi-check2-all"></i>
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Input Area - Always Visible at Bottom -->
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
    height: 80vh; 
    max-height: 600px; 
    width: 100%;
    border: 1px solid #ccc;
    border-radius: 8px;
    overflow: hidden;
}

/* Chat Header */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px;
  background-color: white;
  border-bottom: 1px solid #eaeaea;
  flex-shrink: 0; /* Prevent header from shrinking */
}

.user-info {
  display: flex;
  align-items: center;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #4f46e5;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 12px;
}

.user-details h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.status {
  font-size: 12px;
  color: #10b981;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.icon-button {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 18px;
  cursor: pointer;
  padding: 5px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.icon-button:hover {
  background-color: #f3f4f6;
  color: #4f46e5;
}

/* Breadcrumb Navigation */
.breadcrumb-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background-color: #ffffff;
  border-bottom: 1px solid #eaeaea;
  font-size: 14px;
  flex-shrink: 0; /* Prevent breadcrumb from shrinking */
}

.breadcrumb-path {
  display: flex;
  align-items: center;
}

.breadcrumb-item {
  color: #6b7280;
  text-decoration: none;
}

.breadcrumb-item:hover {
  color: #4f46e5;
  text-decoration: underline;
}

.breadcrumb-item.current {
  color: #1f2937;
  font-weight: 500;
}

.breadcrumb-separator {
  margin: 0 8px;
  color: #9ca3af;
  font-size: 12px;
}

.scroll-bottom-btn {
  display: flex;
  align-items: center;
  background-color: #f3f4f6;
  border: none;
  border-radius: 16px;
  padding: 4px 10px;
  font-size: 12px;
  color: #4f46e5;
  cursor: pointer;
  transition: background-color 0.2s;
}

.scroll-bottom-btn:hover {
  background-color: #e5e7eb;
}

.scroll-bottom-btn i {
  margin-right: 4px;
}

/* Custom Scrollbar */
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 6px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #94a3b8;
}

/* Messages Area - Fixed Height with Scrolling */
.messages {
  flex: 1; 
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 100px; /* Ensure minimum height */
  max-height: calc(100% - 40%); 
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #9ca3af;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 10px;
  color: #d1d5db;
}

.message-group {
  margin-bottom: 20px;
}

.date-separator {
  text-align: center;
  margin: 20px 0;
  position: relative;
}

.date-separator span {
  background-color: #f5f7fb;
  padding: 0 10px;
  font-size: 12px;
  color: #6b7280;
  position: relative;
  z-index: 1;
}

.date-separator:before {
  content: "";
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background-color: #e5e7eb;
  z-index: 0;
}

.message-wrapper {
  display: flex;
  margin-bottom: 12px;
  max-width: 80%;
}

.outgoing {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.incoming {
  align-self: flex-start;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #4f46e5;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  margin: 0 8px;
  flex-shrink: 0;
}

.message-content {
  display: flex;
  flex-direction: column;
}

.outgoing .message-content {
  align-items: flex-end;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 18px;
  max-width: 100%;
  word-wrap: break-word;
  margin-bottom: 4px;
}

.outgoing .message-bubble {
  background-color: #4f46e5;
  color: white;
  border-bottom-right-radius: 4px;
}

.incoming .message-bubble {
  background-color: white;
  color: #1f2937;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.message-info {
  display: flex;
  align-items: center;
  font-size: 11px;
  color: #9ca3af;
  margin: 0 4px;
}

.message-time {
  margin-right: 4px;
}

.message-status {
  color: #4f46e5;
}

/* Input Area - Always Visible at Bottom */
.input-area {
  display: flex;
  align-items: center;
  padding: 15px;
  background-color: white;
  border-top: 1px solid #eaeaea;
  flex-shrink: 0; 
}

.attachment-button {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 20px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.attachment-button:hover {
  background-color: #f3f4f6;
  color: #4f46e5;
}

.input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  background-color: #f3f4f6;
  border-radius: 24px;
  padding: 0 15px;
  margin: 0 10px;
}

.emoji-button {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 18px;
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 12px 5px;
  font-size: 14px;
  color:black;
  outline: none;
  z-index: 99;
}

.send-button {
  background-color: #e5e7eb;
  border: none;
  color: #9ca3af;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.send-button.active {
  background-color: #4f46e5;
  color: white;
}

.send-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

/* Responsive Adjustments */
@media (max-width: 768px) {
  .message-wrapper {
    max-width: 90%;
  }
  
  .breadcrumb-nav {
    padding: 6px 15px;
    font-size: 12px;
  }
  
  .messages {
    max-height: calc(100% - 160px); /* Adjust for smaller header/footer on mobile */
  }
}

@media (max-width: 576px) {
  .chat-header {
    padding: 10px 15px;
  }
  
  .avatar {
    width: 36px;
    height: 36px;
  }
  
  .messages {
    padding: 15px;
  }
  
  .message-bubble {
    padding: 10px 14px;
  }
  
  .input-area {
    padding: 10px;
  }
}

</style>