const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function switchPanel(name) {
  $$(".nav-btn").forEach((b) => b.classList.remove("active"));
  $$(".panel").forEach((p) => p.classList.remove("active"));
  const btn = $(`.nav-btn[data-panel="${name}"]`);
  if (btn) btn.classList.add("active");
  const panel = $(`#panel-${name}`);
  if (panel) panel.classList.add("active");
  if (name === "universe") loadUniverse();
  if (name === "approvals") loadApprovals();
  if (name === "status") loadStatus();
  if (name === "github") loadGithub();
  if (name === "finance") loadPortfolio();
  if (name === "curiosity") loadCuriosity();
}

$$(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchPanel(btn.dataset.panel));
});

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

// Hızlı komut kartları
$$(".qcard").forEach((card) => {
  card.addEventListener("click", async () => {
    const cmd = card.dataset.cmd;
    addMessage("user", `[Komut] ${card.textContent.trim()}`);
    try {
      if (cmd === "expand") {
        await fetch("/api/expand", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic: null }),
        });
        addMessage("assistant", "Bilgi evreni genişletme arka planda başladı.");
      } else if (cmd === "curiosity") {
        await fetch("/api/curiosity", { method: "POST" });
        addMessage("assistant", "Merak motoru çalışıyor. Birkaç dakika sonra Merak panelini yenile.");
        switchPanel("curiosity");
      } else if (cmd === "night") {
        await fetch("/api/night", { method: "POST" });
        addMessage("assistant", "Gece araştırması başladı (sadece öneri). Podcast için rapor bitince üret.");
        switchPanel("night");
      } else if (cmd === "finance") {
        await fetch("/api/finance/cycle", { method: "POST" });
        addMessage("assistant", "Paper trading döngüsü başladı (sanal para).");
        switchPanel("finance");
      } else if (cmd === "discover") {
        const res = await fetch("/api/discover");
        const data = await res.json();
        addMessage("assistant", data.report || JSON.stringify(data.result));
        $("#discover-out").textContent = data.report || JSON.stringify(data, null, 2);
        switchPanel("discover");
      } else if (cmd === "podcast") {
        $("#night-out").textContent = "Podcast taslağı üretiliyor...";
        const res = await fetch("/api/podcast", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          $("#night-out").textContent = data.script || data.path;
          addMessage("assistant", `Podcast taslağı hazır (${data.chars} karakter). Otomatik yayın yok.\nDosya: ${data.path}`);
        } else {
          addMessage("assistant", data.error || "Podcast üretilemedi. Önce gece araştırması çalıştır.");
        }
        switchPanel("night");
      }
    } catch (e) {
      addMessage("assistant", "Komut hatası: " + e.message);
    }
  });
});

// Ses
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
    chatInput.value = e.results[0][0].transcript;
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

// Curiosity
async function loadCuriosity() {
  try {
    const res = await fetch("/api/curiosity");
    const d = await res.json();
    $("#c-count").textContent = d.explored_count ?? 0;
    $("#c-last").textContent = (d.last_run || "—").toString().slice(0, 16);
    const notes = d.recent || [];
    $("#curiosity-out").textContent = notes.length
      ? notes.map((n) => `• ${n.topic} (+${n.pages || 0} sayfa) @ ${n.at || ""}`).join("\n")
      : "Henüz tur yok. Butona bas.";
  } catch (e) {
    $("#curiosity-out").textContent = "Yüklenemedi";
  }
}

$("#curiosity-btn")?.addEventListener("click", async () => {
  $("#curiosity-btn").disabled = true;
  $("#curiosity-out").textContent = "Merak turu çalışıyor...";
  try {
    await fetch("/api/curiosity", { method: "POST" });
    setTimeout(loadCuriosity, 6000);
  } finally {
    $("#curiosity-btn").disabled = false;
  }
});

// Night + podcast
$("#night-btn")?.addEventListener("click", async () => {
  $("#night-out").textContent = "Gece araştırması arka planda...";
  await fetch("/api/night", { method: "POST" });
  $("#night-out").textContent =
    "Başladı. Bittiğinde memory/night_reports altında rapor oluşur.\nSonra ‘Podcast Metni Üret’ ile taslak çıkar.";
});

$("#podcast-btn")?.addEventListener("click", async () => {
  $("#night-out").textContent = "Podcast taslağı üretiliyor (yerel Ollama)...";
  try {
    const res = await fetch("/api/podcast", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      $("#night-out").textContent =
        `Dosya: ${data.path}\nKaynak: ${data.source_report || "—"}\n\n` + (data.script || "");
    } else {
      $("#night-out").textContent = data.error || "Üretilemedi";
    }
  } catch (e) {
    $("#night-out").textContent = "Hata: " + e.message;
  }
});

// Documents upload
$("#doc-upload-btn")?.addEventListener("click", async () => {
  const fileInput = $("#doc-file");
  if (!fileInput.files || !fileInput.files[0]) {
    $("#doc-out").textContent = "Önce dosya seç.";
    return;
  }
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  $("#doc-out").textContent = "Yükleniyor + analiz...";
  try {
    const res = await fetch("/api/ingest", { method: "POST", body: fd });
    const data = await res.json();
    if (data.success) {
      $("#doc-out").textContent =
        (data.message || "OK") +
        "\n\n" +
        (data.analysis_report || JSON.stringify(data.analysis || {}, null, 2));
    } else {
      $("#doc-out").textContent = data.error || JSON.stringify(data);
    }
  } catch (e) {
    $("#doc-out").textContent = "Hata: " + e.message;
  }
});

// Discover
$("#discover-btn")?.addEventListener("click", async () => {
  $("#discover-out").textContent = "Taranıyor...";
  try {
    const res = await fetch("/api/discover");
    const data = await res.json();
    $("#discover-out").textContent = data.report || JSON.stringify(data, null, 2);
  } catch (e) {
    $("#discover-out").textContent = "Hata: " + e.message;
  }
});

// Legacy
$("#legacy-btn")?.addEventListener("click", async () => {
  const pass = $("#legacy-pass").value;
  if (!pass || pass.length < 8) {
    $("#legacy-out").textContent = "Parola en az 8 karakter.";
    return;
  }
  try {
    const res = await fetch("/api/legacy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passphrase: pass }),
    });
    const data = await res.json();
    $("#legacy-out").textContent = data.message || JSON.stringify(data);
  } catch (e) {
    $("#legacy-out").textContent = "Hata: " + e.message;
  }
});

// Finance
async function loadPortfolio() {
  try {
    const res = await fetch("/api/finance/portfolio");
    const d = await res.json();
    $("#f-equity").textContent = (d.equity ?? 0).toFixed(2);
    $("#f-pnl").textContent = (d.pnl_total_pct ?? 0).toFixed(2) + "%";
    $("#f-cash").textContent = (d.cash ?? 0).toFixed(2);
    $("#f-open").textContent = (d.open_positions || []).length;
    $("#fin-mode").textContent = d.mode || "paper";
    if (d.circuit_breaker) $("#fin-mode").textContent += " | DEVRE KESİCİ";

    const box = $("#fin-positions");
    const positions = d.open_positions || [];
    if (!positions.length) {
      box.innerHTML = '<p class="empty">Açık pozisyon yok</p>';
    } else {
      box.innerHTML = "";
      positions.forEach((p) => {
        const div = document.createElement("div");
        div.className = "approval-card";
        const pnlCls = p.pnl >= 0 ? "var(--success)" : "var(--danger)";
        div.innerHTML = `
          <div class="details">
            <div class="action-name">${p.symbol}</div>
            <div>Entry $${p.entry?.toFixed(4)} → Mark $${p.mark?.toFixed(4)}</div>
            <div style="color:${pnlCls}">PnL $${p.pnl?.toFixed(2)}</div>
          </div>`;
        box.appendChild(div);
      });
    }

    const thoughts = d.recent_thoughts || [];
    $("#fin-thoughts").textContent = thoughts
      .map((t) => `[${(t.ts || "").slice(11, 19)}] ${t.action}: ${t.thought}`)
      .join("\n") || "Henüz düşünce yok.";
  } catch (e) {
    $("#fin-thoughts").textContent = "Yüklenemedi: " + e.message;
  }
}

$("#fin-refresh-btn")?.addEventListener("click", loadPortfolio);
$("#fin-cycle-btn")?.addEventListener("click", async () => {
  $("#fin-cycle-btn").disabled = true;
  try {
    await fetch("/api/finance/cycle", { method: "POST" });
    setTimeout(loadPortfolio, 5000);
  } finally {
    $("#fin-cycle-btn").disabled = false;
  }
});

$("#finance-btn").addEventListener("click", async () => {
  const q = $("#finance-query").value.trim();
  if (!q) return;
  $("#finance-result").textContent = "Analiz...";
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
      box.innerHTML = `<p class="empty">${data.error}</p>`;
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
        <a href="${r.url}" target="_blank" style="color:var(--accent-2)">Aç</a>`;
      box.appendChild(div);
    });
  } catch (e) {
    box.innerHTML = '<p class="empty">Yüklenemedi</p>';
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
        </div>`;
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

async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    $("#status-text").textContent = JSON.stringify(data, null, 2);
    const u = data.universe || {};
    const f = data.finance || {};
    const c = data.curiosity || {};
    $("#quick-status").innerHTML = `
      <strong>SEKA</strong> ${data.version || ""}<br>
      Bilgi: ${u.total_pages || 0}<br>
      Merak: ${c.explored_count || 0}<br>
      Paper $: ${f.equity ?? "—"}<br>
      Onay: ${data.pending_approvals || 0}
    `;
  } catch (e) {
    $("#status-text").textContent = "Durum alınamadı";
  }
}

loadStatus();
setInterval(loadStatus, 30000);
addMessage(
  "assistant",
  "SEKA v4 hazır — Sentinel Egemen Kişisel Ajan.\n" +
    "• Ücretli API yok (Ollama)\n" +
    "• Komut köprüsü + paneller\n" +
    "• Merak · Gece · Podcast taslağı · Belge · Keşif · Yedek\n" +
    "• Paper finans (gerçek para kapalı)\n\n" +
    "Üstteki kartlardan tek tıkla operasyon başlat veya emir yaz."
);
