import { createApp } from 'vue';
import './style.css';
import App from './App.vue';
import Chat from './components/Chat.vue';

// Create app and register the chat component
const app = createApp(App);
app.component('chat-component', Chat);

// Delay to ensure DOM is ready
setTimeout(() => {
    const chatAppElement = document.getElementById('chat-app');
    console.log("chat-app element:", chatAppElement);

    if (chatAppElement) {
        const conversationId = chatAppElement.dataset.conversationId;
        const currentUserId = chatAppElement.dataset.currentUserId;
        const receiverId = chatAppElement.dataset.receiverId;

        app.mount('#chat-app');

        // Provide props through global config or use <chat-component :conversation-id="..." />
        app.provide('chatConfig', {
            conversationId: parseInt(conversationId),
            currentUserId: parseInt(currentUserId),
            receiverId: parseInt(receiverId)
        });
    } else {
        console.error("chat-app element not found!");
    }
}, 1000);
