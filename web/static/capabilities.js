/* MKAOS yetenek matrisi + yerel poster */
(function () {
  const box = () => document.querySelector("#capabilities-box");
  const preview = () => document.querySelector("#poster-preview");

  async function loadCapabilities() {
    const el = box();
    if (!el) return;
    el.textContent = "Yükleniyor…";
    try {
      const res = await fetch("/api/capabilities");
      const data = await res.json();
      if (!res.ok) {
        el.textContent = data.detail || "Yetenekler alınamadı";
        return;
      }
      const m = data.matrix || {};
      const lines = ["schema: " + (data.schema || "—"), ""];
      Object.keys(m).forEach((key) => {
        const row = m[key] || {};
        lines.push(
          "▸ " +
            key +
            " · " +
            (row.status || "?") +
            (row.note ? " — " + row.note : "")
        );
      });
      if (data.universe) {
        lines.push("");
        lines.push(
          "Evren: sayfa=" +
            (data.universe.total_pages ?? "—") +
            " tur=" +
            (data.universe.total_runs ?? "—") +
            " tohum=" +
            (data.universe.seed_count ?? "—")
        );
      }
      lines.push("");
      lines.push("production_ready_claim: " + String(data.production_ready_claim));
      el.textContent = lines.join("\n");
    } catch (e) {
      el.textContent = "Hata: " + (e.message || e);
    }
  }

  async function makePoster() {
    const title = prompt("Poster başlığı", "MKAOS Yerel Stüdyo") || "MKAOS";
    const body =
      prompt("Poster metni", "Yerel üretim · ağ yok · inceleme sonrası kullan") ||
      "";
    const res = await fetch("/api/media/poster", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, body }),
    });
    const data = await res.json();
    const el = preview();
    if (!res.ok) {
      if (el) el.textContent = data.detail || "Poster üretilemedi";
      return;
    }
    if (el) {
      el.innerHTML = "";
      const p = document.createElement("p");
      p.textContent =
        "Dosya: " + (data.filename || "") + " · sha256: " + (data.sha256 || "").slice(0, 16) + "…";
      el.appendChild(p);
      if (data.filename) {
        const img = document.createElement("img");
        img.alt = title;
        img.style.maxWidth = "100%";
        img.src = "/memory/generated_images/" + encodeURIComponent(data.filename);
        // static serve may differ; show path as fallback
        img.onerror = () => {
          p.textContent += " (önizleme yolu yapılandırmaya bağlı: " + (data.path || "") + ")";
        };
        el.appendChild(img);
      }
    }
    alert("Poster üretildi: " + (data.filename || data.path));
  }

  function wire() {
    document.querySelector("#cap-refresh-btn")?.addEventListener("click", loadCapabilities);
    document.querySelector("#poster-btn")?.addEventListener("click", makePoster);
    document.querySelector("#poster-quick-btn")?.addEventListener("click", makePoster);
    // panel switch hook
    const orig = window.switchPanel;
    if (typeof orig === "function") {
      window.switchPanel = function (name) {
        orig(name);
        if (name === "capabilities") loadCapabilities();
      };
    }
    document.querySelectorAll('.nav-btn[data-panel="capabilities"]').forEach((btn) => {
      btn.addEventListener("click", () => setTimeout(loadCapabilities, 50));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
