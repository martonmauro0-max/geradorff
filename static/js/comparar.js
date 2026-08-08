const labels = {
  general: "Geral",
  red_dot: "Red Dot",
  scope_2x: "Mira 2x",
  scope_4x: "Mira 4x",
  sniper: "Sniper (AWM)",
  free_look: "Free Look",
};

async function fetchResult(device, style, level) {
  const res = await fetch("/gerar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device, style, level }),
  });
  return res.json();
}

document.getElementById("compare-btn").addEventListener("click", async () => {
  const btn = document.getElementById("compare-btn");
  btn.textContent = "A comparar...";
  btn.disabled = true;

  try {
    const deviceA = document.getElementById("device-a").value;
    const styleA = document.getElementById("style-a").value;
    const levelA = document.getElementById("level-a").value;
    const deviceB = document.getElementById("device-b").value;
    const styleB = document.getElementById("style-b").value;
    const levelB = document.getElementById("level-b").value;

    const [dataA, dataB] = await Promise.all([
      fetchResult(deviceA, styleA, levelA),
      fetchResult(deviceB, styleB, levelB),
    ]);

    if (dataA.error || dataB.error) {
      alert("Erro ao gerar uma das combinacoes.");
      return;
    }

    const rowsEl = document.getElementById("compare-rows");
    rowsEl.innerHTML = "";

    const header = document.createElement("div");
    header.className = "result-row";
    header.innerHTML = "<span></span><span style='color:var(--neon-blue);font-weight:700;'>A</span><span style='color:var(--neon-orange);font-weight:700;'>B</span>";
    header.style.display = "grid";
    header.style.gridTemplateColumns = "1fr auto auto";
    header.style.gap = "12px";
    rowsEl.appendChild(header);

    for (const key in labels) {
      const row = document.createElement("div");
      row.className = "result-row";
      row.style.display = "grid";
      row.style.gridTemplateColumns = "1fr auto auto";
      row.style.gap = "12px";
      row.innerHTML =
        "<span>" + labels[key] + "</span>" +
        "<span class='result-value'>" + dataA.result[key] + "</span>" +
        "<span class='result-value' style='color:var(--neon-orange);'>" + dataB.result[key] + "</span>";
      rowsEl.appendChild(row);
    }

    document.getElementById("compare-result").style.display = "block";
  } catch (e) {
    alert("Erro ao comparar. Tenta novamente.");
  } finally {
    btn.textContent = "Comparar";
    btn.disabled = false;
  }
});
