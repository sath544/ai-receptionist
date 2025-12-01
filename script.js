const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");

// Display messages inside chat window
function addMessage(text, sender = "bot") {
    const message = document.createElement("div");
    message.classList.add("message", sender);
    message.innerText = text;
    chatWindow.appendChild(message);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Send message to backend (Flask)
chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const msg = userInput.value.trim();
    if (!msg) return;

    addMessage(msg, "user");
    userInput.value = "";

    const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
    });

    const data = await response.json();
    addMessage(data.reply, "bot");
});

// 🔥 Initial welcome message
addMessage("👋 Hello! I'm your AI Receptionist.\n\nAsk me about timings, location, contact, or\nBook appointment like:\n👉 book appointment: 2025-12-03 16:00, Alex, meeting");
