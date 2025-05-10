<!-- src/components/UserAvatar.vue -->
<template>
    <div class="avatar-container me-2">
      <img v-if="user.profile_image" :src="user.profile_image" :alt="user.username"
           class="rounded-circle" width="40" height="40" />
      <div v-else class="avatar-placeholder rounded-circle bg-primary text-white d-flex align-items-center justify-content-center"
           style="width: 40px; height: 40px;">
        <span>{{ user.username[0].toUpperCase() }}</span>
      </div>
      <span v-if="user.is_online" class="status-indicator bg-success"></span>
    </div>
  </template>
  
  <script>
  export default {
    props: ['user']
  };
  </script>
  
  <style scoped>
  /* Add styles for avatar here */
  .status-indicator {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid white;
  }
  </style>
  