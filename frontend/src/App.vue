<template>
  <div id="app">
    <chat-component 
      v-if="conversationId && currentUserId && receiverId"
      :conversation-id="conversationId"
      :current-user-id="currentUserId"
      :receiver-id="receiverId"
    />
    <p v-else>Loading chat...</p>
  </div>
</template>

<script>
import ChatComponent from "./components/Chat.vue";

export default {
  components: {
    ChatComponent,
  },
  data() {
    return {
      conversationId: null,
      currentUserId: null,
      receiverId: null,
    };
  },
  mounted() {
    if (window.chatConfig) {
      this.conversationId = window.chatConfig.conversationId || null;
      this.currentUserId = window.chatConfig.currentUserId || null;
      this.receiverId = window.chatConfig.receiverId || null;
      
      console.log(`Fetched Conversation ID: ${this.conversationId}`);
      console.log(`Fetched Current User ID: ${this.currentUserId}`);
      console.log(`Fetched Receiver ID: ${this.receiverId}`);
    } else {
      console.error("window.chatConfig not found. Ensure Django template passes it correctly.");
    }
  },
};
</script>
