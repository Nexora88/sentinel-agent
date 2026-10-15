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
      overlay.innerHTML = '<form id="seka-auth-form" style="width:min(420px,100%);box-sizing:border-box;background:#111827;color:#f8fafc;border:1px solid #334155;border-radius:16px;padding:24px;font:14px system-ui;box-shadow:0 20px 70px #0009"><h2 style="margin:0 0 8px">MKAOS güvenli oturum</h2><p style="color:#94a3b8;margin:0 0 18px">Kimlik bilgileri bu cihazda doğrulanır. MKAOS yerel ajan işletim sistemi.</p><label style="display:block;margin:10px 0 6px">Kullanıcı adı</label><input id="seka-auth-user" autocomplete="username" required value="owner" style="box-sizing:border-box;width:100%;padding:12px;border-radius:8px;border:1px solid #475569;background:#0b1220;color:#fff"><label style="display:block;margin:14px 0 6px">Parola</label><input id="seka-auth-password" type="password" autocomplete="current-password" required style="box-sizing:border-box;width:100%;padding:12px;border-radius:8px;border:1px solid #475569;background:#0b1220;color:#fff"><p id="seka-auth-error" role="alert" style="color:#fca5a5;min-height:18px"></p><div style="display:flex;gap:10px;justify-content:flex-end"><button type="button" id="seka-auth-cancel" style="padding:10px 14px;border-radius:8px">İptal</button><button type="submit" style="padding:10px 16px;border-radius:8px;background:#14b8a6;color:#042f2e;font-weight:700;border:0">Giriş yap</button></div></form>';
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
  if (name === "control") loadControlRoom();
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
  const body = document.createElement("div");
  body.className = "message-content";
  body.textContent = content;
  div.appendChild(body);
  if (role === "assistant") {
    const actions = document.createElement("div");
    actions.className = "message-actions";
    const speak = document.createElement("button");
    speak.type = "button";
    speak.className = "message-speak";
    speak.textContent = "🔊 Seslendir";
    speak.addEventListener("click", () => speakText(content));
    actions.appendChild(speak);
    div.appendChild(actions);
  }
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
  box.replaceChildren();
  const head = document.createElement("div");
  head.className = "approval-card";
  const details = document.createElement("div");
  details.className = "details";
  const title = document.createElement("div");
  title.className = "action-name";
  title.textContent = String(plan.goal || plan.id || "Plan");
  const status = document.createElement("div");
  status.textContent = "Durum: " + String(plan.status || "—") + " · id " + String(plan.id || "—");
  details.append(title, status);
  const run = document.createElement("button");
  run.className = "primary";
  run.textContent = "Güvenli Adımları Çalıştır";
  run.addEventListener("click", async () => {
    const response = await fetch("/api/plan/" + encodeURIComponent(String(plan.id)) + "/run", { method: "POST" });
    if (response.ok) addMessage("assistant", "Plan güvenli adımları arka planda çalışıyor.");
    else addMessage("assistant", "Plan başlatılamadı; durum panelini kontrol et.");
  });
  head.append(details, run);
  box.appendChild(head);
  (plan.steps || []).forEach((step, index) => {
    const div = document.createElement("div");
    div.className = "approval-card";
    const stepDetails = document.createElement("div");
    stepDetails.className = "details";
    const stepTitle = document.createElement("div");
    stepTitle.className = "action-name";
    stepTitle.textContent = String(index + 1) + ". " + String(step.title || "Adım");
    const meta = document.createElement("div");
    meta.textContent = String(step.type || "işlem") + " · " +
      (step.needs_approval ? "🔒 onay" : "⚡ güvenli") + " · " + String(step.status || "pending");
    const description = document.createElement("div");
    description.className = "plan-step-description";
    description.textContent = String(step.detail || "");
    stepDetails.append(stepTitle, meta, description);
    div.appendChild(stepDetails);
    box.appendChild(div);
  });
}

async function loadPlans() {
  try {
    const res = await fetch("/api/plans");
    const data = await res.json();
    const box = $("#plans-list");
    if (!box) return;
    box.replaceChildren();
    (data.plans || []).forEach((plan) => {
      const div = document.createElement("div");
      div.className = "approval-card";
      const details = document.createElement("div");
      details.className = "details";
      const title = document.createElement("div");
      title.className = "action-name";
      title.textContent = String(plan.goal || "Adsız plan");
      const meta = document.createElement("div");
      meta.textContent = String(plan.status || "—") + " · " + (plan.steps || []).length + " adım";
      const open = document.createElement("button");
      open.textContent = "Aç";
      open.addEventListener("click", () => renderPlan(plan));
      details.append(title, meta);
      div.append(details, open);
      box.appendChild(div);
    });
  } catch (_) {}
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
    body: JSON.stringify({ title: "MKAOS Araştırma Paketi" }),
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

// Local-only Turkish voice: no browser SpeechRecognition/TTS cloud fallback.
const voiceBtn = $("#voice-btn");
const voiceSelect = $("#voice-select");
const catDubToggle = $("#cat-dub-toggle");
const voicePace = $("#voice-pace");
const voicePaceValue = $("#voice-pace-value");
const voiceStatus = $("#voice-status");
let mediaRecorder = null;
let recordingChunks = [];
let recordingTimer = null;
let activeAudio = null;
let activeAudioUrl = null;

async function loadVoiceStatus() {
  try {
    const response = await fetch("/api/voice/status");
    if (!response.ok) throw new Error("Ses durumu okunamadı");
    const data = await response.json();
    const male = data.voices?.male?.configured;
    const female = data.voices?.female?.configured;
    const stt = data.whisper_available;
    const piper = data.piper_available;
    if (voiceStatus) {
      voiceStatus.textContent = `Piper ${piper ? "hazır" : "eksik"} · Erkek ${male ? "hazır" : "model eksik"} · Kadın ${female ? "hazır" : "model eksik"} · Yerel STT ${stt ? "hazır" : "model eksik"}`;
      voiceStatus.classList.toggle("is-ready", Boolean(piper && male && female && stt));
    }
    if (voiceBtn && (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)) {
      voiceBtn.disabled = true;
      voiceBtn.title = "Bu tarayıcı yerel ses kaydını desteklemiyor.";
    }
  } catch (_) {
    if (voiceStatus) voiceStatus.textContent = "Ses motoru durumu alınamadı";
  }
}

if (voicePace && voicePaceValue) {
  const updatePaceLabel = () => {
    voicePaceValue.textContent = Number(voicePace.value).toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + "×";
  };
  voicePace.addEventListener("input", updatePaceLabel);
  updatePaceLabel();
}

async function speakText(text) {
  if (activeAudio) {
    activeAudio.pause();
    activeAudio = null;
  }
  if (activeAudioUrl) {
    URL.revokeObjectURL(activeAudioUrl);
    activeAudioUrl = null;
  }
  try {
    const response = await fetch("/api/voice/synthesize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: String(text).slice(0, 4000),
        voice: voiceSelect?.value || "male",
        cat_mode: Boolean(catDubToggle?.checked),
        pace: Number(voicePace?.value || 1)
      })
    });
    if (!response.ok) {
      let message = "Yerel ses üretilemedi.";
      try { message = (await response.json()).detail || message; } catch (_) {}
      addMessage("assistant", message);
      return;
    }
    activeAudioUrl = URL.createObjectURL(await response.blob());
    activeAudio = new Audio(activeAudioUrl);
    activeAudio.addEventListener("ended", () => {
      activeAudio = null;
      if (activeAudioUrl) URL.revokeObjectURL(activeAudioUrl);
      activeAudioUrl = null;
    }, { once: true });
    activeAudio.addEventListener("error", () => {
      activeAudio = null;
      if (activeAudioUrl) URL.revokeObjectURL(activeAudioUrl);
      activeAudioUrl = null;
      if (voiceStatus) voiceStatus.textContent = "Ses dosyası oynatılamadı; yeniden dene.";
    }, { once: true });
    await activeAudio.play();
  } catch (error) {
    addMessage("assistant", "Yerel ses hatası: " + error.message);
  }
}

$("#voice-test-btn")?.addEventListener("click", () => {
  const text = catDubToggle?.checked
    ? "Merhaba! Ben MKAOS. Bu yerel kedi dublajı denemesidir."
    : voiceSelect?.value === "female"
      ? "Merhaba, ben MKAOS. Türkçe konuşma kalitemi yerel ses motoruyla test ediyoruz."
      : "Merhaba. Ben MKAOS. Sakin, tok ve anlaşılır Türkçe ses denemesi.";
  speakText(text);
});

$("#voice-stop-btn")?.addEventListener("click", () => {
  if (activeAudio) activeAudio.pause();
  activeAudio = null;
  if (activeAudioUrl) URL.revokeObjectURL(activeAudioUrl);
  activeAudioUrl = null;
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
});

async function transcribeRecording(blob) {
  const form = new FormData();
  const extension = blob.type.includes("ogg") ? "ogg" : blob.type.includes("mp4") ? "m4a" : "webm";
  form.append("file", blob, `seka-speech.${extension}`);
  if (voiceStatus) voiceStatus.textContent = "Ses yerel modelde çözümleniyor…";
  try {
    const response = await fetch("/api/voice/transcribe", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Yerel konuşma tanıma başarısız.");
    chatInput.value = data.text || "";
    chatInput.focus();
    if (voiceStatus) voiceStatus.textContent = "Metin hazır · gönder tuşuyla onayla";
  } catch (error) {
    addMessage("assistant", error.message);
    loadVoiceStatus();
  }
}

voiceBtn?.addEventListener("click", async () => {
  if (!window.MediaRecorder || !navigator.mediaDevices?.getUserMedia) {
    addMessage("assistant", "Bu tarayıcı yerel ses kaydını desteklemiyor.");
    return;
  }
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "";
    mediaRecorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    recordingChunks = [];
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data?.size) recordingChunks.push(event.data);
    });
    mediaRecorder.addEventListener("stop", async () => {
      clearTimeout(recordingTimer);
      stream.getTracks().forEach((track) => track.stop());
      voiceBtn.classList.remove("recording");
      voiceBtn.textContent = "🎤";
      const blob = new Blob(recordingChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      recordingChunks = [];
      if (blob.size) await transcribeRecording(blob);
    }, { once: true });
    mediaRecorder.start();
    voiceBtn.classList.add("recording");
    voiceBtn.textContent = "⏹";
    if (voiceStatus) voiceStatus.textContent = "Kayıt açık · en fazla 45 saniye";
    recordingTimer = setTimeout(() => {
      if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
    }, 45000);
  } catch (error) {
    addMessage("assistant", "Mikrofon izni alınamadı: " + error.message);
  }
});

loadVoiceStatus();

// SSE jobs
function renderJobs(jobs) {
  const box = $("#jobs-list");
  const live = $("#job-live");
  if (!jobs || !jobs.length) {
    if (live) live.textContent = "İş yok";
    if (box) box.textContent = "Canlı iş yok";
    return;
  }
  const top = jobs[0];
  if (live) live.textContent = String(top.status || "—") + " · " + String(top.title || "İş") + " · " + Math.round((top.progress || 0) * 100) + "%";
  if (!box) return;
  box.replaceChildren();
  jobs.slice(0, 12).forEach((job) => {
    const div = document.createElement("div");
    div.className = "approval-card";
    const details = document.createElement("div");
    details.className = "details";
    const title = document.createElement("div");
    title.className = "action-name";
    title.textContent = String(job.title || "İş");
    const meta = document.createElement("div");
    meta.textContent = String(job.kind || "iş") + " · " + String(job.status || "—") + " · " + Math.round((job.progress || 0) * 100) + "%";
    const message = document.createElement("div");
    message.className = "plan-step-description";
    message.textContent = String(job.message || "");
    details.append(title, meta, message);
    div.appendChild(details);
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
    if (!positions.length) {
      box.textContent = "Açık pozisyon yok";
    } else {
      box.replaceChildren();
      positions.forEach((position) => {
        const div = document.createElement("div");
        div.className = "approval-card";
        const details = document.createElement("div");
        details.className = "details";
        const symbol = document.createElement("div");
        symbol.className = "action-name";
        symbol.textContent = String(position.symbol || "Varlık");
        const pnl = document.createElement("div");
        pnl.textContent = "PnL $" + (Number.isFinite(position.pnl) ? position.pnl.toFixed(2) : "—");
        details.append(symbol, pnl);
        div.appendChild(details);
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

let lastMediaFilename = "";
function renderMediaResult(data) {
  const box = $("#image-result");
  if (!data.success || !/^[A-Za-z0-9._-]+$/.test(String(data.filename || ""))) {
    box.textContent = data.detail || data.error || "İşlem tamamlanamadı.";
    return;
  }
  lastMediaFilename = data.filename;
  const url = "/api/images/" + encodeURIComponent(data.filename);
  if (data.filename.endsWith(".mp4")) {
    const video = document.createElement("video");
    video.src = url; video.controls = true; video.preload = "metadata";
    video.style.maxWidth = "100%"; video.style.borderRadius = "12px";
    box.replaceChildren(video);
  } else {
    const image = document.createElement("img");
    image.src = url; image.alt = "MKAOS tarafından yerel olarak işlenen görsel";
    image.loading = "lazy"; image.style.maxWidth = "100%"; image.style.borderRadius = "12px";
    const save = document.createElement("a");
    save.href = url; save.download = data.filename; save.textContent = "Görseli indir";
    save.className = "media-download";
    box.replaceChildren(image, save);
  }
}
$("#image-btn").addEventListener("click", async () => {
  const mode = $("#media-mode").value;
  const prompt = $("#image-prompt").value.trim();
  const file = $("#media-file").files?.[0];
  const box = $("#image-result");
  box.textContent = "Yerel işlem hazırlanıyor…";
  try {
    let res;
    if (mode === "generate") {
      if (!prompt) { box.textContent = "Önce görsel tarifini yaz."; return; }
      res = await fetch("/api/image", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt }) });
    } else {
      if (!file) { box.textContent = "Düzenlemek için bir görsel seç."; return; }
      const form = new FormData(); form.append("file", file);
      if (mode === "edit") {
        if (!prompt) { box.textContent = "Düzenleme talimatını yaz."; return; }
        form.append("prompt", prompt);
        res = await fetch("/api/media/edit", { method: "POST", body: form });
      } else {
        form.append("color", $("#background-color").value);
        res = await fetch("/api/media/background", { method: "POST", body: form });
      }
    }
    const data = await res.json();
    renderMediaResult(res.ok ? data : { error: data.detail || "Yerel medya işlemi başarısız." });
  } catch (_) { box.textContent = "MKAOS medya servisine ulaşılamadı."; }
});
$("#video-btn")?.addEventListener("click", async () => {
  const box = $("#image-result");
  if (!lastMediaFilename || !lastMediaFilename.endsWith(".png")) {
    box.textContent = "Önce bir PNG görsel üret veya düzenle.";
    return;
  }
  box.textContent = "Yerel video hazırlanıyor…";
  try {
    const res = await fetch("/api/media/video", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename: lastMediaFilename, duration: 4 }) });
    const data = await res.json();
    renderMediaResult(res.ok ? data : { error: data.detail || "Video oluşturulamadı." });
  } catch (_) { box.textContent = "Yerel video servisine ulaşılamadı."; }
});
async function loadGithub() {
  const box = $("#gh-repos");
  if (!box) return;
  box.textContent = "Yükleniyor…";
  try {
    const res = await fetch("/api/github/repos");
    const data = await res.json();
    box.replaceChildren();
    if (data.error) {
      const message = document.createElement("p");
      message.className = "empty";
      message.textContent = String(data.error);
      box.appendChild(message);
      return;
    }
    (data.repos || []).forEach((repo) => {
      const div = document.createElement("div");
      div.className = "approval-card";
      const details = document.createElement("div");
      details.className = "details";
      const title = document.createElement("div");
      title.className = "action-name";
      title.textContent = String(repo.full_name || repo.name || "Depo");
      const description = document.createElement("div");
      description.textContent = String(repo.description || "");
      details.append(title, description);
      div.appendChild(details);
      try {
        const url = new URL(repo.url);
        if (url.protocol === "https:" && url.hostname === "github.com") {
          const link = document.createElement("a");
          link.href = url.href;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = "Aç";
          link.style.color = "var(--accent-2)";
          div.appendChild(link);
        }
      } catch (_) {}
      box.appendChild(div);
    });
  } catch (_) {
    box.textContent = "GitHub depoları alınamadı.";
  }
}
$("#gh-refresh").addEventListener("click", loadGithub);

async function loadApprovals() {
  const box = $("#approvals-list");
  if (!box) return;
  try {
    const res = await fetch("/api/approvals");
    const data = await res.json();
    const actionable = data.pending || [];
    const historyBox = $("#approval-history");
    if (historyBox) {
      historyBox.innerHTML = "";
      const history = data.history || [];
      if (!history.length) {
        historyBox.innerHTML = '<p class="empty">Henüz tamamlanmış işlem yok</p>';
      } else {
        history.slice().reverse().forEach((entry) => {
          const row = document.createElement("div");
          row.className = "approval-card audit-row";
          const summary = document.createElement("div");
          summary.className = "details";
          const title = document.createElement("div");
          title.className = "action-name";
          title.textContent = entry.action || "İşlem";
          const description = document.createElement("div");
          description.textContent = entry.details || "";
          const result = document.createElement("div");
          result.className = "approval-state";
          result.textContent = "Durum: " + (entry.status || "—") + (entry.execution_result ? " · " + entry.execution_result : "");
          summary.append(title, description, result);
          row.appendChild(summary);
          historyBox.appendChild(row);
        });
      }
    }
    if (!actionable.length) {
      box.innerHTML = '<p class="empty">Bekleyen veya yürütülmeye hazır onay yok</p>';
      return;
    }
    box.innerHTML = "";
    actionable.forEach((item) => {
      const card = document.createElement("div");
      card.className = "approval-card";
      const details = document.createElement("div");
      details.className = "details";
      const name = document.createElement("div");
      name.className = "action-name";
      name.textContent = item.action || "İşlem";
      const description = document.createElement("div");
      description.className = "approval-description";
      const context = item.context || {};
      let preview = item.details || "";
      if (item.action === "open_github_issue") {
        preview += "\nDepo: " + (context.owner || "?") + "/" + (context.repo || "?") +
          "\nBaşlık: " + (context.title || "") + "\nGövde:\n" + (context.body || "");
      } else if (item.action === "create_pull_request") {
        preview += "\nDepo: " + (context.owner || "?") + "/" + (context.repo || "?") +
          "\nDal: " + (context.head || "?") + " → " + (context.base || "?") +
          "\nBaşlık: " + (context.title || "") + "\nAçıklama:\n" + (context.body || "");
      } else if (["modify_files", "push_to_remote"].includes(item.action)) {
        preview += "\nDepo: " + (context.owner || "?") + "/" + (context.repo || "?") +
          "\nDosya: " + (context.path || "?") + "\nDal: " + (context.branch || "main") +
          "\nCommit: " + (context.message || "") + "\nSHA: " + (context.sha || "Yeni dosya");
      } else if (context.preview) {
        preview += "\nÖnizleme:\n" + context.preview;
      }
      description.textContent = preview;
      if (["modify_files", "push_to_remote"].includes(item.action) && typeof context.content === "string") {
        const contentDetails = document.createElement("details");
        contentDetails.className = "approval-content-details";
        const summary = document.createElement("summary");
        summary.textContent = "Dosya içeriğini incele (" + context.content.length + " karakter)";
        const code = document.createElement("pre");
        code.className = "approval-preview";
        code.textContent = context.content;
        contentDetails.append(summary, code);
        description.appendChild(contentDetails);
      }
      const state = document.createElement("div");
      state.className = "approval-state";
      state.textContent = "Durum: " + (item.status || "pending");
      details.append(name, description, state);
      const actions = document.createElement("div");
      actions.className = "approval-actions";
      if (item.status === "pending") {
        const approve = document.createElement("button");
        approve.className = "approve";
        approve.textContent = "Onayla";
        approve.addEventListener("click", async () => {
          const result = await fetch(`/api/approvals/${encodeURIComponent(item.id)}/approve`, { method: "POST" });
          if (!result.ok) addMessage("assistant", "Onay kaydedilemedi.");
          await loadApprovals();
        });
        const reject = document.createElement("button");
        reject.className = "reject";
        reject.textContent = "Reddet";
        reject.addEventListener("click", async () => {
          const result = await fetch(`/api/approvals/${encodeURIComponent(item.id)}/reject`, { method: "POST" });
          if (!result.ok) addMessage("assistant", "Reddetme işlemi kaydedilemedi.");
          await loadApprovals();
        });
        actions.append(approve, reject);
      } else if (item.status === "approved" && ["open_github_issue", "create_pull_request", "modify_files", "push_to_remote"].includes(item.action)) {
        const execute = document.createElement("button");
        execute.className = "primary";
        execute.textContent = item.action === "modify_files" ? "İkinci onayı hazırla" : "Onaylı GitHub işlemini yürüt";
        execute.addEventListener("click", async () => {
          const confirmation = item.action === "modify_files"
            ? "Bu adım yalnızca ikinci push onayını oluşturur; dosya henüz GitHub'a gönderilmez. Devam edilsin mi?"
            : "Bu GitHub işlemi dış sistemde değişiklik yapacak. Ayrıntıları ve hedef depoyu kontrol ettin mi?";
          if (!confirm(confirmation)) return;
          execute.disabled = true;
          const result = await fetch(`/api/approvals/${encodeURIComponent(item.id)}/execute`, { method: "POST" });
          const payload = await result.json();
          addMessage("assistant", payload.result || payload.detail || "İşlem sonucu alınamadı.");
          await loadApprovals();
        });
        actions.appendChild(execute);
      } else if (item.status === "approved") {
        const note = document.createElement("span");
        note.className = "approval-note";
        note.textContent = "Onay kaydedildi; bu işlem türü için güvenli yürütücü henüz yok.";
        actions.appendChild(note);
      }
      card.append(details, actions);
      box.appendChild(card);
    });
  } catch (error) {
    box.innerHTML = '<p class="empty">Onay listesi alınamadı.</p>';
  }
}
async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    $("#status-text").textContent = JSON.stringify(data, null, 2);
    const u = data.universe || {};
    const f = data.finance || {};
    const ollama = data.ollama || {};
    const rag = data.rag || {};
    const night = data.night_scheduler || {};
    const sovereign = data.sovereignty || {};
    const miniSovereignty = $("#sovereignty-mini-label");
    if (miniSovereignty) miniSovereignty.textContent = String(sovereign.label || "MKAOS · EGEMENLİK DOĞRULANMADI");
    const nightState = night.last_run || {};
    const nightBox = $("#night-scheduler-status");
    if (nightBox) {
      const lastLabel = nightState.status ? "Son çalışma: " + nightState.status + (nightState.finished_at ? " · " + nightState.finished_at : "") : "Henüz çalışma kaydı yok.";
      if (!night.enabled) {
        nightBox.textContent = "Otomatik denetim kapalı. .env içinde SEKA_NIGHT_AUTORUN=true ile açabilirsin.\n" + lastLabel;
      } else {
        nightBox.textContent = (night.running ? "Zamanlayıcı etkin" : "Zamanlayıcı başlatılamadı") + " · her gece " + (night.scheduled_time || "03:00") + " (" + (night.timezone || "Europe/Istanbul") + ")\n" + lastLabel + "\n" + (night.next_run_at ? "Sonraki çalışma: " + night.next_run_at : "Sonraki çalışma zamanı henüz belirlenmedi.") + "\nKod otomatik değiştirilmez; rapor ve öneriler hazırlanır.";
      }
    }
    const ollamaLabel = ollama.status === "online" ? "hazır" : ollama.status === "model_missing" ? "model eksik" : "bağlantı yok";
    const diskMb = Number(rag.disk_bytes || 0) / (1024 * 1024);
    $("#quick-status").innerHTML = `
      <strong>MKAOS ${data.version || ""}</strong><br>
      Ollama: ${ollamaLabel}<br>
      Bilgi: ${u.total_pages || 0}<br>
      RAG: ${rag.documents ?? 0}/${rag.max_documents ?? "—"} parça · ${diskMb.toFixed(1)} MB<br>
      Paper: ${f.equity ?? "—"}<br>
      Onay: ${data.pending_approvals || 0}<br>
      Ağ: ${data.privacy?.web_research ? "web açık" : "web kapalı"} · ${data.privacy?.external_finance_data ? "finans açık" : "finans kapalı"} · ${data.privacy?.site_scanning ? "tarama açık" : "tarama kapalı"}<br>
      Bildirim: ${data.privacy?.external_notifications ? "açık" : "kapalı"}`;
    $("#quick-status").classList.toggle("is-degraded", ollama.status !== "online" || data.status === "degraded");
    renderJobs(data.jobs || []);
  } catch (e) {}
}

connectSSE();
loadStatus();
setInterval(loadStatus, 30000);
addMessage(
  "assistant",
  "MKAOS v6.5 online · yerel ajan işletim sistemi.\n" +
    "• Canlı iş kuyruğu (SSE)\n" +
    "• Plan motoru → planla: hedef\n" +
    "• Bilgi paketi dışa aktar (paylaşılabilir)\n" +
    "• Hızlı/derin model yönlendirme\n" +
    "• Paper finans · merak · gece · podcast taslağı\n\n" +
    "Ağ özellikleri varsayılan kapalıdır; çevrimdışı profil internet çıkışını sınırlar."
);


async function loadControlRoom() {
  const statusBox = $("#sovereignty-status-card");
  const capsBox = $("#media-capabilities");
  if (!statusBox || !capsBox) return;
  try {
    const [sr, mr, jr] = await Promise.all([
      fetch("/api/sovereignty"), fetch("/api/media/capabilities"), fetch("/api/media/jobs")
    ]);
    const sovereignty = await sr.json(), media = await mr.json(), jobs = await jr.json();
    statusBox.replaceChildren();
    const title = document.createElement("h3");
    title.textContent = String(sovereignty.label || "Egemenlik doğrulanamadı");
    const state = document.createElement("p");
    state.textContent = "Durum: " + String(sovereignty.state || "unknown") +
      " · Tam egemen: " + (sovereignty.fully_sovereign ? "evet" : "doğrulanmadı") +
      " · AIR-GAPPED: " + (sovereignty.air_gapped_verified ? "evet" : "doğrulanmadı");
    const limits = document.createElement("ul");
    (sovereignty.limitations || []).forEach((line) => { const li=document.createElement("li"); li.textContent=String(line); limits.appendChild(li); });
    statusBox.append(title, state, limits);
    capsBox.textContent = JSON.stringify({bridge:media.bridge,engine:media.engine,video_mode:media.video_mode}, null, 2);
    const list=$("#media-jobs-list"); list.replaceChildren();
    if (!(jobs.jobs || []).length) { const empty=document.createElement("p"); empty.className="empty"; empty.textContent="Henüz medya görevi yok."; list.appendChild(empty); }
    (jobs.jobs || []).forEach((job) => {
      const card=document.createElement("div"); card.className="approval-card";
      const detail=document.createElement("div"); detail.className="details";
      const name=document.createElement("div"); name.className="action-name"; name.textContent=job.operation+" · "+job.id;
      const desc=document.createElement("div"); desc.textContent=job.status+" — "+(job.reason||"");
      detail.append(name,desc); card.appendChild(detail);
      if (job.status==="queued") {
        const run=document.createElement("button"); run.textContent="Kaynak uygunsa çalıştır";
        run.addEventListener("click", async()=>{ const res=await fetch("/api/media/jobs/"+encodeURIComponent(job.id)+"/run",{method:"POST"}); const d=await res.json(); desc.textContent=d.status+" — "+(d.reason||d.result?.error||""); loadControlRoom(); });
        card.appendChild(run);
      }
      list.appendChild(card);
    });
  } catch (_) { statusBox.textContent="Egemenlik/medya durumu alınamadı."; }
}
$("#queue-media-btn")?.addEventListener("click", async () => {
  const prompt=$("#queue-media-prompt").value.trim();
  const out=$("#media-capabilities");
  if(!prompt){out.textContent="Önce bir görsel tarifi yaz.";return;}
  const response=await fetch("/api/media/queue",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({operation:"generate",prompt})});
  const data=await response.json();
  out.textContent=response.ok ? "Görev kuyruğa eklendi: "+data.id+" · durum: "+data.status : (data.detail||"Görev eklenemedi.");
  loadControlRoom();
});
$("#refresh-media-btn")?.addEventListener("click",loadControlRoom);
$("#verify-approval-btn")?.addEventListener("click",async()=>{
  const out=$("#approval-verify-result");
  try {
    const payload=JSON.parse($("#approval-payload").value);
    const response=await fetch("/api/approval/verify",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({payload,signature_b64:$("#approval-signature").value.trim()})});
    const data=await response.json(); out.textContent=JSON.stringify(data,null,2);
  } catch(error){out.textContent="Payload JSON geçersiz veya doğrulama başarısız.";}
});
$("#clean-room-audit-btn")?.addEventListener("click",async()=>{
  const out=$("#clean-room-audit-result"); out.textContent="Yerel lisans ipuçları taranıyor…";
  try{const response=await fetch("/api/audit/clean-room");const data=await response.json();out.textContent=JSON.stringify(data,null,2);}
  catch(_){out.textContent="Denetim çalıştırılamadı.";}
});

$("#forget-memory-btn")?.addEventListener("click",async()=>{
  const out=$("#forget-memory-result");
  if(!confirm("Seçilen konuya ait eşleşen kişisel hafıza ve sohbet kayıtları silinsin mi?")) return;
  out.textContent="Yerel eşleşmeler taranıyor…";
  try {
    const response=await fetch("/api/privacy/forget",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      topic:$("#forget-topic").value, last_hours:Number($("#forget-hours").value||24), confirmation:$("#forget-confirm").value
    })});
    const data=await response.json(); out.textContent=JSON.stringify(data,null,2);
  } catch(_) { out.textContent="Silme işlemi tamamlanamadı; yerel veriler otomatik sıfırlanmadı."; }
});

let mkaosApprovalPrivateKey = null;
let mkaosApprovalPublicKeyB64 = "";
function bytesToB64(bytes) {
  let binary = "";
  new Uint8Array(bytes).forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary);
}
function canonicalJson(value) {
  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort().map((key) => JSON.stringify(key) + ":" + canonicalJson(value[key])).join(",") + "}";
  }
  return JSON.stringify(value);
}
$("#approval-keygen-btn")?.addEventListener("click",async()=>{
  const box=$("#approval-public-key");
  if(!window.crypto?.subtle){box.textContent="Bu tarayıcı WebCrypto desteklemiyor; anahtar üretilemedi.";return;}
  try {
    const pair=await crypto.subtle.generateKey({name:"Ed25519"},true,["sign","verify"]);
    const privateDer=await crypto.subtle.exportKey("pkcs8",pair.privateKey);
    const publicRaw=await crypto.subtle.exportKey("raw",pair.publicKey);
    mkaosApprovalPrivateKey=pair.privateKey;
    mkaosApprovalPublicKeyB64=bytesToB64(publicRaw);
    const blob=new Blob([privateDer],{type:"application/octet-stream"});
    const link=document.createElement("a"); link.href=URL.createObjectURL(blob); link.download="mkaos-approval-private.pk8"; link.click();
    setTimeout(()=>URL.revokeObjectURL(link.href),1000);
    box.textContent="Açık anahtar (Base64):\n"+mkaosApprovalPublicKeyB64+"\n\nÖzel anahtar indirildi. Dosyayı paylaşma. Açık anahtarı sunucu .env ayarına ekle ve servisi yeniden başlat. Sayfa yenilenirse özel anahtar belleği kaybolur.";
  } catch(error) { box.textContent="Ed25519 üretimi bu tarayıcıda desteklenmiyor: "+String(error.name||"hata"); }
});
$("#approval-sign-btn")?.addEventListener("click",async()=>{
  const out=$("#approval-verify-result");
  if(!mkaosApprovalPrivateKey){out.textContent="Önce bu tarayıcı oturumunda Ed25519 anahtarı üret.";return;}
  try {
    const payload=JSON.parse($("#approval-payload").value);
    const signature=await crypto.subtle.sign({name:"Ed25519"},mkaosApprovalPrivateKey,new TextEncoder().encode(canonicalJson(payload)));
    const signatureB64=bytesToB64(signature);
    $("#approval-signature").value=signatureB64;
    const response=await fetch("/api/approval/verify",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({payload,signature_b64:signatureB64})});
    const data=await response.json(); out.textContent=JSON.stringify(data,null,2);
  } catch(error) { out.textContent="İmza işlemi başarısız. Payload ve sunucu açık anahtarını denetle."; }
});
