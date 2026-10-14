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
    if (btn.dataset.panel === "github") loadGithub();
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
    addMessage("assistant", data.reply || "Cevap yok");
  } catch (err) {
    addMessage("assistant", "Hata: " + err.message);
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

// Voice (Web Speech API)
const voiceBtn = $("#voice-btn");
let recognizing = false;
let recognition = null;

if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang = "tr-TR";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    chatInput.value = text;
    sendMessage();
  };
  recognition.onend = () => {
    recognizing = false;
    voiceBtn.classList.remove("recording");
    voiceBtn.textContent = "🎤";
  };
  recognition.onerror = () => {
    recognizing = false;
    voiceBtn.classList.remove("recording");
  };

  voiceBtn.addEventListener("click", () => {
    if (recognizing) {
      recognition.stop();
      return;
    }
    recognizing = true;
    voiceBtn.classList.add("recording");
    voiceBtn.textContent = "🔴";
    recognition.start();
  });
} else {
  voiceBtn.style.display = "none";
}

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
  } catch (e) {}
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
    setTimeout(loadUniverse, 4000);
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

// Finance
$("#finance-btn").addEventListener("click", async () => {
  const q = $("#finance-query").value.trim();
  if (!q) return;
  $("#finance-result").textContent = "Analiz ediliyor...";
  try {
    const res = await fetch("/api/finance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    const data = await res.json();
    $("#finance-result").textContent = data.result || JSON.stringify(data);
  } catch (e) {
    $("#finance-result").textContent = "Hata: " + e.message;
  }
});

// Image
$("#image-btn").addEventListener("click", async () => {
  const prompt = $("#image-prompt").value.trim();
  if (!prompt) return;
  $("#image-result").innerHTML = "<p>Üretiliyor...</p>";
  try {
    const res = await fetch("/api/image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await res.json();
    if (data.success) {
      $("#image-result").innerHTML = `
        <p>Kaynak: ${data.source} — ${data.filename}</p>
        <img src="/api/images/${data.filename}" alt="generated" style="max-width:100%;border-radius:12px;margin-top:12px" />
      `;
    } else {
      $("#image-result").innerHTML = `<p>Hata: ${data.error}</p>`;
    }
  } catch (e) {
    $("#image-result").innerHTML = `<p>Hata: ${e.message}</p>`;
  }
});

// GitHub
async function loadGithub() {
  const box = $("#gh-repos");
  box.innerHTML = "Yükleniyor...";
  try {
    const res = await fetch("/api/github/repos");
    const data = await res.json();
    if (data.error) {
      box.innerHTML = `<p class="empty">${data.error}<br>GITHUB_TOKEN .env'e ekle.</p>`;
      return;
    }
    box.innerHTML = "";
    (data.repos || []).forEach((r) => {
      const div = document.createElement("div");
      div.className = "approval-card";
      div.innerHTML = `
        <div class="details">
          <div class="action-name">${r.private ? "🔒" : "🌐"} ${r.full_name}</div>
          <div>${r.description || ""} · ${r.language || "?"}</div>
        </div>
        <a href="${r.url}" target="_blank" style="color:var(--accent)">Aç</a>
      `;
      box.appendChild(div);
    });
  } catch (e) {
    box.innerHTML = "<p class=\"empty\">Yüklenemedi</p>";
  }
}
$("#gh-refresh").addEventListener("click", loadGithub);

// Approvals
async function loadApprovals() {
  const box = $("#approvals-list");
  try {
    const res = await fetch("/api/approvals");
    const data = await res.json();
    const pending = data.pending || [];
    if (!pending.length) {
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
    box.innerHTML = '<p class="empty">Yüklenemedi</p>';
  }
}

// Status
async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    $("#status-text").textContent = JSON.stringify(data, null, 2);
    const u = data.universe || {};
    $("#quick-status").innerHTML = `
      Bilgi: ${u.total_pages || 0}<br>
      Tur: ${u.total_runs || 0}<br>
      Onay: ${data.pending_approvals || 0}<br>
      GH: ${data.github_enabled ? "✓" : "—"}
    `;
  } catch (e) {
    $("#status-text").textContent = "Durum alınamadı";
  }
}

loadStatus();
setInterval(loadStatus, 30000);
addMessage("assistant", "Merhaba. Ben Sentinel v3.\n• Sesli komut için 🎤\n• Finans, görsel, GitHub panelleri hazır\n• Bilgi evrenim sürekli büyüyor.\nEmirlerini yaz veya söyle.");
