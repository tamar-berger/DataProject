// ===== Hero helpers =====
document.getElementById("startBtn")?.addEventListener("click", (e) => {
  if (e.currentTarget.getAttribute("href")?.startsWith("#")) {
    e.preventDefault();
    document.querySelector("#rate")?.scrollIntoView({ behavior: "smooth" });
  }
});

const heroVideo = document.querySelector(".video-hero__bg");
if (heroVideo && heroVideo.play) {
  heroVideo.play().catch(() => {
    const tryPlay = () => { heroVideo.play().catch(() => {}); document.removeEventListener("click", tryPlay); };
    document.addEventListener("click", tryPlay, { once: true });
  });
}

// ===== Ratings, sliders, API =====
const rated = new Map();

const selectEl = document.getElementById("countrySelect");
const addBtn = document.getElementById("addCountry");
const listEl = document.getElementById("ratedList");
const goBtn = document.getElementById("goBtn");
const againBtn = document.getElementById("againBtn");
const statusEl = document.getElementById("status");
const resultWrap = document.getElementById("result");
const countryBox = document.getElementById("countryBox");

function colorCountry() {} // replaced after SVG loads

function setRating(name, value) {
  rated.set(name, value);
  window.colorCountry(name, value);
  renderRated();
}

function renderRated() {
  if (!listEl) return;
  listEl.innerHTML = "";
  for (const [country, value] of rated.entries()) {
    const li = document.createElement("li");
    li.className = "rated-item";

    const label = document.createElement("span");
    label.className = "country-label";
    label.textContent = country;

    const stars = document.createElement("div");
    stars.className = "stars";
    for (let i = 1; i <= 5; i++) {
      const btn = document.createElement("button");
      btn.className = "star" + (i <= value ? " active" : "");
      btn.type = "button";
      btn.setAttribute("aria-label", `Rate ${country} ${i} star${i > 1 ? "s" : ""}`);
      btn.textContent = i <= value ? "⭐" : "☆";
      btn.addEventListener("click", () => {
        setRating(country, i);
      });
      stars.appendChild(btn);
    }

    const remove = document.createElement("button");
    remove.className = "remove";
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      rated.delete(country);
      window.colorCountry(country, 0);
      renderRated();
    });

    li.append(label, stars, remove);
    listEl.appendChild(li);
  }
}

addBtn?.addEventListener("click", () => {
  const c = selectEl.value;
  if (!rated.has(c)) setRating(c, 3);
});

// Sliders
document.querySelectorAll('input[type="range"]').forEach(r => {
  const out = r.parentElement.querySelector("output");
  const setVar = () => {
    const min = Number(r.min) || 0;
    const max = Number(r.max) || 100;
    const pct = ((Number(r.value) - min) / (max - min)) * 100;
    r.style.setProperty("--val", pct + "%");
  };
  const sync = () => { out.textContent = r.value; setVar(); };
  r.addEventListener("input", sync);
  sync();
});

async function getRecommendation() {
  if (!goBtn) return;
  statusEl.textContent = "Scoring your preferences...";
  resultWrap.hidden = true;
  goBtn.disabled = true;

  const ratings = Object.fromEntries(rated.entries());
  const weights = {};
  document.querySelectorAll('input[type="range"]').forEach(r => {
    weights[r.dataset.key] = Number(r.value);
  });

  try {
    const resp = await fetch("/api/recommend", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ ratings, weights })
    });

    const txt = await resp.text();
    if (!resp.ok) throw new Error(txt || "Request failed");

    if (countryBox) countryBox.textContent = txt.trim() || "Unknown";
    resultWrap.hidden = false;
    statusEl.textContent = "";
  } catch (err) {
    statusEl.textContent = `Could not get a recommendation, ${err.message}`;
  } finally {
    goBtn.disabled = false;
  }
}

goBtn?.addEventListener("click", getRecommendation);
againBtn?.addEventListener("click", () => {
  resultWrap.hidden = true;
  window.scrollTo({ top: 0, behavior: "smooth" });
});

renderRated();

/* ========= Map rating integration ========= */
(function initMap() {
  const mount = document.getElementById("mapMount");
  if (!mount) return;

  const svgURL = window.APP?.worldSvgUrl;
  if (!svgURL) {
    console.warn("Missing worldSvgUrl");
    return;
  }

  fetch(svgURL, { cache: "force-cache" })
    .then(resp => { if (!resp.ok) throw new Error(`HTTP ${resp.status}`); return resp.text(); })
    .then(svgText => {
      mount.innerHTML = svgText;
      const svg = mount.querySelector("svg");
      if (!svg) return;
      svg.classList.add("world");

      const paths = svg.querySelectorAll("path");
      paths.forEach(p => {
        const n = p.getAttribute("data-name") || p.getAttribute("name") || p.getAttribute("title") || p.getAttribute("id");
        if (n) p.setAttribute("data-name", n);
        p.setAttribute("tabindex", "0");
      });

      const tooltip = document.getElementById("mapTooltip");
      const rater = document.getElementById("rater");
      const raterName = document.getElementById("raterName");
      const raterStars = document.getElementById("raterStars");
      const raterCancel = document.getElementById("raterCancel");
      const raterSave = document.getElementById("raterSave");

      let currentName = null;
      let currentValue = 3;

      function buildStars(val = 3) {
        raterStars.innerHTML = "";
        for (let i = 1; i <= 5; i++) {
          const b = document.createElement("button");
          b.type = "button";
          b.className = i <= val ? "active" : "";
          b.textContent = i <= val ? "⭐" : "☆";
          b.setAttribute("aria-label", `Rate ${i} star${i > 1 ? "s" : ""}`);
          b.addEventListener("click", () => {
            currentValue = i;
            buildStars(i);
          });
          raterStars.appendChild(b);
        }
      }

      function showTooltip(e, name) {
        const rect = svg.getBoundingClientRect();
        tooltip.textContent = name;
        tooltip.style.left = `${e.clientX - rect.left}px`;
        tooltip.style.top = `${e.clientY - rect.top}px`;
        tooltip.style.opacity = "1";
      }
      function hideTooltip() { tooltip.style.opacity = "0"; }

      function openRater(e, name) {
        currentName = name;
        const existing = rated.has(name) ? rated.get(name) : 3;
        currentValue = existing;
        raterName.textContent = name;
        buildStars(existing);
        const vw = window.innerWidth, vh = window.innerHeight;
        const x = Math.min((e.clientX ?? vw / 2) + 12, vw - 240);
        const y = Math.min((e.clientY ?? vh / 2) + 12, vh - 180);
        rater.style.left = `${x}px`;
        rater.style.top = `${y}px`;
        rater.hidden = false;
      }

      function onPathEnter(e) {
        const name = e.target.getAttribute("data-name");
        if (name) showTooltip(e, name);
      }
      function onPathMove(e) {
        const name = e.target.getAttribute("data-name");
        if (name) showTooltip(e, name);
      }
      function onPathLeave() { hideTooltip(); }
      function onPathClick(e) {
        const name = e.target.getAttribute("data-name");
        if (name) openRater(e, name);
      }
      function onPathKey(e) {
        if (e.key === "Enter" || e.key === " ") {
          const name = e.target.getAttribute("data-name");
          if (name) {
            e.preventDefault();
            openRater(e, name);
          }
        }
      }

      paths.forEach(p => {
        p.addEventListener("mouseenter", onPathEnter);
        p.addEventListener("mousemove", onPathMove);
        p.addEventListener("mouseleave", onPathLeave);
        p.addEventListener("click", onPathClick);
        p.addEventListener("keydown", onPathKey);
      });

      raterCancel.addEventListener("click", () => { rater.hidden = true; });
      raterSave.addEventListener("click", () => {
        if (currentName) setRating(currentName, currentValue);
        rater.hidden = true;
      });

      document.addEventListener("keydown", (e) => { if (e.key === "Escape") rater.hidden = true; });
      document.addEventListener("click", (e) => {
        if (!rater.hidden && !rater.contains(e.target) && !svg.contains(e.target)) rater.hidden = true;
      });

      window.colorCountry = function(name, value) {
        const node = svg.querySelector(`path[data-name="${CSS.escape(name)}"]`);
        if (!node) return;
        if (value > 0) node.classList.add("is-rated"); else node.classList.remove("is-rated");
      };

      rated.forEach((v, k) => window.colorCountry(k, v));
    })
    .catch(e => console.warn("Could not load world.svg", e));
})();
