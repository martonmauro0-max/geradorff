const state = { device: null, style: null, level: null };
let lastResult = null;

function setupGrid(gridId, key) {
  const grid = document.getElementById(gridId);
  const buttons = grid.querySelectorAll(".option-btn");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state[key] = btn.dataset.value;
      if (key === "device") {
        document.getElementById("device-selected").textContent = "Selecionado: " + btn.dataset.value;
      }
    });
  });
}

setupGrid("device-grid", "device");
setupGrid("style-grid", "style");
setupGrid("level-grid", "level");

const searchInput = document.getElementById("device-search");
searchInput.addEventListener("input", () => {
  const term = searchInput.value.trim().toLowerCase();
  const buttons = document.querySelectorAll(".device-btn");
  buttons.forEach((btn) => {
    const text = btn.dataset.value.toLowerCase();
    if (term === "" || text.includes(term)) {
      btn.classList.remove("hidden");
    } else {
      btn.classList.add("hidden");
    }
  });
});

const labels = {
  general: "Geral",
  red_dot: "Red Dot",
  scope_2x: "Mira 2x",
  scope_4x: "Mira 4x",
  sniper: "Sniper (AWM)",
  free_look: "Free Look",
};

document.getElementById("generate-btn").addEventListener("click", async () => {
  if (!state.device || !state.style || !state.level) {
    alert("Escolhe telemovel, estilo de jogo e nivel antes de gerar.");
    return;
  }

  const btn = document.getElementById("generate-btn");
  btn.textContent = "A gerar...";
  btn.disabled = true;

  try {
    const res = await fetch("/gerar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    });
    const data = await res.json();

    if (data.error) {
      alert(data.error);
      return;
    }

    lastResult = data.result;

    const rowsEl = document.getElementById("result-rows");
    rowsEl.innerHTML = "";
    for (const key in labels) {
      const row = document.createElement("div");
      row.className = "result-row";
      row.innerHTML = "<span>" + labels[key] + "</span><span class=\"result-value\">" + data.result[key] + "</span>";
      rowsEl.appendChild(row);
    }

    const card = document.getElementById("result-card");
    card.classList.remove("show");
    void card.offsetWidth;
    card.classList.add("show");

    document.getElementById("total-uses").textContent = data.total_uses;
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    alert("Erro ao gerar. Tenta novamente.");
  } finally {
    btn.textContent = "Gerar Sensibilidade";
    btn.disabled = false;
  }
});

function buildResultText() {
  if (!lastResult) return "";
  let text = "Sensibilidade Free Fire - " + state.device + " (" + state.style + ", " + state.level + ")\n";
  for (const key in labels) {
    text += labels[key] + ": " + lastResult[key] + "\n";
  }
  return text;
}

document.getElementById("copy-btn").addEventListener("click", async () => {
  const text = buildResultText();
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    alert("Copiado!");
  } catch (e) {
    alert("Nao foi possivel copiar automaticamente. Copia manualmente o resultado.");
  }
});

document.getElementById("whatsapp-btn").addEventListener("click", () => {
  const text = buildResultText();
  if (!text) return;
  const url = "https://wa.me/?text=" + encodeURIComponent(text);
  window.open(url, "_blank");
});

const FAV_KEY = "geradorff_favoritos";

function getFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAV_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function saveFavorites(favs) {
  localStorage.setItem(FAV_KEY, JSON.stringify(favs));
}

function renderFavorites() {
  const favs = getFavorites();
  const card = document.getElementById("favorites-card");
  const list = document.getElementById("favorites-list");

  if (favs.length === 0) {
    card.style.display = "none";
    return;
  }

  card.style.display = "block";
  list.innerHTML = "";
  favs.forEach((fav, index) => {
    const item = document.createElement("div");
    item.className = "favorite-item";
    item.innerHTML =
      "<span>" + fav.device + " - " + fav.style + " - " + fav.level + "</span>" +
      "<button data-index=\"" + index + "\">Usar</button>";
    list.appendChild(item);
  });

  list.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const fav = favs[parseInt(btn.dataset.index)];
      selectByValue("device-grid", "device", fav.device);
      selectByValue("style-grid", "style", fav.style);
      selectByValue("level-grid", "level", fav.level);
    });
  });
}

function selectByValue(gridId, key, value) {
  const grid = document.getElementById(gridId);
  const buttons = grid.querySelectorAll(".option-btn");
  buttons.forEach((b) => {
    b.classList.remove("hidden");
    if (b.dataset.value === value) {
      b.classList.add("active");
      state[key] = value;
      if (key === "device") {
        document.getElementById("device-selected").textContent = "Selecionado: " + value;
        document.getElementById("device-search").value = "";
      }
    } else {
      b.classList.remove("active");
    }
  });
}

document.getElementById("save-fav-btn").addEventListener("click", () => {
  if (!state.device || !state.style || !state.level) {
    alert("Escolhe telemovel, estilo e nivel antes de guardar como favorito.");
    return;
  }
  const favs = getFavorites();
  const exists = favs.some((f) => f.device === state.device && f.style === state.style && f.level === state.level);
  if (exists) {
    alert("Este favorito ja existe.");
    return;
  }
  favs.push({ device: state.device, style: state.style, level: state.level });
  saveFavorites(favs);
  renderFavorites();
  alert("Favorito guardado!");
});

renderFavorites();
