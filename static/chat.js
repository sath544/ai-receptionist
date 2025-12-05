// static/chat.js
document.addEventListener("DOMContentLoaded", function() {
  const chatWindow = document.getElementById("chatWindow");
  const userInput = document.getElementById("userInput");
  const sendBtn = document.getElementById("sendBtn");

  function addMessage(text, who="bot") {
    const el = document.createElement("div");
    el.className = "message " + who;
    el.style.margin = "8px 0";
    el.style.display = "inline-block";
    el.style.padding = "10px 12px";
    el.style.borderRadius = "12px";
    el.style.maxWidth = "78%";
    if (who === "user") {
      el.style.background = "var(--primary)";
      el.style.color = "white";
      el.style.marginLeft = "auto";
    } else {
      el.style.background = "#f3f4f6";
      el.style.color = "#111827";
    }
    el.innerText = text;
    chatWindow.appendChild(el);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  if (chatWindow.children.length === 0) addMessage("Hello! How can I help you today?");

  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    addMessage(text, "user");
    userInput.value = "";
    const payload = { message: text };
    if (window.CLIENT_SLUG) payload.client = window.CLIENT_SLUG;
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      const textResp = await res.text();
      let data = {};
      try { data = JSON.parse(textResp);} catch(e){ addMessage("Server error: invalid response"); return; }
      addMessage(data.reply || 'No reply');
    } catch(e) {
      addMessage("Network error. Try again later.");
    }
  }

  sendBtn.addEventListener("click", function(e){ e.preventDefault(); sendMessage(); });
  userInput.addEventListener("keydown", function(e){ if (e.key === "Enter") { e.preventDefault(); sendMessage(); } });
});
