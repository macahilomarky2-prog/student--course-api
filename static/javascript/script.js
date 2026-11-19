// Campus Connect - loads dashboard counters from the Flask API.
// The page and the API share the same origin, so relative URLs work locally and on Render.
const API_BASE = "/api";

async function loadStats() {
  const targets = document.querySelectorAll("[data-stat]");
  if (!targets.length) return;

  try {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const stats = await response.json();

    targets.forEach((el) => {
      const key = el.dataset.stat;
      el.textContent = stats[key] !== undefined ? stats[key] : "-";
    });
  } catch (err) {
    console.error("Could not load stats:", err);
    targets.forEach((el) => (el.textContent = "!"));
  }
}

document.addEventListener("DOMContentLoaded", loadStats);
