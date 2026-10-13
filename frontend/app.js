/* ─────────────────────────────────────────────────────────
   AI Resume Screener — Frontend Logic
   ───────────────────────────────────────────────────────── */

const API_BASE = window.location.origin;

let selectedFiles = [];
let lastResults = null;

// ─── Drag & Drop ──────────────────────────────────────────
const dropZone = document.getElementById("dropZone");
const resumeInput = document.getElementById("resumeInput");

dropZone.addEventListener("click", () => resumeInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  addFiles([...e.dataTransfer.files]);
});
resumeInput.addEventListener("change", () => {
  addFiles([...resumeInput.files]);
  resumeInput.value = "";
});

function addFiles(files) {
  const allowed = ["pdf", "docx", "doc", "txt"];
  files.forEach((f) => {
    const ext = f.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
      showToast(`❌ ${f.name} — unsupported format`, "error");
      return;
    }
    if (!selectedFiles.find((x) => x.name === f.name && x.size === f.size)) {
      selectedFiles.push(f);
    }
  });
  renderFileList();
}

function removeFile(idx) {
  selectedFiles.splice(idx, 1);
  renderFileList();
}

function renderFileList() {
  const fl = document.getElementById("fileList");
  if (!selectedFiles.length) {
    fl.classList.add("hidden");
    fl.innerHTML = "";
    return;
  }
  fl.classList.remove("hidden");
  fl.innerHTML = selectedFiles
    .map((f, i) => {
      const ext = f.name.split(".").pop().toUpperCase();
      const icon = ext === "PDF" ? "📕" : ext === "DOCX" || ext === "DOC" ? "📘" : "📄";
      const size = f.size > 1024 * 1024
        ? (f.size / 1024 / 1024).toFixed(1) + " MB"
        : Math.round(f.size / 1024) + " KB";
      return `
        <div class="file-item">
          <span class="file-icon">${icon}</span>
          <span class="file-name" title="${f.name}">${f.name}</span>
          <span class="file-size">${size}</span>
          <button class="file-remove" onclick="removeFile(${i})" title="Remove">✕</button>
        </div>`;
    })
    .join("");
}

// ─── Analysis ─────────────────────────────────────────────
async function analyzeResumes() {
  const jd = document.getElementById("jobDescription").value.trim();
  if (!jd) {
    showToast("⚠️ Please enter a job description.", "warn");
    return;
  }
  if (!selectedFiles.length) {
    showToast("⚠️ Please upload at least one resume.", "warn");
    return;
  }

  const fd = new FormData();
  fd.append("job_description", jd);
  selectedFiles.forEach((f) => fd.append("resumes", f));

  document.getElementById("formSection").classList.add("hidden");
  document.getElementById("loadingSection").classList.remove("hidden");
  document.getElementById("resultsSection").classList.add("hidden");

  try {
    const res = await fetch(`${API_BASE}/api/screen`, {
      method: "POST",
      body: fd,
    });

    const responseText = await res.text();
    let payload = null;
    try {
      payload = responseText ? JSON.parse(responseText) : null;
    } catch {
      payload = null;
    }

    if (!res.ok) {
      throw new Error(payload?.error || "Server error while screening resumes.");
    }

    if (!payload || typeof payload !== "object") {
      throw new Error("Invalid response from server.");
    }

    lastResults = payload;
    renderResults(payload);
  } catch (err) {
    lastResults = null;
    document.getElementById("loadingSection").classList.add("hidden");
    document.getElementById("formSection").classList.remove("hidden");
    showToast("❌ Error: " + (err?.message || "Unknown error"), "error");
  }
}

// ─── Render Results ───────────────────────────────────────
function renderResults(data) {
  const safeData = data || {};
  const jds = safeData.job_description_summary || {};
  const candidates = Array.isArray(safeData.candidates) ? safeData.candidates : [];

  document.getElementById("loadingSection").classList.add("hidden");
  document.getElementById("resultsSection").classList.remove("hidden");

  const jdCard = document.getElementById("jdSummaryCard");
  const requiredSkills = Array.isArray(jds.required_skills) ? jds.required_skills : [];
  const softSkills = Array.isArray(jds.soft_skills) ? jds.soft_skills : [];
  jdCard.innerHTML = `
    <h3 style="font-size:1rem;font-weight:700;margin-bottom:1.2rem;">📊 Job Description Analysis</h3>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;">
      <div>
        <div class="gauge-label" style="margin-bottom:.5rem;">🔧 Required Technical Skills</div>
        <div class="skill-chips">
          ${requiredSkills.length
            ? requiredSkills.map((s) => `<span class="chip chip-accent">${escHtml(String(s))}</span>`).join("")
            : '<span style="color:var(--text-muted);font-size:.85rem;">None detected</span>'}
        </div>
      </div>
      <div>
        <div class="gauge-label" style="margin-bottom:.5rem;">🤝 Soft Skills</div>
        <div class="skill-chips">
          ${softSkills.length
            ? softSkills.map((s) => `<span class="chip chip-teal">${escHtml(String(s))}</span>`).join("")
            : '<span style="color:var(--text-muted);font-size:.85rem;">None detected</span>'}
        </div>
      </div>
      <div>
        <div class="gauge-label" style="margin-bottom:.5rem;">⏱️ Experience Required</div>
        <span class="chip chip-yellow">${jds.required_experience_years != null
          ? `${jds.required_experience_years}+ years`
          : "Not specified"}</span>
      </div>
    </div>`;

  const totalProcessed = Number(safeData.total_processed) || 0;
  const totalErrors = Number(safeData.total_errors) || 0;
  document.getElementById("resultsMeta").textContent =
    `${totalProcessed} candidate${totalProcessed !== 1 ? "s" : ""} analyzed${totalErrors ? ` · ${totalErrors} error(s)` : ""}`;

  const container = document.getElementById("candidateCards");
  container.innerHTML = "";

  if (!candidates.length) {
    container.innerHTML = '<div class="error-card"><span style="font-size:1.3rem;">⚠️</span><div><div style="font-weight:600;margin-bottom:.2rem;">No candidates</div><div class="error-msg">No valid resume results were returned.</div></div></div>';
    return;
  }

  candidates.forEach((c) => {
    if (c.error) {
      container.innerHTML += `
        <div class="error-card">
          <span style="font-size:1.3rem;">⚠️</span>
          <div>
            <div style="font-weight:600;margin-bottom:.2rem;">${escHtml(String(c.filename || "Unknown file"))}</div>
            <div class="error-msg">${escHtml(String(c.error))}</div>
          </div>
        </div>`;
      return;
    }

    const scoreObj = c.scores || {};
    const skills = c.skills || {};
    const rec = c.recommendation || { label: "Unknown", color: "red", icon: "❔" };
    const rank = Number(c.rank) || 0;
    const rankClass = rank > 0 && rank <= 3 ? `rank-${rank}` : "rank-n";
    const rankLabel = rank > 0 && rank <= 3 ? ["🥇", "🥈", "🥉"][rank - 1] : `#${rank || 1}`;
    const score = Number(scoreObj.final) || 0;
    const scoreColor = scoreToColor(score);

    const matched = Array.isArray(skills.matched) ? skills.matched : [];
    const missing = Array.isArray(skills.missing) ? skills.missing : [];
    const candidateTechnical = Array.isArray(skills.candidate_technical) ? skills.candidate_technical : [];
    const candidateSoft = Array.isArray(skills.candidate_soft) ? skills.candidate_soft : [];

    const cardEl = document.createElement("div");
    cardEl.className = "candidate-card";
    cardEl.dataset.color = rec.color || "red";

    cardEl.innerHTML = `
      <div class="card-header" onclick="toggleCard(this)">
        <div class="rank-badge ${rankClass}">${rankLabel}</div>
        <div class="candidate-info">
          <div class="candidate-name">${escHtml(String(c.candidate_name || "Unknown Candidate"))}</div>
          <div class="candidate-file">📎 ${escHtml(String(c.filename || "Unknown file"))}</div>
          ${c.email || c.phone
            ? `<div class="candidate-contact">${c.email ? "✉️ " + escHtml(String(c.email)) : ""}${c.email && c.phone ? " &nbsp;|&nbsp; " : ""}${c.phone ? "📞 " + escHtml(String(c.phone)) : ""}</div>`
            : ""}
        </div>
        <div class="score-block">
          <div class="score-big" style="color:${scoreColor}">${score}%</div>
          <div class="score-label">Match Score</div>
          <div class="rec-badge rec-${rec.color || "red"}">${rec.icon || "❔"} ${rec.label || "Unknown"}</div>
        </div>
        <span class="expand-icon">▼</span>
      </div>
      <div class="card-body">
        <div class="score-gauges">
          ${buildGauge("Content Similarity", Number(scoreObj.tfidf_similarity) || 0, scoreToColor(Number(scoreObj.tfidf_similarity) || 0))}
          ${buildGauge("Skill Overlap", Number(scoreObj.skill_overlap) || 0, scoreToColor(Number(scoreObj.skill_overlap) || 0))}
          ${buildGauge("Education Match", Number(scoreObj.education) || 0, scoreToColor(Number(scoreObj.education) || 0))}
          ${buildGauge("Experience Match", Number(scoreObj.experience) || 0, scoreToColor(Number(scoreObj.experience) || 0))}
        </div>

        ${c.experience_years != null
          ? `<div style="margin-bottom:1.2rem;"><span class="exp-tag">⏱️ ${c.experience_years} year${c.experience_years !== 1 ? "s" : ""} experience detected</span></div>`
          : ""}

        <div class="skills-grid">
          <div class="skills-box">
            <div class="skills-box-title" style="color:var(--green);">✅ Matched Skills</div>
            <div class="skills-chips">
              ${matched.length
                ? matched.map((s) => `<span class="chip chip-matched">${escHtml(String(s))}</span>`).join("")
                : '<span class="no-skills">No JD skills matched</span>'}
            </div>
          </div>
          <div class="skills-box">
            <div class="skills-box-title" style="color:var(--red);">❌ Missing Skills</div>
            <div class="skills-chips">
              ${missing.length
                ? missing.map((s) => `<span class="chip chip-missing">${escHtml(String(s))}</span>`).join("")
                : '<span class="no-skills">All JD skills covered!</span>'}
            </div>
          </div>
          <div class="skills-box">
            <div class="skills-box-title" style="color:var(--blue);">🔧 All Candidate Skills</div>
            <div class="skills-chips">
              ${candidateTechnical.length
                ? candidateTechnical.map((s) => `<span class="chip chip-extra">${escHtml(String(s))}</span>`).join("")
                : '<span class="no-skills">None detected</span>'}
            </div>
          </div>
          <div class="skills-box">
            <div class="skills-box-title" style="color:#d8b4fe;">🤝 Soft Skills</div>
            <div class="skills-chips">
              ${candidateSoft.length
                ? candidateSoft.map((s) => `<span class="chip chip-soft">${escHtml(String(s))}</span>`).join("")
                : '<span class="no-skills">None detected</span>'}
            </div>
          </div>
        </div>
      </div>`;

    container.appendChild(cardEl);

    setTimeout(() => {
      cardEl.querySelectorAll(".gauge-fill").forEach((el) => {
        el.style.width = el.dataset.pct + "%";
      });
    }, 100);
  });
}

function buildGauge(label, value, color) {
  return `
    <div class="gauge-item">
      <div class="gauge-label">${label}</div>
      <div class="gauge-bar">
        <div class="gauge-fill" data-pct="${value}" style="width:0%;background:${color};"></div>
      </div>
      <div class="gauge-value" style="color:${color}">${value}%</div>
    </div>`;
}

function scoreToColor(score) {
  if (score >= 80) return "#22c55e";
  if (score >= 65) return "#3b82f6";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}

function toggleCard(header) {
  if (!header) return;
  header.classList.toggle("open");
  const body = header.nextElementSibling;
  if (!body) return;
  body.classList.toggle("open");
  if (body.classList.contains("open")) {
    body.querySelectorAll(".gauge-fill").forEach((el) => {
      el.style.width = el.dataset.pct + "%";
    });
  }
}

// ─── Filter ───────────────────────────────────────────────
function filterResults(color, btn) {
  document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  document.querySelectorAll(".candidate-card").forEach((card) => {
    if (color === "all" || card.dataset.color === color) {
      card.classList.remove("hidden");
    } else {
      card.classList.add("hidden");
    }
  });
}

// ─── Reset ────────────────────────────────────────────────
function resetForm() {
  selectedFiles = [];
  lastResults = null;
  renderFileList();
  document.getElementById("jobDescription").value = "";
  document.getElementById("resultsSection").classList.add("hidden");
  document.getElementById("formSection").classList.remove("hidden");
  document.getElementById("loadingSection").classList.add("hidden");
  document.querySelectorAll(".filter-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.filter === "all");
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ─── Download Report ──────────────────────────────────────
function downloadReport() {
  if (!lastResults) return;
  const blob = new Blob([JSON.stringify(lastResults, null, 2)], {
    type: "application/json",
  });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `resume_screening_report_${Date.now()}.json`;
  a.click();
}

// ─── Toast ────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const existing = document.getElementById("toast");
  if (existing) existing.remove();
  const t = document.createElement("div");
  t.id = "toast";
  const bg = type === "error" ? "#ef4444" : type === "warn" ? "#f59e0b" : "#6c63ff";
  t.style.cssText = `
    position:fixed;bottom:2rem;right:2rem;background:${bg};color:#fff;
    padding:.85rem 1.4rem;border-radius:10px;font-size:.9rem;font-weight:500;
    box-shadow:0 8px 24px rgba(0,0,0,.4);z-index:9999;animation:fadeIn .3s ease;`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// Inject fadeIn keyframe
const style = document.createElement("style");
style.textContent = "@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}";
document.head.appendChild(style);

// ─── Helpers ─────────────────────────────────────────────
function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
