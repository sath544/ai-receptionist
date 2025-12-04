// chat.js - interacts with /chat endpoint and renders messages
const chatWindow = document.getElementById('chatWindow');
const userInput = document.getElementById('userInput');
const chatForm = document.getElementById('chatForm');

function addMessage(text, cls='bot') {
  const el = document.createElement('div');
  el.className = 'message ' + (cls === 'user' ? 'user' : 'bot');
  el.innerText = text;
  chatWindow.appendChild(el);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return false;
  addMessage(text, 'user');
  userInput.value = '';
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    addMessage(data.reply || 'Sorry, no reply.');
  } catch (e) {
    addMessage('Network error. Try again later.');
  }
  return false; // prevent form submit
}

// Add a welcome message if empty
if (chatWindow && chatWindow.children.length === 0) {
  addMessage("Hello! How can I help you today?");
}
