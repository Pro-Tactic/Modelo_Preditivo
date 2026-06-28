/* ================================================================
   brasil_egito.js — carrega os resultados já gerados e renderiza
   ================================================================ */

// Coordenadas dos slots no campo (x%: esquerda→direita, y%: cima→baixo)
const COORDS = {
    "4-4-2": {
        "GK":  {x:50, y:88}, "RB": {x:82, y:72}, "RCB":{x:61, y:74},
        "LCB": {x:39, y:74}, "LB": {x:18, y:72},
        "RM":  {x:82, y:47}, "CM1":{x:60, y:49}, "CM2":{x:40, y:49},
        "LM":  {x:18, y:47},
        "ST1": {x:64, y:18}, "ST2":{x:36, y:18}
    },
    "5-2-3": {
        "GK":  {x:50, y:88},
        "RWB": {x:84, y:65}, "RCB":{x:64, y:76}, "CB":{x:50, y:78},
        "LCB": {x:36, y:76}, "LWB":{x:16, y:65},
        "CM1": {x:60, y:49}, "CM2":{x:40, y:49},
        "RW":  {x:78, y:22}, "ST": {x:50, y:14}, "LW":{x:22, y:22}
    }
};

const SLOT_PT = {
    GK:"GOL",RB:"LD",LB:"LE",RCB:"ZGD",LCB:"ZGE",CB:"ZAG",
    RWB:"ALD",LWB:"ALE",CM:"MC",CM1:"MC",CM2:"MC",
    RM:"MD",LM:"ME",RW:"PD",LW:"PE",ST:"ATA",ST1:"ATA",ST2:"ATA"
};

let simData = null;

// ── inicialização ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
    spawnStars();
    await loadResults();
});

function spawnStars() {
    const sc = document.querySelector(".stars-container");
    for (let i = 0; i < 45; i++) {
        const s = document.createElement("div");
        const size = Math.random() * 2 + 1;
        Object.assign(s.style, {
            position: "absolute",
            width:  size + "px",
            height: size + "px",
            left:   Math.random() * 100 + "%",
            top:    Math.random() * 100 + "%",
            background: "#fff",
            borderRadius: "50%",
            opacity: Math.random() * 0.65 + 0.2
        });
        sc.appendChild(s);
    }
}

// ── busca os resultados na API ────────────────────────────────────────────────
async function loadResults() {
    try {
        const res = await fetch("/api/results");

        if (res.status === 404) {
            const body = await res.json();
            showError(body.erro || "Execute primeiro o script de simulação.");
            return;
        }
        if (!res.ok) throw new Error("Erro inesperado: " + res.status);

        simData = await res.json();
        renderAll(simData);

    } catch (err) {
        showError("Não foi possível carregar os dados.\n" + err.message);
    }
}

function showError(msg) {
    document.getElementById("loading-screen").classList.add("hidden");
    const el = document.getElementById("error-screen");
    el.classList.remove("hidden");
    el.querySelector("p").textContent = msg;
}

// ── renderização principal ────────────────────────────────────────────────────
function renderAll(d) {
    document.getElementById("loading-screen").classList.add("hidden");
    document.getElementById("main-content").classList.remove("hidden");

    renderMatchup(d);
    renderPitch("brasil", d.escalacao_brasil, d.formacao_brasil, "team-brasil");
    renderPitch("egito",  d.escalacao_egito,  d.formacao_egito,  "team-egito");
    renderChart(d.placares);
    renderMetrics(d.stats);
    renderList("list-gols",   d.goleadores,  "green");
    renderList("list-assists", d.assistentes, "red");
}

// ── banner e barra de probabilidade ──────────────────────────────────────────
function renderMatchup(d) {
    const s = d.stats;

    // formações
    document.getElementById("formacao-brasil").textContent = d.formacao_brasil;
    document.getElementById("badge-brasil").textContent    = d.formacao_brasil;
    document.getElementById("formacao-egito").textContent  = d.formacao_egito;
    document.getElementById("badge-egito").textContent     = d.formacao_egito;

    // barra
    const pB = s.probabilidades.brasil;
    const pE = s.probabilidades.empate;
    const pG = s.probabilidades.egito;

    setBar("bar-brasil", "pct-brasil", pB);
    setBar("bar-empate", "pct-empate", pE);
    setBar("bar-egito",  "pct-egito",  pG);

    // quick stats
    document.getElementById("qs-placar").textContent    = d.placares[0]?.placar || "--";
    document.getElementById("qs-1gol-br").textContent   = s.primeiro_gol.brasil.toFixed(2) + "%";
    document.getElementById("qs-1gol-eg").textContent   = s.primeiro_gol.egito.toFixed(2) + "%";

    // favorito
    const favEl  = document.getElementById("qs-fav");
    const favPct = document.getElementById("qs-fav-pct");
    if (pB >= pG && pB >= pE) {
        favEl.textContent = "Brasil";
        favEl.className   = "qs-val green";
        favPct.textContent = "com " + pB.toFixed(2) + "%";
    } else if (pG > pB && pG > pE) {
        favEl.textContent = "Egito";
        favEl.className   = "qs-val red";
        favPct.textContent = "com " + pG.toFixed(2) + "%";
    } else {
        favEl.textContent = "Empate";
        favEl.className   = "qs-val white";
        favPct.textContent = "com " + pE.toFixed(2) + "%";
    }
}

function setBar(barId, pctId, value) {
    document.getElementById(barId).style.width = value + "%";
    document.getElementById(pctId).textContent  = value.toFixed(2) + "%";
}

// ── campo tático ──────────────────────────────────────────────────────────────
function renderPitch(team, lineup, formation, cssClass) {
    const layer = document.getElementById(`players-${team}`);
    layer.innerHTML = "";

    const coords = COORDS[formation] || COORDS["4-4-2"];

    lineup.forEach(player => {
        const slot   = player.slot;
        const name   = player.name;
        const photo  = player.info?.photo_url;
        const coord  = coords[slot] || {x: 50, y: 50};

        const node = document.createElement("div");
        node.className = `pitch-player ${cssClass}`;
        node.style.left = coord.x + "%";
        node.style.top  = coord.y + "%";

        // avatar
        const av = document.createElement("div");
        av.className = "p-avatar";

        if (photo) {
            const img = document.createElement("img");
            img.src = photo;
            img.alt = name;
            img.onerror = () => {
                img.remove();
                av.textContent = name.substring(0, 2).toUpperCase();
            };
            av.appendChild(img);
        } else {
            av.textContent = name.substring(0, 2).toUpperCase();
        }

        // nome (sobrenome)
        const nameLbl = document.createElement("span");
        nameLbl.className = "p-name";
        const parts = name.split(" ");
        nameLbl.textContent = parts.length > 1 ? parts[parts.length - 1] : name;

        node.appendChild(av);
        node.appendChild(nameLbl);

        // tooltip
        node.addEventListener("mouseenter", e => showTooltip(e, player, team));
        node.addEventListener("mouseleave", hideTooltip);

        layer.appendChild(node);
    });
}

// ── tooltip ───────────────────────────────────────────────────────────────────
function showTooltip(e, player, team) {
    const tt = document.getElementById("pitch-tooltip");
    const isBr = team === "brasil";

    let goalPct = 0, assistPct = 0;
    if (simData) {
        const g = simData.goleadores.find(x => x.jogador === player.name);
        const a = simData.assistentes.find(x => x.jogador === player.name);
        if (g) goalPct   = g.prob;
        if (a) assistPct = a.prob;
    }

    tt.innerHTML = `
        <div class="tt-title">${player.name}</div>
        <div class="tt-row"><span>Posição:</span>
            <span class="tt-val" style="color:${isBr ? 'var(--green)' : 'var(--red)'}">
                ${SLOT_PT[player.slot] || player.slot}</span></div>
        <div class="tt-row"><span>Prob. Gol:</span>
            <span class="tt-val">${goalPct.toFixed(2)}%</span></div>
        <div class="tt-row"><span>Prob. Assist.:</span>
            <span class="tt-val">${assistPct.toFixed(2)}%</span></div>
    `;
    tt.classList.add("show");
    moveTT(e);
    node_ref = e.currentTarget;
    node_ref.addEventListener("mousemove", moveTT);
}

function hideTooltip() {
    document.getElementById("pitch-tooltip").classList.remove("show");
}

function moveTT(e) {
    const tt = document.getElementById("pitch-tooltip");
    let x = e.clientX + 14, y = e.clientY + 14;
    if (x + 180 > window.innerWidth)  x = e.clientX - 190;
    if (y + 120 > window.innerHeight) y = e.clientY - 130;
    tt.style.left = x + "px";
    tt.style.top  = y + "px";
}

// ── gráfico de placares ───────────────────────────────────────────────────────
let chart = null;
function renderChart(placares) {
    const ctx = document.getElementById("scoresChart").getContext("2d");
    if (chart) chart.destroy();

    Chart.defaults.color = "#A5B2D6";
    Chart.defaults.font.family = "'Inter', sans-serif";

    chart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: placares.map(p => p.placar),
            datasets: [{
                label: "Probabilidade (%)",
                data:  placares.map(p => p.prob),
                backgroundColor: ctx2 => {
                    const c = ctx2.chart;
                    if (!c.chartArea) return null;
                    const g = c.ctx.createLinearGradient(0, 0, c.chartArea.right, 0);
                    g.addColorStop(0, "rgba(255,23,68,.85)");
                    g.addColorStop(1, "rgba(0,230,118,.9)");
                    return g;
                },
                borderWidth: 0,
                borderRadius: 4,
                barPercentage: 0.6
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(10,12,18,.96)",
                    titleFont: { size: 13, weight: "bold", family: "'Outfit',sans-serif" },
                    bodyFont:  { size: 12 },
                    borderColor: "rgba(255,255,255,.1)",
                    borderWidth: 1,
                    displayColors: false,
                    callbacks: { label: c => `Chance de ${c.raw.toFixed(2)}%` }
                }
            },
            scales: {
                x: { grid: { color: "rgba(255,255,255,.03)" },
                     ticks: { callback: v => v + "%" } },
                y: { grid: { display: false } }
            }
        }
    });
}

// ── métricas ──────────────────────────────────────────────────────────────────
function renderMetrics(s) {
    setText("m-lead-br",  s.lideranca.brasil.toFixed(2) + "%");
    setText("m-lead-eg",  s.lideranca.egito.toFixed(2) + "%");
    setText("m-zerozero", s.primeiro_gol.sem_gol.toFixed(2) + "%");
    setText("m-h1",   s.halves.apenas_1t.toFixed(2) + "%");
    setText("m-h2",   s.halves.apenas_2t.toFixed(2) + "%");
    setText("m-both", s.halves.ambos.toFixed(2) + "%");
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

// ── listas de artilheiros / assistentes ──────────────────────────────────────
function renderList(containerId, lista, colorType) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";

    lista.slice(0, 8).forEach((item, i) => {
        const photo = item.info?.photo_url;
        const color = colorType === "green" ? "var(--green)" : "var(--red)";
        const glow  = colorType === "green" ? "var(--green-glow)" : "var(--red-glow)";

        const row = document.createElement("div");
        row.className = "pl-item";

        row.innerHTML = `
            <span class="pl-rank">#${i + 1}</span>
            <div class="pl-avatar">
                <img src="${photo || ""}" alt="${item.jogador}"
                     onerror="this.parentElement.textContent='${item.jogador.substring(0,2).toUpperCase()}'">
            </div>
            <div class="pl-info">
                <span class="pl-name">${item.jogador}</span>
                <span class="pl-equipe">${item.equipe === "Brazil" ? "Brasil" : "Egito"}</span>
                <div class="pl-bar-bg">
                    <div class="pl-bar-fill"
                         style="width:${Math.min(100, item.prob * 3.2)}%;
                                background:${color};
                                box-shadow:0 0 6px ${glow}">
                    </div>
                </div>
            </div>
            <span class="pl-pct" style="color:${color}">${item.prob.toFixed(2)}%</span>
        `;
        container.appendChild(row);
    });
}
