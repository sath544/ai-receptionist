// static/chat.js - simple, robust chat frontend
document.addEventListener("DOMContentLoaded", function() {
  const chatWindow = document.getElementById("chatWindow") || document.querySelector(".chat-window");
  const userInput = document.getElementById("userInput") || document.querySelector("input[name='message']") || document.querySelector("input[type='text']");
  const sendBtn = document.getElementById("sendBtn") || document.querySelector("button[type='submit'], button.send-btn");

  // Helper to print messages
  function addMessage(text, type="bot") {
    if (!chatWindow) return console.warn("chatWindow not found");
    const el = document.createElement("div");
    el.className = "message " + (type === "user" ? "user" : "bot");
    el.innerText = text;
    chatWindow.appendChild(el);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  // If chatWindow empty, add greeting
  if (chatWindow && chatWindow.children.length === 0) {
    addMessage("Hello! How can I help you today?");
  }

  async function sendMessage() {
    const text = (userInput && userInput.value) ? userInput.value.trim() : "";
    if (!text) return false;
    addMessage(text, "user");
    if (userInput) userInput.value = "";

    try {
      console.log("Sending /chat:", text);
      const res = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: text})
      });
      console.log("Fetch status:", res.status);
      const raw = await res.text();
      console.log("Raw response:", raw);
      let data;
      try {
        data = JSON.parse(raw);
      } catch(e) {
        console.error("Invalid JSON from server:", e, raw);
        addMessage("Server returned invalid data. Check logs.");
        return false;
      }
      addMessage(data.reply || "No reply received.");
    } catch(err) {
      console.error("Network error:", err);
      addMessage("Network error. Try again later.");
    }
    return false;
  }

  // Wire up button and Enter key
  if (sendBtn) {
    sendBtn.addEventListener("click", function(e){ e.preventDefault(); sendMessage(); });
  }
  if (userInput) {
    userInput.addEventListener("keydown", function(e){
      if (e.key === "Enter") {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // expose for manual console testing
  window._debugSend = sendMessage;
});
