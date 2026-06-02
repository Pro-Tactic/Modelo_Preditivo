// Global Variables
let allPlayers = { Arsenal: [], PSG: [] };
let activeInjuries = [];
let scoresChart = null;
let currentSimulationData = null;
let activeTeamTab = "PSG"; // "Arsenal" or "PSG"

// DOM Elements
const injuryTrigger = document.getElementById("injury-trigger");
const injuryOptions = document.getElementById("custom-select-wrapper"); // We'll toggle class 'open' on parent
const selectWrapper = document.querySelector(".custom-select-wrapper");
const playerSearch = document.getElementById("player-search");
const playersListOptions = document.getElementById("players-list-options");
const activeInjuriesList = document.getElementById("active-injuries-list");
const simSlider = document.getElementById("sim-slider");
const simSliderValue = document.getElementById("sim-slider-value");
const runSimBtn = document.getElementById("run-simulation-btn");
const loadingOverlay = document.getElementById("loading-overlay");

// Coordinate mappings for formations
// Coordinates are in percentages (x: left-to-right 0-100, y: bottom-to-top 0-100)
// GK is at bottom (y: 90), Strikers at top (y: 10)
const POSITION_COORDINATES = {
    "4-3-3": {
        "GK":  { x: 50, y: 92 },
        "RB":  { x: 85, y: 72 },
        "RCB": { x: 62, y: 74 },
        "LCB": { x: 38, y: 74 },
        "LB":  { x: 15, y: 72 },
        "CM1": { x: 70, y: 48 },
        "CM2": { x: 50, y: 52 },
        "CM3": { x: 30, y: 48 },
        "RW":  { x: 80, y: 22 },
        "ST":  { x: 50, y: 15 },
        "LW":  { x: 20, y: 22 }
    },
    "4-2-3-1": {
        "GK":   { x: 50, y: 92 },
        "RB":   { x: 85, y: 72 },
        "RCB":  { x: 62, y: 74 },
        "LCB":  { x: 38, y: 74 },
        "LB":   { x: 15, y: 72 },
        "VOL1": { x: 67, y: 54 },
        "VOL2": { x: 33, y: 54 },
        "RAM":  { x: 80, y: 32 },
        "CAM":  { x: 50, y: 34 },
        "LAM":  { x: 20, y: 32 },
        "ST":   { x: 50, y: 14 }
    },
    "4-4-2": {
        "GK":  { x: 50, y: 92 },
        "RB":  { x: 85, y: 72 },
        "RCB": { x: 62, y: 74 },
        "LCB": { x: 38, y: 74 },
        "LB":  { x: 15, y: 72 },
        "RM":  { x: 85, y: 46 },
        "CM1": { x: 62, y: 48 },
        "CM2": { x: 38, y: 48 },
        "LM":  { x: 15, y: 46 },
        "ST1": { x: 65, y: 16 },
        "ST2": { x: 35, y: 16 }
    }
};

// Start initialization
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
});

// Initial Setup
async function initApp() {
    // Populate star background
    const starsContainer = document.querySelector(".stars-container");
    if (starsContainer) {
        for (let i = 0; i < 40; i++) {
            const star = document.createElement("div");
            star.style.position = "absolute";
            star.style.width = Math.random() * 2 + 1 + "px";
            star.style.height = star.style.width;
            star.style.left = Math.random() * 100 + "%";
            star.style.top = Math.random() * 100 + "%";
            star.style.backgroundColor = "#ffffff";
            star.style.opacity = Math.random() * 0.7 + 0.3;
            star.style.borderRadius = "50%";
            starsContainer.appendChild(star);
        }
    }

    // Load available players
    await loadPlayersList();
    
    // Trigger initial simulation to populate data
    await runSimulation();
}

// Setup all click and input handlers
function setupEventListeners() {
    // Dropdown Trigger Toggle
    injuryTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        const isOpen = selectWrapper.classList.toggle("open");
        injuryTrigger.setAttribute("aria-expanded", isOpen);
        playerSearch.focus();
    });

    // Keyboard navigation for Dropdown Trigger
    injuryTrigger.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            const isOpen = selectWrapper.classList.toggle("open");
            injuryTrigger.setAttribute("aria-expanded", isOpen);
            if (isOpen) playerSearch.focus();
        }
    });

    // Close Dropdown on outside click
    document.addEventListener("click", () => {
        selectWrapper.classList.remove("open");
        injuryTrigger.setAttribute("aria-expanded", "false");
    });

    // Search Player Filter
    playerSearch.addEventListener("input", (e) => {
        filterPlayersList(e.target.value);
    });

    // Prevent closing select when clicking inside the search bar or container
    document.querySelector(".custom-options").addEventListener("click", (e) => {
        e.stopPropagation();
    });

    // Range Slider Value update
    simSlider.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        simSliderValue.textContent = val.toLocaleString("pt-BR");
        simSlider.setAttribute("aria-valuetext", val.toLocaleString("pt-BR") + " simulações");
    });

    // Trigger Simulation
    runSimBtn.addEventListener("click", () => {
        runSimulation();
    });

    // Tactical Board Tabs
    document.getElementById("btn-tab-arsenal").addEventListener("click", (e) => {
        switchTacticalTab("Arsenal");
    });
    document.getElementById("btn-tab-psg").addEventListener("click", (e) => {
        switchTacticalTab("PSG");
    });
}

// Fetch lists of players from backend
async function loadPlayersList() {
    try {
        const res = await fetch("/api/players");
        if (!res.ok) throw new Error("Could not fetch players list");
        
        allPlayers = await res.json();
        renderDropdownOptions();
    } catch (err) {
        console.error("Error loading players list:", err);
    }
}

// Render Dropdown options dynamically based on groups
function renderDropdownOptions() {
    playersListOptions.innerHTML = "";
    
    // Group 1: Arsenal
    if (allPlayers.Arsenal && allPlayers.Arsenal.length > 0) {
        const header = document.createElement("div");
        header.className = "team-header-opt";
        header.textContent = "Arsenal";
        playersListOptions.appendChild(header);
        
        allPlayers.Arsenal.forEach(player => {
            if (!activeInjuries.includes(player.name)) {
                playersListOptions.appendChild(createPlayerOptionElement(player));
            }
        });
    }

    // Group 2: PSG
    if (allPlayers.PSG && allPlayers.PSG.length > 0) {
        const header = document.createElement("div");
        header.className = "team-header-opt";
        header.textContent = "Paris Saint-Germain";
        playersListOptions.appendChild(header);
        
        allPlayers.PSG.forEach(player => {
            if (!activeInjuries.includes(player.name)) {
                playersListOptions.appendChild(createPlayerOptionElement(player));
            }
        });
    }
}

// Helper to build a player element option
function createPlayerOptionElement(player) {
    const opt = document.createElement("div");
    opt.className = "player-option";
    opt.dataset.playerName = player.name;
    
    const img = document.createElement("img");
    img.className = "player-opt-photo";
    img.src = player.photo_url || "";
    img.alt = player.name;
    // Fallback if SofaScore image returns 403 or error
    img.onerror = () => {
        img.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><circle cx='12' cy='12' r='11' fill='%23222'/><text x='50%' y='65%' font-family='sans-serif' font-size='10' font-weight='bold' fill='%23555' text-anchor='middle'>?</text></svg>";
    };
    
    const name = document.createElement("span");
    name.textContent = player.name;
    
    opt.appendChild(img);
    opt.appendChild(name);
    
    // Option Click event to add player as desfalque
    opt.addEventListener("click", () => {
        addInjury(player.name);
        selectWrapper.classList.remove("open");
        playerSearch.value = "";
        filterPlayersList("");
    });
    
    return opt;
}

// Filter dropdown list based on search term
function filterPlayersList(query) {
    const term = query.toLowerCase().trim();
    const options = playersListOptions.querySelectorAll(".player-option");
    
    options.forEach(opt => {
        const name = opt.dataset.playerName.toLowerCase();
        if (name.includes(term)) {
            opt.style.display = "flex";
        } else {
            opt.style.display = "none";
        }
    });
}

// Add Injury and redraw lists
function addInjury(playerName) {
    if (!activeInjuries.includes(playerName)) {
        activeInjuries.push(playerName);
        renderActiveInjuries();
        renderDropdownOptions();
    }
}

// Remove Injury and redraw lists
function removeInjury(playerName) {
    activeInjuries = activeInjuries.filter(p => p !== playerName);
    renderActiveInjuries();
    renderDropdownOptions();
}

// Render active injury badges
function renderActiveInjuries() {
    activeInjuriesList.innerHTML = "";
    
    if (activeInjuries.length === 0) {
        activeInjuriesList.innerHTML = `<span class="no-injuries-placeholder">Nenhum jogador indisponível. Todos estão aptos a jogar!</span>`;
        return;
    }
    
    activeInjuries.forEach(name => {
        const badge = document.createElement("div");
        badge.className = "injury-badge";
        badge.innerHTML = `
            <span>${name}</span>
            <span class="remove-btn">&times;</span>
        `;
        badge.addEventListener("click", () => {
            removeInjury(name);
        });
        activeInjuriesList.appendChild(badge);
    });
}

// Call Api /api/simulate to calculate Monte Carlo
async function runSimulation() {
    // Show Load overlay
    loadingOverlay.classList.add("show");
    runSimBtn.disabled = true;
    runSimBtn.querySelector(".btn-text").textContent = "SIMULANDO...";
    runSimBtn.querySelector(".loader-spinner").classList.remove("hidden");
    
    try {
        const response = await fetch("/api/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                desfalques: activeInjuries,
                simulacoes: parseInt(simSlider.value)
            })
        });
        
        if (!response.ok) throw new Error("Simulation error");
        
        const data = await response.json();
        currentSimulationData = data;
        
        // Render all dashboard modules
        updateDashboardData(data);
        
    } catch (err) {
        console.error("Simulation failed:", err);
        alert("Erro ao executar a simulação. Certifique-se de que o backend está ativo.");
    } finally {
        // Hide loader overlay
        loadingOverlay.classList.remove("show");
        runSimBtn.disabled = false;
        runSimBtn.querySelector(".btn-text").textContent = "INICIAR SIMULAÇÃO";
        runSimBtn.querySelector(".loader-spinner").classList.add("hidden");
    }
}

// Switch between Arsenal and PSG visual lineups
function switchTacticalTab(team) {
    activeTeamTab = team;
    document.getElementById("btn-tab-arsenal").classList.toggle("active", team === "Arsenal");
    document.getElementById("btn-tab-psg").classList.toggle("active", team === "PSG");
    
    if (currentSimulationData) {
        renderTacticalPitch(currentSimulationData);
    }
}

// Main logic to update DOM with returned JSON data
function updateDashboardData(data) {
    // Team names
    document.getElementById("label-team-a").textContent = data.time_a;
    document.getElementById("label-team-b").textContent = data.time_b;
    
    // Victory Probability segment sizes
    const probA = data.probabilidades.a;
    const probDraw = data.probabilidades.empate;
    const probB = data.probabilidades.b;
    
    const barA = document.getElementById("bar-prob-a");
    const barDraw = document.getElementById("bar-prob-draw");
    const barB = document.getElementById("bar-prob-b");
    
    barA.style.width = `${probA}%`;
    barA.querySelector(".segment-pct").textContent = `${probA.toFixed(2)}%`;
    
    barDraw.style.width = `${probDraw}%`;
    barDraw.querySelector(".segment-pct").textContent = `${probDraw.toFixed(2)}%`;
    
    barB.style.width = `${probB}%`;
    barB.querySelector(".segment-pct").textContent = `${probB.toFixed(2)}%`;
    
    // Quick Stats Highlight
    document.getElementById("stat-most-probable-score").textContent = data.placar_mais_comum;
    
    const favText = data.favorito === "Nenhum" ? "Empate" : (data.favorito === "Arsenal" ? "Arsenal" : "PSG");
    const favValueEl = document.getElementById("stat-fav-team");
    favValueEl.textContent = favText;
    
    // Set color based on favorite
    favValueEl.className = "stat-value";
    if (data.favorito === "Arsenal") {
        favValueEl.classList.add("neon-green");
    } else if (data.favorito === "Paris Saint-Germain") {
        favValueEl.classList.add("neon-blue");
    } else {
        favValueEl.classList.add("neon-white");
    }
    
    document.getElementById("stat-fav-chance").textContent = `chance de ${data.favorito_chance.toFixed(2)}%`;
    
    // Expected Goals (xG) Text
    document.getElementById("stat-expected-goals").textContent = `PSG ${data.medias_gols.a.toFixed(2)} | ARS ${data.medias_gols.b.toFixed(2)}`;
    
    // Knockout scenario Details
    document.getElementById("stat-k-overtime").textContent = data.mata_mata.prorrogacao || "N/A";
    
    const penWinner = data.mata_mata.penaltis || "N/A";
    const penEl = document.getElementById("stat-k-penalties");
    penEl.textContent = penWinner;
    penEl.className = "k-value";
    if (penWinner === "Arsenal") {
        penEl.classList.add("neon-green");
    } else if (penWinner === "Paris Saint-Germain") {
        penEl.classList.add("neon-blue");
    } else {
        penEl.classList.add("neon-white");
    }
    
    document.getElementById("stat-forces-detail").innerHTML = `
        ${data.time_a}: ATK ${data.forcas.a.atk.toFixed(2)} | DEF ${data.forcas.a.def.toFixed(2)} <br>
        ${data.time_b}: ATK ${data.forcas.b.atk.toFixed(2)} | DEF ${data.forcas.b.def.toFixed(2)}
    `;
    // Leadership in Match
    if (data.lideranca) {
        document.getElementById("lead-psg-pct").textContent = data.lideranca.psg.toFixed(2) + "%";
        document.getElementById("lead-arsenal-pct").textContent = data.lideranca.arsenal.toFixed(2) + "%";
        document.getElementById("lead-nenhum-pct").textContent = data.lideranca.nenhum.toFixed(2) + "%";
    }

    // First Goal of Match
    if (data.primeiro_gol) {
        document.getElementById("first-psg-pct").textContent = data.primeiro_gol.psg.toFixed(2) + "%";
        document.getElementById("first-arsenal-pct").textContent = data.primeiro_gol.arsenal.toFixed(2) + "%";
        document.getElementById("first-semgol-pct").textContent = data.primeiro_gol.sem_gol.toFixed(2) + "%";
    }

    // Render Lists: Scorers and Assisters
    renderProbabilitiesList("scorers-list", data.artilheiros, "green");
    renderProbabilitiesList("assisters-list", data.assistentes, "blue");

    // Render Chart: Exact Scores
    renderExactScoresChart(data.placares_provaveis);
    
    // Render Pitch Tactical Formations
    renderTacticalPitch(data);
}

// Render Scorers & Assisters List with custom styles
function renderProbabilitiesList(containerId, listData, colorType) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";
    
    if (!listData || listData.length === 0) {
        container.innerHTML = `<span class="no-injuries-placeholder">Sem estatísticas disponíveis.</span>`;
        return;
    }
    
    listData.slice(0, 5).forEach((item, index) => {
        const card = document.createElement("div");
        card.className = "probability-item";
        
        const photoUrl = item.info?.photo_url || "";
        
        card.innerHTML = `
            <span class="item-rank">#${index + 1}</span>
            <img class="item-avatar" src="${photoUrl}" alt="${item.jogador}" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'32\\' height=\\'32\\' viewBox=\\'0 0 32 32\\'><circle cx=\\'16\\' cy=\\'16\\' r=\\'15\\' fill=\\'%23222\\'/><text x=\\'50%\\' y=\\'60%\\' font-family=\\'sans-serif\\' font-size=\\'12\\' font-weight=\\'bold\\' fill=\\'%23555\\' text-anchor=\\'middle\\'>?</text></svg>'">
            <div class="item-info">
                <span class="item-name">${item.jogador}</span>
                <div class="item-bar-bg">
                    <div class="item-bar-fill" style="width: ${Math.min(100, item.prob * 5)}%;"></div>
                </div>
            </div>
            <span class="item-pct">${item.prob.toFixed(2)}%</span>
        `;
        
        // Add color segment class to item bar fill
        card.querySelector(".item-bar-fill").style.backgroundColor = colorType === "green" ? "var(--color-green)" : "var(--color-blue)";
        if (colorType === "green") {
            card.querySelector(".item-bar-fill").style.boxShadow = "0 0 5px var(--color-green-glow)";
        } else {
            card.querySelector(".item-bar-fill").style.boxShadow = "0 0 5px var(--color-blue-glow)";
        }
        
        container.appendChild(card);
    });
}

// Chart.js Horizontal Bar Chart implementation
function renderExactScoresChart(scoresData) {
    const ctx = document.getElementById("scoresChart").getContext("2d");
    
    const labels = scoresData.map(item => item.placar);
    const probabilities = scoresData.map(item => item.prob);
    
    // Destroy previous instance to avoid layout overlays
    if (scoresChart) {
        scoresChart.destroy();
    }
    
    Chart.defaults.color = "#7F869B";
    Chart.defaults.font.family = "'Inter', sans-serif";
    
    scoresChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Probabilidade (%)",
                data: probabilities,
                backgroundColor: (context) => {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    if (!chartArea) return null;
                    
                    // Create dynamic color gradient (green to blue) matching brand style
                    const gradient = ctx.createLinearGradient(0, 0, chartArea.right, 0);
                    gradient.addColorStop(0, "rgba(37, 89, 237, 0.85)"); // Blue
                    gradient.addColorStop(1, "rgba(162, 255, 1, 0.9)");  // Neon green
                    return gradient;
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
                    backgroundColor: "rgba(15, 16, 21, 0.95)",
                    titleFont: { size: 13, weight: "bold", family: "'Outfit', sans-serif" },
                    bodyFont: { size: 12 },
                    borderColor: "rgba(255, 255, 255, 0.1)",
                    borderWidth: 1,
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        label: (context) => `Chance de ${context.raw.toFixed(2)}%`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.03)" },
                    ticks: {
                        callback: (value) => `${value}%`
                    }
                },
                y: {
                    grid: { display: false }
                }
            }
        }
    });
}

// Tradução de posições do inglês para português do Brasil
function traduzirPosicao(slot) {
    const base = slot.replace(/\d+/g, "").toUpperCase();
    const mapa = {
        "GK": "GOL",
        "RB": "LD",
        "LB": "LE",
        "RCB": "ZGD",
        "LCB": "ZGE",
        "VOL": "VOL",
        "CM": "MC",
        "CAM": "MEI",
        "LM": "ME",
        "RM": "MD",
        "RW": "PD",
        "RAM": "PD",
        "LW": "PE",
        "LAM": "PE",
        "ST": "ATA"
    };
    return mapa[base] || base;
}

// Drawing players on visual canvas pitch
function renderTacticalPitch(data) {
    const overlay = document.getElementById("pitch-players-overlay");
    const formationBadge = document.getElementById("current-pitch-formation");
    overlay.innerHTML = "";
    
    // Get correct tactical formation and squad list depending on selection
    const isArsenal = activeTeamTab === "Arsenal";
    const formation = isArsenal ? data.formacao_b : data.formacao_a;
    const lineup = isArsenal ? data.escalacao_b : data.escalacao_a;
    
    formationBadge.textContent = formation;
    
    // Check if coordinates exist for this formation. Fallback to 4-3-3 if none found.
    const coordinates = POSITION_COORDINATES[formation] || POSITION_COORDINATES["4-3-3"];
    
    // Draw each starting 11 player on the field
    lineup.forEach((player, index) => {
        const slot = player.slot;
        const name = player.name;
        const photoUrl = player.info?.photo_url || "";
        const playerSofaId = player.info?.id || null;
        
        // Get preset positions
        const coord = coordinates[slot] || { x: 50, y: 50 };
        
        // Create tactical circle element
        const playerNode = document.createElement("div");
        playerNode.className = `pitch-player ${isArsenal ? "team-a" : "team-b"}`;
        playerNode.style.left = `${coord.x}%`;
        playerNode.style.top = `${coord.y}%`;
        
        // Circle structure
        const avatarWrapper = document.createElement("div");
        avatarWrapper.className = "player-avatar-wrapper";
        
        if (photoUrl) {
            const img = document.createElement("img");
            img.className = "player-img";
            img.src = photoUrl;
            img.alt = name;
            img.onerror = () => {
                img.style.display = "none";
                avatarWrapper.innerHTML = `<span class="player-img-placeholder">${name.substring(0, 2).toUpperCase()}</span>`;
            };
            avatarWrapper.appendChild(img);
        } else {
            avatarWrapper.innerHTML = `<span class="player-img-placeholder">${name.substring(0, 2).toUpperCase()}</span>`;
        }
        
        // Player name text label below card
        const nameLabel = document.createElement("span");
        nameLabel.className = "player-name-lbl";
        // Extract surname for better display
        const nameParts = name.split(" ");
        const displayName = nameParts.length > 1 ? nameParts[nameParts.length - 1] : name;
        nameLabel.textContent = displayName;
        
        playerNode.appendChild(avatarWrapper);
        playerNode.appendChild(nameLabel);
        
        // Show tooltip on Hover
        playerNode.addEventListener("mouseenter", (e) => {
            showPlayerTooltip(e, player, isArsenal);
        });
        
        playerNode.addEventListener("mouseleave", () => {
            hidePlayerTooltip();
        });
        
        overlay.appendChild(playerNode);
    });
}

// Display customized visual tooltips on hover
function showPlayerTooltip(e, player, isArsenal) {
    const tooltip = document.getElementById("pitch-tooltip");
    
    // Find goal/assist probability from the simulated results lists
    let goalChance = 0;
    let assistChance = 0;
    
    if (currentSimulationData) {
        const goalMatch = currentSimulationData.artilheiros.find(item => item.jogador === player.name);
        if (goalMatch) goalChance = goalMatch.prob;
        
        const assistMatch = currentSimulationData.assistentes.find(item => item.jogador === player.name);
        if (assistMatch) assistChance = assistMatch.prob;
    }
    
    tooltip.innerHTML = `
        <div class="tooltip-title">${player.name}</div>
        <div class="tooltip-row">
            <span>Posição:</span>
            <span class="tooltip-val" style="color: ${isArsenal ? "var(--color-green)" : "var(--color-blue)"}">${traduzirPosicao(player.slot)}</span>
        </div>
        <div class="tooltip-row">
            <span>Probabilidade Gol:</span>
            <span class="tooltip-val neon-white">${goalChance.toFixed(2)}%</span>
        </div>
        <div class="tooltip-row">
            <span>Probabilidade Assist:</span>
            <span class="tooltip-val neon-white">${assistChance.toFixed(2)}%</span>
        </div>
    `;
    
    tooltip.classList.add("show");
    
    // Position the tooltip near the cursor
    updateTooltipPosition(e);
    
    // Bind mousemove to follow cursor
    e.currentTarget.addEventListener("mousemove", updateTooltipPosition);
}

function hidePlayerTooltip() {
    const tooltip = document.getElementById("pitch-tooltip");
    tooltip.classList.remove("show");
}

function updateTooltipPosition(e) {
    const tooltip = document.getElementById("pitch-tooltip");
    const x = e.clientX + 15;
    const y = e.clientY + 15;
    
    // Prevent tooltip from overflowing the viewport
    const tooltipWidth = tooltip.offsetWidth;
    const tooltipHeight = tooltip.offsetHeight;
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    
    let adjustedX = x;
    let adjustedY = y;
    
    if (x + tooltipWidth > windowWidth) {
        adjustedX = e.clientX - tooltipWidth - 15;
    }
    
    if (y + tooltipHeight > windowHeight) {
        adjustedY = e.clientY - tooltipHeight - 15;
    }
    
    tooltip.style.left = `${adjustedX}px`;
    tooltip.style.top = `${adjustedY}px`;
}
