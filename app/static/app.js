const messages = document.getElementById("messages");
const inspect = document.getElementById("inspect");
const form = document.getElementById("askForm");
const input = document.getElementById("question");
const healthPill = document.getElementById("healthPill");
const sessionId = "web-" + Math.random().toString(36).slice(2, 10);

function addMessage(text, role, refused = false) {
  const el = document.createElement("div");
  el.className = `msg ${role}${refused ? " refuse" : ""}`;
  el.textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

async function refreshHealth() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    healthPill.textContent = `ok · ${data.docs_indexed} chunks · ${data.eval_mode}`;
    healthPill.className = "pill ok";
  } catch {
    healthPill.textContent = "offline";
    healthPill.className = "pill bad";
  }
}

async function ask(question) {
  addMessage(question, "user");
  input.value = "";
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) {
    addMessage("Request failed: " + res.status, "bot", true);
    return;
  }
  const data = await res.json();
  addMessage(data.answer, "bot", data.refused);
  inspect.textContent = JSON.stringify(data, null, 2);
  document.getElementById("mGrounded").textContent = String(data.grounded);
  document.getElementById("mRefused").textContent = data.refused ? (data.refusal_reason || "yes") : "no";
  document.getElementById("mSources").textContent = String((data.sources || []).length);
  document.getElementById("mModel").textContent = data.model;
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (q) ask(q);
});

document.getElementById("resetBtn").addEventListener("click", async () => {
  await fetch(`/api/sessions/${sessionId}/reset`, { method: "POST" });
  messages.innerHTML = "";
  inspect.textContent = "Session reset. Ask a new question.";
});

document.querySelectorAll(".chips button").forEach((btn) => {
  btn.addEventListener("click", () => ask(btn.dataset.q));
});

refreshHealth();
setInterval(refreshHealth, 15000);
addMessage("Hi — ask product, warranty or evaluation questions. Safety refusals and source traces show on the right.", "bot");
