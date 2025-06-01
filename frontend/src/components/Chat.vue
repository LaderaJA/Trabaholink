<template>
  <div class="chat-container">
    <!-- Enhanced Chat Header -->
    <div class="chat-header">
      <div class="breadcrumb-path">
        <a href="/messages" class="breadcrumb-item">
          <i class="bi bi-arrow-left me-2"></i>
          Messages
        </a>
        <i class="bi bi-chevron-right breadcrumb-separator"></i>
        <span class="breadcrumb-item current">{{ receiverName }}</span>
      </div>
      <div class="header-actions">
        <button class="action-btn" title="Voice call">
          <i class="bi bi-telephone"></i>
        </button>
        <button class="action-btn" title="Video call">
          <i class="bi bi-camera-video"></i>
        </button>
        <button class="scroll-bottom-btn" @click="scrollToBottom" title="Scroll to bottom">
          <i class="bi bi-arrow-down-circle"></i>
          <span>Latest</span>
        </button>
      </div>
    </div>

    <!-- Enhanced Messages Area -->
    <div class="messages-container">
      <div class="messages custom-scrollbar" ref="messagesContainer">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">
            <i class="bi bi-chat-heart"></i>
          </div>
          <h3>Start the conversation!</h3>
          <p>Send a message to begin chatting with {{ receiverName }}</p>
        </div>

        <template v-else>
          <!-- Message Groups by Date -->
          <div v-for="(group, date) in messageGroups" :key="date" class="message-group">
            <!-- Enhanced Date Separator -->
            <div class="date-separator" :id="`date-${date}`">
              <span>{{ formatDateLabel(date) }}</span>
            </div>

            <!-- Enhanced Message Bubbles -->
            <div 
              v-for="(message, index) in group" 
              :key="message.id" 
              :class="[
                'message-wrapper', 
                message.sender_id === currentUserId ? 'outgoing' : 'incoming',
                { 'grouped': isGroupedMessage(group, index) }
              ]">
              
              <!-- Avatar (only for incoming and first in group) -->
              <div 
                v-if="message.sender_id !== currentUserId && !isGroupedMessage(group, index)" 
                class="message-avatar">
                {{ message.sender_username ? message.sender_username.charAt(0).toUpperCase() : 'U' }}
              </div>
              
              <!-- Message Content -->
              <div class="message-content">
                <div class="message-bubble" :class="{ 'has-reactions': message.reactions }">
                  {{ message.content }}
                  
                  <!-- Message reactions (placeholder) -->
                  <div v-if="message.reactions" class="message-reactions">
                    <span class="reaction">❤️ 2</span>
                    <span class="reaction">👍 1</span>
                  </div>
                </div>
                <div class="message-info" v-if="!isGroupedMessage(group, index) || index === group.length - 1">
                  <span class="message-time">{{ formatTime(message.timestamp || message.created_at || new Date()) }}</span>
                  <span v-if="message.sender_id === currentUserId" class="message-status">
                    <i class="bi bi-check2-all" :class="{ 'read': message.is_read }"></i>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Typing Indicator -->
        <div v-if="isTyping" class="typing-indicator">
          <div class="message-wrapper incoming">
            <div class="message-avatar">
              {{ receiverName.charAt(0).toUpperCase() }}
            </div>
            <div class="message-content">
              <div class="typing-bubble">
                <div class="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Enhanced Input Area -->
    <div class="input-area">
      <button class="attachment-button" title="Add attachment">
        <i class="bi bi-plus-circle"></i>
      </button>
      
      <div class="input-wrapper">
        <button class="emoji-button" title="Add emoji">
          <i class="bi bi-emoji-smile"></i>
        </button>
        
        <div class="input-field">
          <textarea 
            v-model="newMessage" 
            placeholder="Type a message..." 
            @keydown="handleKeyDown"
            @input="handleInput"
            ref="messageInput"
            rows="1"
            class="message-input"></textarea>
        </div>
        
        <button class="attachment-button secondary" title="Attach file">
          <i class="bi bi-paperclip"></i>
        </button>
        
        <button class="voice-button" title="Voice message">
          <i class="bi bi-mic"></i>
        </button>
      </div>
      
      <button 
        class="send-button" 
        :class="{'active': newMessage.trim()}" 
        @click="sendMessage"
        :disabled="!newMessage.trim()"
        title="Send message">
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
      receiverName: "User",
      isScrolledToBottom: true,
      isTyping: false,
      typingTimeout: null
    };
  },
  mounted() {
    this.fetchMessages();
    this.getReceiverName();
    
    this.$nextTick(() => {
      this.scrollToBottom();
      this.setupScrollListener();
      this.setupInputAutoResize();
    });
  },
  updated() {
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
        this.resetInputHeight();
        this.scrollToBottom();
      } catch (error) {
        console.error("Error sending message:", error.response ? error.response.data : error);
      }
    },

    handleKeyDown(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        this.sendMessage();
      }
    },

    handleInput() {
      this.autoResizeInput();
      this.handleTypingIndicator();
    },

    handleTypingIndicator() {
      // Simulate typing indicator
      if (this.typingTimeout) {
        clearTimeout(this.typingTimeout);
      }
      
      // In a real app, you'd send typing status to the server
      this.typingTimeout = setTimeout(() => {
        // Stop typing indicator
      }, 1000);
    },

    autoResizeInput() {
      const input = this.$refs.messageInput;
      if (input) {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
      }
    },

    resetInputHeight() {
      const input = this.$refs.messageInput;
      if (input) {
        input.style.height = 'auto';
      }
    },

    setupInputAutoResize() {
      const input = this.$refs.messageInput;
      if (input) {
        input.addEventListener('input', this.autoResizeInput);
      }
    },

    isGroupedMessage(group, index) {
      if (index === 0) return false;
      
      const currentMessage = group[index];
      const previousMessage = group[index - 1];
      
      // Group if same sender and within 5 minutes
      const timeDiff = new Date(currentMessage.timestamp || currentMessage.created_at) - 
                      new Date(previousMessage.timestamp || previousMessage.created_at);
      
      return currentMessage.sender_id === previousMessage.sender_id && 
             timeDiff < 5 * 60 * 1000; // 5 minutes
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
      return date.toISOString().split('T')[0];
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
    
    getReceiverName() {
      this.receiverName = `User ${this.receiverId}`;
    }
  }
};
</script>

<style scoped>
/* Enhanced CSS Variables */
:root {
  --primary-blue: #2563eb;
  --primary-blue-dark: #1d4ed8;
  --primary-blue-light: #3b82f6;
  --secondary-blue: #1e40af;
  --accent-yellow: #f59e0b;
  --accent-green: #10b981;
  --accent-purple: #8b5cf6;
  --accent-pink: #ec4899;
  --success-green: #10b981;
  --warning-orange: #f97316;
  --danger-red: #ef4444;
  --text-dark: #111827;
  --text-medium: #374151;
  --text-light: #6b7280;
  --text-white: #ffffff;
  --background-white: #ffffff;
  --background-gray: #f9fafb;
  --background-gray-light: #f3f4f6;
  --border-color: #e5e7eb;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* Main Container */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  background: linear-gradient(135deg, var(--background-white) 0%, var(--background-gray) 100%);
  position: relative;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
}

/* Enhanced Chat Header */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
  color: var(--text-white);
  height: 70px;
  flex-shrink: 0;
  z-index: 10;
  box-shadow: var(--shadow-md);
}

.breadcrumb-path {
  display: flex;
  align-items: center;
}

.breadcrumb-item {
  color: var(--text-white);
  text-decoration: none;
  font-weight: 600;
  font-size: 1rem;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
}

.breadcrumb-item:hover {
  color: var(--accent-yellow);
  transform: translateX(-2px);
}

.breadcrumb-item.current {
  color: var(--text-white);
  font-weight: 700;
  font-size: 1.125rem;
}

.breadcrumb-separator {
  margin: 0 0.75rem;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.875rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  color: var(--text-white);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1rem;
}

.action-btn:hover {
  background-color: var(--accent-yellow);
  color: var(--text-dark);
  transform: scale(1.1);
}

.scroll-bottom-btn {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, var(--accent-yellow) 0%, #f59e0b 100%);
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  cursor: pointer;
  color: var(--text-dark);
  font-weight: 600;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.scroll-bottom-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.scroll-bottom-btn i {
  margin-right: 0.5rem;
}

/* Enhanced Messages Container */
.messages-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #fafbfc 0%, var(--background-gray) 100%);
}

.messages {
  height: 100%;
  padding: 1.5rem;
  overflow-y: auto;
  background-image: 
    radial-gradient(circle at 25% 25%, rgba(37, 99, 235, 0.02) 0%, transparent 50%),
    radial-gradient(circle at 75% 75%, rgba(37, 99, 235, 0.02) 0%, transparent 50%);
}

/* Enhanced Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: var(--text-medium);
  padding: 2rem;
  text-align: center;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1.5rem;
  color: var(--primary-blue);
  background: linear-gradient(135deg, var(--primary-blue) 0%, var(--accent-purple) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.empty-state h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-dark);
  margin-bottom: 0.5rem;
}

.empty-state p {
  font-size: 1rem;
  color: var(--text-light);
  max-width: 300px;
}

.message-group {
  margin-bottom: 1.5rem;
}

/* Enhanced Date Separator */
.date-separator {
  text-align: center;
  margin: 2rem 0;
  position: relative;
}

.date-separator span {
  background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
  color: var(--text-white);
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 12px;
  position: relative;
  z-index: 1;
  box-shadow: var(--shadow-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.date-separator:before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, var(--border-color) 50%, transparent 100%);
  z-index: 0;
}

/* Enhanced Message Wrapper */
.message-wrapper {
  display: flex;
  margin-bottom: 0.5rem;
  clear: both;
  width: 100%;
  animation: messageSlideIn 0.3s ease-out;
}

.message-wrapper.grouped {
  margin-bottom: 0.25rem;
}

.outgoing {
  flex-direction: row-reverse;
  justify-content: flex-end;
}

.incoming {
  flex-direction: row;
  justify-content: flex-start;
}

/* Enhanced Message Avatar */
.message-avatar {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--accent-purple) 0%, var(--accent-pink) 100%);
  color: var(--text-white);
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
  align-self: flex-end;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
  border: 2px solid var(--background-white);
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 65%;
  position: relative;
}

.outgoing .message-content {
  align-items: flex-end;
}

.incoming .message-content {
  align-items: flex-start;
}

/* Enhanced Message Bubble */
.message-bubble {
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  word-wrap: break-word;
  line-height: 1.4;
  border-radius: 18px;
  max-width: 100%;
  position: relative;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.message-bubble:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.outgoing .message-bubble {
  background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
  color: var(--text-white);
  border-radius: 18px 18px 4px 18px;
}

.incoming .message-bubble {
  background: linear-gradient(135deg, var(--background-white) 0%, var(--background-gray-light) 100%);
  color: var(--text-dark);
  border-radius: 18px 18px 18px 4px;
  border: 1px solid var(--border-color);
}

.message-bubble.has-reactions {
  margin-bottom: 1.5rem;
}

/* Message Reactions */
.message-reactions {
  position: absolute;
  bottom: -1.25rem;
  right: 0;
  display: flex;
  gap: 0.25rem;
}

.reaction {
  background-color: var(--background-white);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  box-shadow: var(--shadow-sm);
}

.message-info {
  display: flex;
  font-size: 0.75rem;
  color: var(--text-light);
  margin-top: 0.25rem;
  padding: 0 0.25rem;
}

.outgoing .message-info {
  justify-content: flex-end;
}

.incoming .message-info {
  justify-content: flex-start;
}

.message-time {
  margin-right: 0.5rem;
  font-weight: 500;
}

.message-status {
  color: var(--primary-blue);
  transition: color 0.2s ease;
}

.message-status .read {
  color: var(--success-green);
}

/* Enhanced Typing Indicator */
.typing-indicator {
  margin-top: 1rem;
}

.typing-bubble {
  background: linear-gradient(135deg, var(--background-white) 0%, var(--background-gray-light) 100%);
  border: 1px solid var(--border-color);
  border-radius: 18px 18px 18px 4px;
  padding: 1rem;
  box-shadow: var(--shadow-sm);
}

.typing-dots {
  display: flex;
  gap: 0.25rem;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--text-light);
  animation: typingDots 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }

/* Enhanced Input Area */
.input-area {
  display: flex;
  align-items: flex-end;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, var(--background-white) 0%, var(--background-gray-light) 100%);
  border-top: 1px solid var(--border-color);
  min-height: 80px;
  flex-shrink: 0;
  z-index: 10;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}

.attachment-button,
.emoji-button,
.voice-button,
.send-button {
  border: none;
  background: linear-gradient(135deg, var(--background-gray-light) 0%, var(--border-color) 100%);
  color: var(--text-medium);
  font-size: 1.125rem;
  cursor: pointer;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}

.attachment-button:hover,
.emoji-button:hover,
.voice-button:hover {
  background: linear-gradient(135deg, var(--accent-yellow) 0%, #f59e0b 100%);
  color: var(--text-white);
  transform: scale(1.1);
}

.attachment-button.secondary {
  font-size: 1rem;
}

.input-wrapper {
  display: flex;
  flex-grow: 1;
  align-items: flex-end;
  background-color: var(--background-white);
  border: 2px solid var(--border-color);
  border-radius: 24px;
  margin: 0 0.75rem;
  padding: 0.5rem;
  min-height: 48px;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.input-wrapper:focus-within {
  border-color: var(--primary-blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1), var(--shadow-md);
}

.input-field {
  flex-grow: 1;
  margin: 0 0.5rem;
}

.message-input {
  width: 100%;
  padding: 0.5rem 0;
  border: none;
  font-size: 0.875rem;
  background-color: transparent;
  outline: none;
  color: var(--text-dark);
  resize: none;
  font-family: inherit;
  line-height: 1.4;
  max-height: 120px;
}

.message-input::placeholder {
  color: var(--text-light);
}

.send-button {
  background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
  color: var(--text-white);
  opacity: 0.6;
  transition: all 0.2s ease;
}

.send-button.active {
  opacity: 1;
  transform: scale(1.05);
}

.send-button:hover.active {
  background: linear-gradient(135deg, var(--primary-blue-dark) 0%, var(--primary-blue) 100%);
  transform: scale(1.1);
  box-shadow: var(--shadow-md);
}

.send-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Enhanced Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: var(--text-light);
}

/* Animations */
@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes typingDots {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .chat-header {
    height: 60px;
    padding: 0.75rem 1rem;
  }
  
  .messages {
    padding: 1rem;
  }
  
  .message-content {
    max-width: 80%;
  }
  
  .input-area {
    min-height: 70px;
    padding: 0.75rem 1rem;
  }
  
  .breadcrumb-item {
    font-size: 0.875rem;
  }
  
  .scroll-bottom-btn {
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
  }
  
  .scroll-bottom-btn span {
    display: none;
  }

  .header-actions {
    gap: 0.25rem;
  }

  .action-btn {
    width: 36px;
    height: 36px;
    font-size: 0.875rem;
  }

  .attachment-button,
  .emoji-button,
  .voice-button,
  .send-button {
    width: 36px;
    height: 36px;
    font-size: 1rem;
  }
}

/* iOS Safari viewport fix */
@supports (-webkit-touch-callout: none) {
  .chat-container {
    height: -webkit-fill-available;
  }
}
</style>
