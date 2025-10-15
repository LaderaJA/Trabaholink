<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">
          <i class="bi bi-search"></i>
          Find Users
        </h2>
        <button class="modal-close" @click="close">
          <i class="bi bi-x"></i>
        </button>
      </div>
      
      <div class="modal-body">
        <div class="search-input-wrapper">
          <i class="bi bi-search search-icon"></i>
          <input 
            type="text" 
            class="search-input" 
            placeholder="Search by username or name..."
            v-model="searchQuery"
            @input="handleSearch"
            ref="searchInput">
        </div>
        
        <div class="search-results">
          <!-- Loading State -->
          <div v-if="loading" class="loading-state">
            <div class="spinner"></div>
            <p>Searching...</p>
          </div>
          
          <!-- No Query -->
          <div v-else-if="!searchQuery || searchQuery.length < 2" class="empty-message">
            <i class="bi bi-search" style="font-size: 2rem; color: var(--text-light); margin-bottom: 0.5rem;"></i>
            <p>Type at least 2 characters to search</p>
          </div>
          
          <!-- No Results -->
          <div v-else-if="searchResults.length === 0 && !loading" class="empty-message">
            <i class="bi bi-person-x" style="font-size: 2rem; color: var(--text-light); margin-bottom: 0.5rem;"></i>
            <p>No users found</p>
          </div>
          
          <!-- Results -->
          <div v-else class="results-list">
            <div 
              v-for="user in searchResults" 
              :key="user.id" 
              class="user-result"
              @click="startChat(user)">
              <div class="user-result-avatar">
                {{ getInitial(user.username) }}
              </div>
              <div class="user-result-info">
                <h4 class="user-result-name">{{ user.full_name || user.username }}</h4>
                <p class="user-result-username">@{{ user.username }}</p>
              </div>
              <button class="btn-start-chat" @click.stop="startChat(user)">
                <i class="bi bi-chat"></i>
                Chat
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'UserSearchModal',
  props: {
    isOpen: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      searchQuery: '',
      searchResults: [],
      loading: false,
      searchTimeout: null
    };
  },
  watch: {
    isOpen(newVal) {
      if (newVal) {
        this.$nextTick(() => {
          this.$refs.searchInput?.focus();
        });
      } else {
        this.searchQuery = '';
        this.searchResults = [];
      }
    }
  },
  methods: {
    close() {
      this.$emit('close');
    },
    
    handleSearch() {
      if (this.searchTimeout) {
        clearTimeout(this.searchTimeout);
      }
      
      if (this.searchQuery.length < 2) {
        this.searchResults = [];
        return;
      }
      
      this.searchTimeout = setTimeout(() => {
        this.searchUsers();
      }, 300);
    },
    
    async searchUsers() {
      this.loading = true;
      
      try {
        const response = await axios.get('/api/users/search/', {
          params: { q: this.searchQuery },
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        
        this.searchResults = response.data.users || [];
      } catch (error) {
        console.error('Error searching users:', error);
        this.searchResults = [];
      } finally {
        this.loading = false;
      }
    },
    
    startChat(user) {
      window.location.href = `/messaging/start/${user.username}/`;
    },
    
    getInitial(username) {
      return username ? username.charAt(0).toUpperCase() : 'U';
    }
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: white;
  border-radius: 20px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 2px solid #e2e8f0;
  background: linear-gradient(135deg, #5271FF 0%, #004AAD 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.modal-close {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.modal-close:hover {
  background: rgba(255, 255, 255, 0.2);
}

.modal-body {
  padding: 1.5rem;
  max-height: 60vh;
  overflow-y: auto;
}

.search-input-wrapper {
  position: relative;
  margin-bottom: 1rem;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: #718096;
  font-size: 1rem;
}

.search-input {
  width: 100%;
  padding: 0.875rem 1.125rem 0.875rem 3rem;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: #5271FF;
  box-shadow: 0 0 0 4px rgba(82, 113, 255, 0.1);
}

.search-results {
  min-height: 200px;
}

.loading-state,
.empty-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  color: #718096;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #5271FF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.user-result {
  display: flex;
  align-items: center;
  padding: 1rem;
  border-radius: 12px;
  transition: all 0.2s ease;
  cursor: pointer;
  border: 1px solid transparent;
}

.user-result:hover {
  background: #f7fafc;
  border-color: #AFE4E6;
}

.user-result-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #AFE4E6 0%, #84C7EE 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  font-weight: 700;
  color: #004AAD;
  margin-right: 1rem;
  flex-shrink: 0;
}

.user-result-info {
  flex: 1;
  min-width: 0;
}

.user-result-name {
  font-size: 1rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 0.25rem 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-result-username {
  font-size: 0.875rem;
  color: #4a5568;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-start-chat {
  background: linear-gradient(135deg, #5271FF 0%, #004AAD 100%);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  border: none;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
}

.btn-start-chat:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

@media (max-width: 576px) {
  .modal-content {
    width: 95%;
    max-height: 90vh;
  }
  
  .modal-body {
    padding: 1rem;
  }
}
</style>
