const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");

function addMessage(text, sender = "bot") {
    const msg = document.createElement("div");
    msg.classList.add("message", sender);
    msg.textContent = text;
    chatWindow.appendChild(msg);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage(message) {
    addMessage(message, "user");

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message })
        });

        const data = await res.json();
        addMessage(data.reply || "Sorry, I didn't understand that.", "bot");
    } catch (err) {
        console.error(err);
        addMessage("There was an error connecting to the server. Please try again.", "bot");
    }
}

chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = userInput.value.trim();
    if (!text) return;
    userInput.value = "";
    sendMessage(text);
});

// Initial welcome message
addMessage(
    "Hello 👋 I'm your AI Receptionist.\n\n" +
    "You can ask about:\n" +
    "• Timings\n" +
    "• Location\n" +
    "• Contact details\n" +
    "• Services\n\n" +
    "To book appointment, type:\n" +
    "book appointment: 2025-12-03 16:00, Your Name, purpose",
    "bot"
);

