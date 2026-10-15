const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// Authenticated local session. Token is kept in sessionStorage, not in URLs.
const nativeFetch = window.fetch.bind(window);
let authToken = sessionStorage.getItem("seka.session") || "";
let authPromptActive = false;
async function requestLogin() {
  if (authToken) return true;
  if (authPromptActive) return false;
  authPromptActive = true;
  try {
    return await new Promise((resolve) => {
      let settled = false;
      const finish = (value) => {
        if (settled) return;
        settled = true;
        document.querySelector("#seka-auth-overlay")?.remove();
        resolve(value);
      };
      const overlay = document.createElement("div");
      overlay.id = "seka-auth-overlay";
      overlay.style.cssText = "position:fixed;inset:0;z-index:99999;display:grid;place-items:center;background:rgba(3,8,18,.88);padding:20px";
      overlay.innerHTML = '<form id="seka-auth-form" style="width:min(420px,100%);box-sizing:border-box;background:#111827;color:#f8fafc;border:1px solid #334155;border-radius:16px;padding:24px;font:14px system-ui;box-shadow:0 20px 70px #0009"><h2 style="margin:0 0 8px">SEKA güvenli oturum</h2><p style="color:#94a3b8;margin:0 0 18px">Kimlik bilgileri bu cihazda doğrulanır.</p><label style="display:block;margin:10px 0 6px">Kullanıcı adı</label><input id="seka-auth-user" autocomplete="username" required value="owner" style="box-sizing:border-box;width:100%;padding:12px;border-radius:8px;border:1px solid #475569;background:#0b1220;color:#fff"><label style="display:block;margin:14px 0 6px">Parola</label><input id="seka-auth-password" type="password" autocomplete="current-password" required style="box-sizing:border-box;width:100%;padding:12px;border-radius:8px;border:1px solid #475569;background:#0b1220;color:#fff"><p id="seka-auth-error" role="alert" style="color:#fca5a5;min-height:18px"></p><div style="display:flex;gap:10px;justify-content:flex-end"><button type="button" id="seka-auth-cancel" style="padding:10px 14px;border-radius:8px">İptal</button><button type="submit" style="padding:10px 16px;border-radius:8px;background:#14b8a6;color:#042f2e;font-weight:700;border:0">Giriş yap</button></div></form>';
      document.body.appendChild(overlay);
      const form = overlay.querySelector("#seka-auth-form");
      overlay.querySelector("#seka-auth-cancel").addEventListener("click", () => finish(false));
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const username = overlay.querySelector("#seka-auth-user").value.trim();
        const password = overlay.querySelector("#seka-auth-password").value;
        const submit = form.querySelector('button[type="submit"]');
        submit.disabled = true;
        try {
          const response = await nativeFetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
          });
          if (!response.ok) {
            overlay.querySelector("#seka-auth-error").textContent = "Giriş başarısız. Bilgileri ve OWNER_PASSWORD ayarını kontrol et.";
            submit.disabled = false;
            return;
          }
          const data = await response.json();
          authToken = data.token || "";
          if (authToken) sessionStorage.setItem("seka.session", authToken);
          finish(Boolean(authToken));
        } catch (error) {
          overlay.querySelector("#seka-auth-error").textContent = "Sunucuya bağlanılamadı.";
          submit.disabled = false;
        }
      });
      overlay.querySelector("#seka-auth-password").focus();
    });
  } finally {
    authPromptActive = false;
  }
}
window.fetch = async (input, init = {}) => {
  const url = typeof input === "string" ? input : input.url;
  if (!url || url.includes("/api/login") || !url.includes("/api/")) return nativeFetch(input, init);
  const sourceHeaders = init.headers || (typeof input !== "string" ? input.headers : undefined);
  const headers = new Headers(sourceHeaders);
  if (authToken) headers.set("Authorization", "Bearer " + authToken);
  let response = await nativeFetch(input, { ...init, headers });
  if (response.status === 401) {
    authToken = "";
    sessionStorage.removeItem("seka.session");
    if (await requestLogin()) {
      const retryHeaders = new Headers(sourceHeaders);
      retryHeaders.set("Authorization", "Bearer " + authToken);
      response = await nativeFetch(input, { ...init, headers: retryHeaders });
    }
  }
  return response;
};

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
  if (name === "pulse") loadPulse();
  if (name === "plan") loadPlans();
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
  let text = chatInput.value.trim();
  if (!text) return;

  // Shortcut: planla: ...
  if (/^planla\s*:/i.test(text)) {
    const goal = text.split(/:/).slice(1).join(":").trim();
    chatInput.value = "";
    addMessage("user", text);
    await createPlan(goal);
    return;
  }

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

async function createPlan(goal) {
  if (!goal) {
    goal = prompt("Plan hedefi?");
    if (!goal) return;
  }
  addMessage("assistant", "Plan üretiliyor: " + goal);
  try {
    const res = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal }),
    });
    const plan = await res.json();
    if (!plan.success && plan.error) {
      addMessage("assistant", plan.error);
      return;
    }
    renderPlan(plan);
    switchPanel("plan");
    addMessage(
      "assistant",
      `Plan hazır (${plan.steps?.length || 0} adım). Plan panelinden güvenli adımları çalıştır.`
    );
  } catch (e) {
    addMessage("assistant", "Plan hatası: " + e.message);
  }
}

function renderPlan(plan) {
  const box = $("#plan-view");
  if (!box) return;
  box.innerHTML = "";
  const head = document.createElement("div");
  head.className = "approval-card";
  head.innerHTML = `
    <div class="details">
      <div class="action-name">${plan.goal || plan.id}</div>
      <div>Durum: ${plan.status} · id ${plan.id}</div>
    </div>
    <button class="primary" id="run-plan-btn" data-id="${plan.id}">Güvenli Adımları Çalıştır</button>`;
  box.appendChild(head);
  (plan.steps || []).forEach((s, i) => {
    const div = document.createElement("div");
    div.className = "approval-card";
    const badge = s.needs_approval ? "🔒 onay" : "⚡ güvenli";
    div.innerHTML = `
      <div class="details">
        <div class="action-name">${i + 1}. ${s.title}</div>
        <div>${s.type} · ${badge} · ${s.status || "pending"}</div>
        <div style="color:var(--text-muted);font-size:0.85rem">${s.detail || ""}</div>
      </div>`;
    box.appendChild(div);
  });
  $("#run-plan-btn")?.addEventListener("click", async () => {
    await fetch(`/api/plan/${plan.id}/run`, { method: "POST" });
    addMessage("assistant", "Plan güvenli adımları arka planda çalışıyor (canlı işler)." );
  });
}

async function loadPlans() {
  try {
    const res = await fetch("/api/plans");
    const data = await res.json();
    const box = $("#plans-list");
    box.innerHTML = "";
    (data.plans || []).forEach((p) => {
      const div = document.createElement("div");
      div.className = "approval-card";
      div.innerHTML = `
        <div class="details">
          <div class="action-name">${p.goal}</div>
          <div>${p.status} · ${(p.steps || []).length} adım</div>
        </div>
        <button data-pid="${p.id}">Aç</button>`;
      div.querySelector("button").addEventListener("click", () => renderPlan(p));
      box.appendChild(div);
    });
  } catch (e) {}
}

$("#plan-create-btn")?.addEventListener("click", async () => {
  const goal = $("#plan-goal").value.trim();
  if (!goal) return;
  await createPlan(goal);
  loadPlans();
});

// Quick cards
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
        addMessage("assistant", "Bilgi genişletme işi kuyruğa alındı.");
      } else if (cmd === "curiosity") {
        await fetch("/api/curiosity", { method: "POST" });
        addMessage("assistant", "Merak turu başladı.");
        switchPanel("curiosity");
      } else if (cmd === "night") {
        await fetch("/api/night", { method: "POST" });
        addMessage("assistant", "Gece araştırması iş kuyruğunda.");
        switchPanel("night");
      } else if (cmd === "finance") {
        await fetch("/api/finance/cycle", { method: "POST" });
        addMessage("assistant", "Paper döngü başladı.");
        switchPanel("finance");
      } else if (cmd === "discover") {
        const res = await fetch("/api/discover");
        const data = await res.json();
        addMessage("assistant", data.report || "");
        $("#discover-out").textContent = data.report || "";
        switchPanel("discover");
      } else if (cmd === "podcast") {
        const res = await fetch("/api/podcast", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          $("#night-out").textContent = data.script || data.path;
          addMessage("assistant", `Podcast taslağı hazır · ${data.path}`);
        } else addMessage("assistant", data.error || "Önce gece turu çalıştır.");
        switchPanel("night");
      } else if (cmd === "pack") {
        await exportPack();
      } else if (cmd === "plan") {
        switchPanel("plan");
        $("#plan-goal")?.focus();
        addMessage("assistant", "Hedefini yazıp Plan Üret’e bas veya: planla: ...");
      }
    } catch (e) {
      addMessage("assistant", "Komut hatası: " + e.message);
    }
  });
});

async function exportPack() {
  const res = await fetch("/api/pack", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "SEKA Araştırma Paketi" }),
  });
  const data = await res.json();
  const out = $("#pack-out");
  if (out) {
    out.style.display = "block";
    out.textContent = JSON.stringify(data.pack || data, null, 2);
  }
  addMessage(
    "assistant",
    data.success
      ? `Bilgi paketi hazır (kişisel veri yok).\nJSON: ${data.json_path}\nMD: ${data.md_path}`
      : "Paket hatası"
  );
  switchPanel("universe");
}

$("#pack-btn")?.addEventListener("click", exportPack);

// Voice
const voiceBtn = $("#voice-btn");
let recognizing = false;
let recognition = null;
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang = "tr-TR";
  recognition.continuous = false;
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
} else if (voiceBtn) voiceBtn.style.display = "none";

// SSE jobs
function renderJobs(jobs) {
  const box = $("#jobs-list");
  const live = $("#job-live");
  if (!jobs || !jobs.length) {
    if (live) live.textContent = "İş yok";
    if (box) box.innerHTML = '<p class="empty">Canlı iş yok</p>';
    return;
  }
  const top = jobs[0];
  if (live) {
    live.textContent = `${top.status} · ${top.title} · ${Math.round((top.progress || 0) * 100)}%`;
  }
  if (!box) return;
  box.innerHTML = "";
  jobs.slice(0, 12).forEach((j) => {
    const div = document.createElement("div");
    div.className = "approval-card";
    div.innerHTML = `
      <div class="details">
        <div class="action-name">${j.title}</div>
        <div>${j.kind} · ${j.status} · ${Math.round((j.progress || 0) * 100)}%</div>
        <div style="color:var(--text-muted);font-size:0.82rem">${j.message || ""}</div>
      </div>`;
    box.appendChild(div);
  });
}

async function connectSSE() {
  const cache = new Map();
  try {
    const response = await fetch("/api/jobs/stream", { headers: { Accept: "text/event-stream" } });
    if (!response.ok || !response.body) {
      setTimeout(connectSSE, 5000);
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";
      for (const event of events) {
        const line = event.split("\n").find((part) => part.startsWith("data: "));
        if (!line) continue;
        try {
          const job = JSON.parse(line.slice(6));
          cache.set(job.id, job);
          const list = Array.from(cache.values()).sort((a, b) =>
            (b.updated_at || "").localeCompare(a.updated_at || "")
          );
          renderJobs(list);
        } catch (e) {}
      }
    }
  } catch (e) {}
  setTimeout(connectSSE, 5000);
}

async function loadPulse() {
  try {
    const [m, s] = await Promise.all([
      fetch("/api/manifesto").then((r) => r.json()),
      fetch("/api/status").then((r) => r.json()),
    ]);
    const pillars = $("#manifesto-pillars");
    pillars.innerHTML = "";
    (m.pillars || []).forEach((p) => {
      const d = document.createElement("div");
      d.className = "pillar";
      d.textContent = p;
      pillars.appendChild(d);
    });
    $("#models-box").textContent = JSON.stringify(s.models || {}, null, 2);
    renderJobs(s.jobs || []);
  } catch (e) {}
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
  await fetch("/api/expand", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic: topic || null }),
  });
  setTimeout(loadUniverse, 4000);
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

async function loadCuriosity() {
  try {
    const res = await fetch("/api/curiosity");
    const d = await res.json();
    $("#c-count").textContent = d.explored_count ?? 0;
    $("#c-last").textContent = (d.last_run || "—").toString().slice(0, 16);
    const notes = d.recent || [];
    $("#curiosity-out").textContent = notes.length
      ? notes.map((n) => `• ${n.topic} (+${n.pages || 0})`).join("\n")
      : "Henüz tur yok.";
  } catch (e) {}
}

$("#curiosity-btn")?.addEventListener("click", async () => {
  await fetch("/api/curiosity", { method: "POST" });
  setTimeout(loadCuriosity, 6000);
});

$("#night-btn")?.addEventListener("click", async () => {
  $("#night-out").textContent = "Gece işi kuyruğa alındı...";
  await fetch("/api/night", { method: "POST" });
});

$("#podcast-btn")?.addEventListener("click", async () => {
  $("#night-out").textContent = "Podcast üretiliyor...";
  const res = await fetch("/api/podcast", { method: "POST" });
  const data = await res.json();
  $("#night-out").textContent = data.success
    ? `Dosya: ${data.path}\n\n${data.script || ""}`
    : data.error || "Hata";
});

$("#doc-upload-btn")?.addEventListener("click", async () => {
  const fileInput = $("#doc-file");
  if (!fileInput.files?.[0]) {
    $("#doc-out").textContent = "Dosya seç";
    return;
  }
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  $("#doc-out").textContent = "Yükleniyor...";
  const res = await fetch("/api/ingest", { method: "POST", body: fd });
  const data = await res.json();
  $("#doc-out").textContent =
    (data.message || data.error || "") +
    "\n\n" +
    (data.analysis_report || "");
});

$("#discover-btn")?.addEventListener("click", async () => {
  const res = await fetch("/api/discover");
  const data = await res.json();
  $("#discover-out").textContent = data.report || "";
});

$("#legacy-btn")?.addEventListener("click", async () => {
  const pass = $("#legacy-pass").value;
  if (!pass || pass.length < 8) {
    $("#legacy-out").textContent = "Min 8 karakter";
    return;
  }
  const res = await fetch("/api/legacy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ passphrase: pass }),
  });
  const data = await res.json();
  $("#legacy-out").textContent = data.message || JSON.stringify(data);
});

async function loadPortfolio() {
  try {
    const res = await fetch("/api/finance/portfolio");
    const d = await res.json();
    $("#f-equity").textContent = (d.equity ?? 0).toFixed(2);
    $("#f-pnl").textContent = (d.pnl_total_pct ?? 0).toFixed(2) + "%";
    $("#f-cash").textContent = (d.cash ?? 0).toFixed(2);
    $("#f-open").textContent = (d.open_positions || []).length;
    $("#fin-mode").textContent = d.mode || "paper";
    const box = $("#fin-positions");
    const positions = d.open_positions || [];
    if (!positions.length) box.innerHTML = '<p class="empty">Yok</p>';
    else {
      box.innerHTML = "";
      positions.forEach((p) => {
        const div = document.createElement("div");
        div.className = "approval-card";
        div.innerHTML = `<div class="details"><div class="action-name">${p.symbol}</div>
          <div>PnL $${p.pnl?.toFixed(2)}</div></div>`;
        box.appendChild(div);
      });
    }
    $("#fin-thoughts").textContent = (d.recent_thoughts || [])
      .map((t) => `${t.action}: ${t.thought}`)
      .join("\n") || "—";
  } catch (e) {}
}

$("#fin-refresh-btn")?.addEventListener("click", loadPortfolio);
$("#fin-cycle-btn")?.addEventListener("click", async () => {
  await fetch("/api/finance/cycle", { method: "POST" });
  setTimeout(loadPortfolio, 5000);
});

$("#finance-btn").addEventListener("click", async () => {
  const q = $("#finance-query").value.trim();
  if (!q) return;
  const res = await fetch("/api/finance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: q }),
  });
  const data = await res.json();
  $("#finance-result").textContent = data.result || "";
});

$("#image-btn").addEventListener("click", async () => {
  const prompt = $("#image-prompt").value.trim();
  if (!prompt) return;
  $("#image-result").innerHTML = "Üretiliyor...";
  const res = await fetch("/api/image", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  const data = await res.json();
  if (data.success) {
    $("#image-result").innerHTML = `<img src="/api/images/${data.filename}" style="max-width:100%;border-radius:12px" />`;
  } else $("#image-result").textContent = data.error || "Hata";
});

async function loadGithub() {
  const box = $("#gh-repos");
  box.innerHTML = "...";
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
    div.innerHTML = `<div class="details"><div class="action-name">${r.full_name}</div>
      <div>${r.description || ""}</div></div>
      <a href="${r.url}" target="_blank" style="color:var(--accent-2)">Aç</a>`;
    box.appendChild(div);
  });
}
$("#gh-refresh").addEventListener("click", loadGithub);

async function loadApprovals() {
  const box = $("#approvals-list");
  const res = await fetch("/api/approvals");
  const data = await res.json();
  const pending = data.pending || [];
  if (!pending.length) {
    box.innerHTML = '<p class="empty">Bekleyen yok</p>';
    return;
  }
  box.innerHTML = "";
  pending.forEach((item) => {
    const card = document.createElement("div");
    card.className = "approval-card";
    card.innerHTML = `
      <div class="details"><div class="action-name">${item.action}</div><div>${item.details}</div></div>
      <div class="approval-actions">
        <button class="approve" data-id="${item.id}">Onayla</button>
        <button class="reject" data-id="${item.id}">Reddet</button>
      </div>`;
    box.appendChild(card);
  });
  box.querySelectorAll(".approve").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await fetch(`/api/approvals/${btn.dataset.id}/approve`, { method: "POST" });
      loadApprovals();
    })
  );
  box.querySelectorAll(".reject").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await fetch(`/api/approvals/${btn.dataset.idx}/reject`, { method: "POST" });
      loadApprovals();
    })
  );
}

async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    $("#status-text").textContent = JSON.stringify(data, null, 2);
    const u = data.universe || {};
    const f = data.finance || {};
    $("#quick-status").innerHTML = `
      <strong>SEKA ${data.version || ""}</strong><br>
      Bilgi: ${u.total_pages || 0}<br>
      Paper: ${f.equity ?? "—"}<br>
      Onay: ${data.pending_approvals || 0}`;
    renderJobs(data.jobs || []);
  } catch (e) {}
}

connectSSE();
loadStatus();
setInterval(loadStatus, 30000);
addMessage(
  "assistant",
  "SEKA v6 online.\n" +
    "• Canlı iş kuyruğu (SSE)\n" +
    "• Plan motoru → planla: hedef\n" +
    "• Bilgi paketi dışa aktar (paylaşılabilir)\n" +
    "• Hızlı/derin model yönlendirme\n" +
    "• Paper finans · merak · gece · podcast taslağı\n\n" +
    "Ücretli API yok. Veri sende kalır."
);
