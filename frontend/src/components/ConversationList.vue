<!-- src/components/ConversationList.vue -->
<template>
    <div class="conversations-list">
      <a v-for="conv in conversations" 
         :key="conv.id"
         :href="`/chat/${conv.id}/`"
         :class="['conversation-item', { active: conv.id === selectedId }]">
         
        <div class="d-flex align-items-center">
          <UserAvatar :user="getOtherUser(conv)" />
          <div class="conversation-info">
            <h6 class="mb-0">{{ getOtherUser(conv).full_name || getOtherUser(conv).username }}</h6>
            <p class="text-muted mb-0 text-truncate">
              {{ conv.last_message_content || 'No messages yet' }}
            </p>
          </div>
          <span v-if="conv.unread_count > 0" class="badge rounded-pill bg-primary ms-auto">
            {{ conv.unread_count }}
          </span>
        </div>
      </a>
    </div>
  </template>
  
  <script>
  import UserAvatar from './UserAvatar.vue';
  
  export default {
    props: ['conversations', 'currentUserId', 'selectedId'],
    components: { UserAvatar },
    methods: {
      getOtherUser(conv) {
        return conv.user1.id === this.currentUserId ? conv.user2 : conv.user1;
      }
    }
  };
  </script>
  
  <style scoped>
  /* You can add your custom styles here */
  </style>
  