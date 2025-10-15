<template>
  <div class="chat-container">
    <!-- Messages Area -->
    <div class="messages-area" ref="messagesContainer">
      <!-- Empty State -->
      <div v-if="messages.length === 0 && !loading" class="empty-chat">
        <div class="empty-chat-icon">
          <i class="bi bi-chat-heart"></i>
        </div>
        <h3>Start the conversation!</h3>
        <p>Send a message to begin chatting</p>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-messages">
        <div class="spinner"></div>
      </div>

      <!-- Messages -->
      <template v-else>
        <div v-for="(group, date) in messageGroups" :key="date" class="message-group">
          <!-- Date Separator -->
          <div class="date-separator">
            <span>{{ formatDateLabel(date) }}</span>
          </div>

          <!-- Message Bubbles -->
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
              {{ getInitial(message.sender_username) }}
            </div>
            
            <!-- Message Content -->
            <div class="message-content">
              <div class="message-bubble">
                {{ message.content }}
              </div>
              <div class="message-info" v-if="!isGroupedMessage(group, index) || index === group.length - 1">
                <span class="message-time">{{ formatTime(message.timestamp || message.created_at) }}</span>
                <span v-if="message.sender_id === currentUserId" class="message-status" :class="{ 'read': message.is_read }">
                  <i class="bi bi-check2-all"></i>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Typing Indicator -->
        <div v-if="isTyping" class="typing-indicator">
          <div class="message-wrapper incoming">
            <div class="message-avatar">
              {{ receiverInitial }}
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
      </template>
    </div>

    <!-- Input Area -->
    <div class="input-area">
      <button class="input-btn" @click="toggleEmojiPicker" title="Emoji">
        <i class="bi bi-emoji-smile"></i>
      </button>
      
      <button class="input-btn" @click="attachFile" title="Attach file">
        <i class="bi bi-paperclip"></i>
      </button>
      
      <div class="input-wrapper">
        <textarea 
          v-model="newMessage" 
          @keydown="handleKeyDown"
          @input="handleInput"
          ref="messageInput"
          placeholder="Type a message..."
          rows="1"
          class="message-input"></textarea>
      </div>
      
      <button 
        class="input-btn send-btn" 
        :class="{ 'active': newMessage.trim() }" 
        @click="sendMessage"
        :disabled="!newMessage.trim()"
        title="Send">
        <i class="bi bi-send-fill"></i>
      </button>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'ChatWindow',
  data() {
    return {
      messages: [],
      messageGroups: {},
      newMessage: '',
      conversationId: window.chatConfig?.conversationId || null,
      currentUserId: window.chatConfig?.currentUserId || null,
      receiverId: window.chatConfig?.receiverId || null,
      apiBaseUrl: window.chatConfig?.apiBaseUrl || '',
      csrfToken: window.chatConfig?.csrfToken || '',
      isScrolledToBottom: true,
      isTyping: false,
      typingTimeout: null,
      loading: true,
      receiverInitial: 'U',
      websocket: null
    };
  },
  mounted() {
    this.fetchMessages();
    this.setupWebSocket();
    
    this.$nextTick(() => {
      this.scrollToBottom();
      this.setupScrollListener();
      this.setupInputAutoResize();
    });
  },
  beforeUnmount() {
    if (this.websocket) {
      this.websocket.close();
    }
  },
  methods: {
    async fetchMessages() {
      try {
        this.loading = true;
        const response = await axios.get(this.apiBaseUrl, {
          headers: { 
            'Accept': 'application/json',
            'X-CSRFToken': this.csrfToken
          }
        });

        if (response.data && Array.isArray(response.data.messages)) {
          this.messages = response.data.messages;
          this.groupMessagesByDate();
        }
      } catch (error) {
        console.error('Error fetching messages:', error);
      } finally {
        this.loading = false;
      }
    },

    async sendMessage() {
      if (!this.newMessage.trim()) return;

      const messageContent = this.newMessage.trim();
      this.newMessage = '';
      this.resetInputHeight();

      try {
        const response = await axios.post(
          `/messaging/${this.conversationId}/send/`,
          {
            sender: this.currentUserId,
            content: messageContent
          },
          {
            headers: { 
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            }
          }
        );

        this.messages.push(response.data);
        this.groupMessagesByDate();
        this.scrollToBottom();
        
        // Send via WebSocket if connected
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
          this.websocket.send(JSON.stringify({
            type: 'message',
            message: response.data
          }));
        }
      } catch (error) {
        console.error('Error sending message:', error);
        // Restore message on error
        this.newMessage = messageContent;
      }
    },

    setupWebSocket() {
      if (!this.conversationId) return;
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;
      
      try {
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
          console.log('WebSocket connected');
        };
        
        this.websocket.onmessage = (event) => {
          const data = JSON.parse(event.data);
          
          if (data.type === 'message' && data.message.sender_id !== this.currentUserId) {
            this.messages.push(data.message);
            this.groupMessagesByDate();
            if (this.isScrolledToBottom) {
              this.scrollToBottom();
            }
          } else if (data.type === 'typing') {
            this.isTyping = data.is_typing && data.user_id !== this.currentUserId;
          }
        };
        
        this.websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
        
        this.websocket.onclose = () => {
          console.log('WebSocket disconnected');
          // Attempt to reconnect after 3 seconds
          setTimeout(() => this.setupWebSocket(), 3000);
        };
      } catch (error) {
        console.error('WebSocket setup error:', error);
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
      if (this.typingTimeout) {
        clearTimeout(this.typingTimeout);
      }
      
      // Send typing status via WebSocket
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({
          type: 'typing',
          is_typing: true,
          user_id: this.currentUserId
        }));
      }
      
      this.typingTimeout = setTimeout(() => {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
          this.websocket.send(JSON.stringify({
            type: 'typing',
            is_typing: false,
            user_id: this.currentUserId
          }));
        }
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
      
      const timeDiff = new Date(currentMessage.timestamp || currentMessage.created_at) - 
                      new Date(previousMessage.timestamp || previousMessage.created_at);
      
      return currentMessage.sender_id === previousMessage.sender_id && 
             timeDiff < 5 * 60 * 1000;
    },

    scrollToBottom() {
      this.$nextTick(() => {
        if (this.$refs.messagesContainer) {
          this.$refs.messagesContainer.scrollTop = this.$refs.messagesContainer.scrollHeight;
          this.isScrolledToBottom = true;
        }
      });
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
        const timestamp = message.timestamp || message.created_at || new Date();
        const dateStr = this.formatDate(timestamp);
        
        if (!groups[dateStr]) {
          groups[dateStr] = [];
        }
        
        groups[dateStr].push(message);
      });
      
      this.messageGroups = groups;
    },

    getInitial(username) {
      return username ? username.charAt(0).toUpperCase() : 'U';
    },

    toggleEmojiPicker() {
      // Implement emoji picker
      console.log('Emoji picker clicked');
    },

    attachFile() {
      // Implement file attachment
      console.log('Attach file clicked');
    }
  }
};
</script>

<style scoped>
/* Component styles are inherited from parent template */
</style>
