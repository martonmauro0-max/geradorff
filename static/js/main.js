const state = { device: null, style: null, level: null, dpi: "com" };
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
setupGrid("dpi-grid", "dpi");

const searchInput = document.getElementById("device-search");
searchInput.addEventListener("input", () => {
  const term = searchInput.value.trim().toLowerCase();
  const groups = document.querySelectorAll(".device-brand-group");
  groups.forEach((group) => {
    const buttons = group.querySelectorAll(".device-btn");
    let visibleCount = 0;
    buttons.forEach((btn) => {
      const text = btn.dataset.value.toLowerCase();
      if (term === "" || text.includes(term)) {
        btn.classList.remove("hidden");
        visibleCount++;
      } else {
        btn.classList.add("hidden");
      }
    });
    group.style.display = visibleCount > 0 ? "block" : "none";
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

    if (state.dpi === "com") {
      let deviceMaxDpi = 800;
      try {
        const dpiRes = await fetch("/device-info?device=" + encodeURIComponent(state.device));
        const dpiData = await dpiRes.json();
        deviceMaxDpi = dpiData.max_dpi || 800;
      } catch (e) {
        deviceMaxDpi = 800;
      }
      const dpiFloor = 320;
      const dpiCeil = Math.min(1200, deviceMaxDpi);
      const dpiRange = Math.max(dpiCeil - dpiFloor, 0);
      const dpiValue = Math.round(dpiFloor + (data.result.general / 200) * dpiRange);
      lastResult.dpi = dpiValue;
      const dpiRow = document.createElement("div");
      dpiRow.className = "result-row";
      dpiRow.innerHTML = "<span>DPI recomendado (max " + dpiCeil + ")</span><span class=\"result-value\">" + dpiValue + "</span>";
      rowsEl.appendChild(dpiRow);
    } else {
      delete lastResult.dpi;
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

const HUD_FAV_KEY = "geradorff_hud_favoritos";
let selectedFingers = null;
let lastHud = null;

const hudGrid = document.getElementById("hud-fingers-grid");
hudGrid.querySelectorAll(".option-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    hudGrid.querySelectorAll(".option-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    selectedFingers = btn.dataset.value;
  });
});

function getHudFavorites() {
  try {
    return JSON.parse(localStorage.getItem(HUD_FAV_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function saveHudFavorites(favs) {
  localStorage.setItem(HUD_FAV_KEY, JSON.stringify(favs));
}

function renderHudFavorites() {
  const favs = getHudFavorites();
  const list = document.getElementById("hud-favorites-list");
  list.innerHTML = "";
  if (favs.length === 0) return;

  const title = document.createElement("div");
  title.className = "field-label";
  title.textContent = "HUDs favoritos";
  list.appendChild(title);

  favs.forEach((fav) => {
    const item = document.createElement("div");
    item.className = "favorite-item";
    item.innerHTML = "<span>" + fav.fingers + " dedo" + (fav.fingers > 1 ? "s" : "") + " - " + fav.code + "</span>";
    list.appendChild(item);
  });
}

const HUD_LAYOUTS = {
  1: [
    [{ label: "Fogo", x: 88, y: 78 }],
    [{ label: "Fogo", x: 85, y: 65 }],
    [{ label: "Fogo", x: 90, y: 88 }],
    [{ label: "Fogo", x: 82, y: 75 }],
    [{ label: "Fogo", x: 92, y: 60 }],
  ],
  2: [
    [{ label: "Fogo", x: 88, y: 78 }, { label: "Mira", x: 70, y: 60 }],
    [{ label: "Fogo", x: 85, y: 65 }, { label: "Mira", x: 65, y: 80 }],
    [{ label: "Fogo", x: 90, y: 85 }, { label: "Mira", x: 75, y: 55 }],
    [{ label: "Fogo", x: 82, y: 70 }, { label: "Mira", x: 60, y: 65 }],
    [{ label: "Fogo", x: 92, y: 60 }, { label: "Mira", x: 72, y: 82 }],
  ],
  3: [
    [{ label: "Fogo", x: 88, y: 78 }, { label: "Mira", x: 70, y: 60 }, { label: "Salto", x: 55, y: 85 }],
    [{ label: "Fogo", x: 85, y: 65 }, { label: "Mira", x: 65, y: 80 }, { label: "Salto", x: 45, y: 70 }],
    [{ label: "Fogo", x: 90, y: 85 }, { label: "Mira", x: 75, y: 55 }, { label: "Salto", x: 50, y: 75 }],
    [{ label: "Fogo", x: 82, y: 70 }, { label: "Mira", x: 60, y: 65 }, { label: "Salto", x: 40, y: 80 }],
    [{ label: "Fogo", x: 92, y: 60 }, { label: "Mira", x: 72, y: 82 }, { label: "Salto", x: 48, y: 65 }],
  ],
  4: [
    [{ label: "Fogo", x: 88, y: 78 }, { label: "Mira", x: 70, y: 60 }, { label: "Salto", x: 55, y: 85 }, { label: "Agac", x: 40, y: 65 }],
    [{ label: "Fogo", x: 85, y: 65 }, { label: "Mira", x: 65, y: 80 }, { label: "Salto", x: 45, y: 70 }, { label: "Agac", x: 30, y: 85 }],
    [{ label: "Fogo", x: 90, y: 85 }, { label: "Mira", x: 75, y: 55 }, { label: "Salto", x: 50, y: 75 }, { label: "Agac", x: 35, y: 60 }],
    [{ label: "Fogo", x: 82, y: 70 }, { label: "Mira", x: 60, y: 65 }, { label: "Salto", x: 40, y: 80 }, { label: "Agac", x: 25, y: 70 }],
    [{ label: "Fogo", x: 92, y: 60 }, { label: "Mira", x: 72, y: 82 }, { label: "Salto", x: 48, y: 65 }, { label: "Agac", x: 32, y: 90 }],
  ],
};

function generateHudCode(fingers, variant) {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let rand = "";
  const seed = fingers * 1000 + variant * 37;
  let x = seed;
  for (let i = 0; i < 4; i++) {
    x = (x * 9301 + 49297) % 233280;
    rand += chars[Math.floor((x / 233280) * chars.length)];
  }
  return "HUD-" + fingers + "D-V" + variant + "-" + rand;
}

function renderHudMock(fingers, variant) {
  const mock = document.getElementById("hud-mock");
  mock.innerHTML = "";
  const layout = HUD_LAYOUTS[fingers][variant - 1];
  layout.forEach((point) => {
    const dot = document.createElement("div");
    dot.className = "hud-dot";
    dot.style.left = point.x + "%";
    dot.style.top = point.y + "%";
    dot.textContent = point.label;
    mock.appendChild(dot);
  });
}

document.getElementById("hud-btn").addEventListener("click", () => {
  if (!selectedFingers) {
    alert("Escolhe o numero de dedos antes de gerar.");
    return;
  }
  const fingers = parseInt(selectedFingers);
  const variant = Math.floor(Math.random() * 5) + 1;
  const code = generateHudCode(fingers, variant);
  lastHud = { fingers: fingers, variant: variant, code: code };
  document.getElementById("hud-value").textContent = fingers + " dedo" + (fingers > 1 ? "s" : "") + " - Variante " + variant;
  document.getElementById("hud-code").textContent = code;
  renderHudMock(fingers, variant);
  document.getElementById("hud-result").style.display = "block";
});

document.getElementById("hud-copy-btn").addEventListener("click", async () => {
  if (!lastHud) return;
  try {
    await navigator.clipboard.writeText(lastHud.code);
    alert("Codigo copiado!");
  } catch (e) {
    alert("Nao foi possivel copiar. Copia manualmente: " + lastHud.code);
  }
});

document.getElementById("hud-fav-btn").addEventListener("click", () => {
  if (lastHud === null) return;
  const favs = getHudFavorites();
  const exists = favs.some((f) => f.fingers === lastHud.fingers && f.variant === lastHud.variant);
  if (!exists) {
    favs.push(lastHud);
    saveHudFavorites(favs);
    renderHudFavorites();
    alert("HUD guardado como favorito!");
  } else {
    alert("Este HUD ja esta nos favoritos.");
  }
});

renderHudFavorites();
