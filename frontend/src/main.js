import { createApp } from 'vue';
import './style.css';
import App from './App.vue';
import Chat from './components/Chat.vue'; // Import Chat component

const app = createApp(App);
app.component('chat-component', Chat); // Register Chat component

// Add a delay before mounting
setTimeout(() => {
    const chatAppElement = document.getElementById('chat-app');
    console.log("📌 chat-app element:", chatAppElement); // Check for presence
    if (chatAppElement) {
        app.mount('#chat-app'); // Change mount point back to #chat-app
    } else {
        console.error("❌ chat-app element not found!");
    }
}, 1000); // 1 second delay
