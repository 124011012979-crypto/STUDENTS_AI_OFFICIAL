
let currentChatId = null;

async function sendMessage() {
    const input = document.getElementById("user-input");
    const question = input.value.trim();

    if (!question) return;

    // Get selected programme and year
    const programme = document.getElementById("programme-select").value;
    const year = document.getElementById("year-select").value;

    const welcome = document.getElementById("welcome-screen");

    if (welcome) welcome.style.display = "none";

    addMessage(question, "user");

    input.value = "";
    input.disabled = true;

    const sendButton = document.querySelector(".input-area button");
    if (sendButton) sendButton.disabled = true;

    const loadingId = addMessage("STUDENTS AI is thinking...", "assistant");

    try {
        console.log("Sending question:", question);
        console.log("Programme:", programme);
        console.log("Year:", year);

        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question,
                chat_id: currentChatId,
                programme: programme,
                year: year
            })
        });

        console.log("HTTP Status:", response.status);

        const data = await response.json();

        console.log("Server response:", data);

        removeMessage(loadingId);

        if (!response.ok) {
            throw new Error(data.error || "Server error: " + response.status);
        }

        currentChatId = data.chat_id;

        addMessage(data.answer, "assistant");

    } catch (error) {
        removeMessage(loadingId);

        addMessage(
            "ERROR: " + error.message,
            "assistant"
        );

        console.error("Chat error:", error);

    } finally {
        input.disabled = false;

        if (sendButton) sendButton.disabled = false;

        input.focus();
    }
}


function addMessage(text, sender) {
    const messages = document.getElementById("messages");

    const messageDiv = document.createElement("div");

    messageDiv.className = "message " + sender;

    const content = document.createElement("div");

    content.className = "message-content";
    content.textContent = text;

    messageDiv.appendChild(content);
    messages.appendChild(messageDiv);

    messages.scrollTop = messages.scrollHeight;

    return messageDiv.id = "msg-" + Date.now() + "-" + Math.random();
}


function removeMessage(messageId) {
    const element = document.getElementById(messageId);

    if (element) element.remove();
}


function newChat() {
    currentChatId = null;

    document.getElementById("messages").innerHTML = "";

    const welcome = document.getElementById("welcome-screen");

    if (welcome) welcome.style.display = "block";

    document.getElementById("user-input").focus();
}


function useSuggestion(question) {
    const input = document.getElementById("user-input");

    input.value = question;

    sendMessage();
}


document.addEventListener("DOMContentLoaded", function () {
    const input = document.getElementById("user-input");

    if (input) {
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });
    }

    checkBackend();
});


async function checkBackend() {
    try {
        const response = await fetch("/api/health");
        const data = await response.json();

        console.log("Backend:", data);

    } catch (error) {
        console.error("Backend error:", error);
    }
}
