const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// Navigation
$$(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".nav-btn").forEach((b) => b.classList.remove("active"));
    $$(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $(`#panel-${btn.dataset.panel}`).classList.add("active");

    if (btn.dataset.panel === "universe") loadUniverse();
    if (btn.dataset.panel === "approvals") loadApprovals();
    if (btn.dataset.panel === "status") loadStatus();
  });
});

// Chat
const chatBox = $("#chat-messages");
const chatInput = $("#chat-input");
const sendBtn = $("#send-btn");

function addMessage(role, content) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = content;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  addMessage("user", text);
  chatInput.value = "";
  sendBtn.disabled = true;
  sendBtn.textContent = "...";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    addMessage("assistant", data.reply || "Cevap alınamadı.");
  } catch (err) {
    addMessage("assistant", "Bağlantı hatası: " + err.message);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Gönder";
  }
}

sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Universe
async function loadUniverse() {
  try {
    const res = await fetch("/api/universe");
    const data = await res.json();
    $("#u-pages").textContent = data.total_pages ?? 0;
    $("#u-runs").textContent = data.total_runs ?? 0;
    $("#u-seeds").textContent = data.seed_count ?? 0;
    $("#u-visited").textContent = data.visited_count ?? 0;

    const list = $("#topic-list");
    list.innerHTML = "";
    (data.recent_topics || []).forEach((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      list.appendChild(li);
    });
  } catch (e) {
    console.error(e);
  }
}

$("#expand-btn").addEventListener("click", async () => {
  const topic = $("#new-topic").value.trim();
  $("#expand-btn").disabled = true;
  $("#expand-btn").textContent = "Genişliyor...";
  try {
    await fetch("/api/expand", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic || null }),
    });
    setTimeout(loadUniverse, 3000);
  } finally {
    $("#expand-btn").disabled = false;
    $("#expand-btn").textContent = "Şimdi Genişlet";
  }
});

$("#add-seed-btn").addEventListener("click", async () => {
  const topic = $("#new-topic").value.trim();
  if (!topic) return;
  await fetch("/api/seed", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
  $("#new-topic").value = "";
  loadUniverse();
});

// Approvals
async function loadApprovals() {
  const box = $("#approvals-list");
  try {
    const res = await fetch("/api/approvals");
    const data = await res.json();
    const pending = data.pending || [];

    if (pending.length === 0) {
      box.innerHTML = '<p class="empty">Bekleyen onay yok.</p>';
      return;
    }

    box.innerHTML = "";
    pending.forEach((item, idx) => {
      const card = document.createElement("div");
      card.className = "approval-card";
      card.innerHTML = `
        <div class="details">
          <div class="action-name">${item.action}</div>
          <div>${item.details}</div>
        </div>
        <div class="approval-actions">
          <button class="approve" data-idx="${idx}">Onayla</button>
          <button class="reject" data-idx="${idx}">Reddet</button>
        </div>
      `;
      box.appendChild(card);
    });

    box.querySelectorAll(".approve").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await fetch(`/api/approvals/${btn.dataset.idx}/approve`, { method: "POST" });
        loadApprovals();
      });
    });
    box.querySelectorAll(".reject").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await fetch(`/api/approvals/${btn.dataset.idx}/reject`, { method: "POST" });
        loadApprovals();
      });
    });
  } catch (e) {
    box.innerHTML = '<p class="empty">Yüklenemedi.</p>';
  }
}

// Status
async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    $("#status-text").textContent = JSON.stringify(data, null, 2);

    // Quick status in sidebar
    const u = data.universe || {};
    $("#quick-status").innerHTML = `
      Bilgi: ${u.total_pages || 0}<br>
      Tur: ${u.total_runs || 0}<br>
      Onay: ${data.pending_approvals || 0}
    `;
  } catch (e) {
    $("#status-text").textContent = "Durum alınamadı.";
  }
}

// Initial load
loadStatus();
setInterval(loadStatus, 30000);

// Welcome message
addMessage("assistant", "Merhaba. Ben Sentinel. Emirlerini buradan ver. Seni tanıyacağım ve bilgi evrenim sürekli genişleyecek.");
