// ISO 3166-1 alpha-2 codes for flagcdn.com
const FLAG_CODES = {
    "Brazil": "br", "Argentina": "ar", "France": "fr", "Germany": "de",
    "Spain": "es", "England": "gb-eng", "Portugal": "pt", "Netherlands": "nl",
    "Belgium": "be", "Uruguay": "uy", "Italy": "it", "Croatia": "hr",
    "Colombia": "co", "Mexico": "mx", "USA": "us", "United States": "us", "Canada": "ca",
    "Morocco": "ma", "Japan": "jp", "South Korea": "kr", "Senegal": "sn",
    "Ecuador": "ec", "Switzerland": "ch", "Denmark": "dk", "Poland": "pl",
    "Australia": "au", "Serbia": "rs", "Cameroon": "cm", "Ghana": "gh",
    "Tunisia": "tn", "Qatar": "qa", "Saudi Arabia": "sa", "Iran": "ir",
    "Wales": "gb-wls", "Czechia": "cz", "Hungary": "hu", "Türkiye": "tr",
    "Turkey": "tr", "Ukraine": "ua", "Chile": "cl", "Peru": "pe",
    "Bolivia": "bo", "Paraguay": "py", "Venezuela": "ve", "Costa Rica": "cr",
    "Panama": "pa", "Jamaica": "jm", "Honduras": "hn", "El Salvador": "sv",
    "Algeria": "dz", "Egypt": "eg", "Nigeria": "ng", "Ivory Coast": "ci",
    "Côte d'Ivoire": "ci", "Mali": "ml", "DR Congo": "cd", "Congo DR": "cd", "South Africa": "za", 
    "Kenya": "ke", "Guinea": "gn", "Iraq": "iq", "Uzbekistan": "uz", "New Zealand": "nz",
    "Norway": "no", "Sweden": "se", "Austria": "at", "Scotland": "gb-sct",
    "Slovakia": "sk", "Romania": "ro", "Georgia": "ge", "Albania": "al",
    "Cuba": "cu", "Trinidad and Tobago": "tt", "Curaçao": "cw",
    "Guatemala": "gt", "Dominican Republic": "do", "Haiti": "ht",
    "Suriname": "sr", "Guyana": "gy", "Nicaragua": "ni", "Bermuda": "bm",
    "Israel": "il", "Greece": "gr", "Finland": "fi", "Iceland": "is",
    "Kosovo": "xk", "North Macedonia": "mk", "Bosnia-Herzegovina": "ba", "Bosnia & Herzegovina": "ba",
    "Montenegro": "me", "Armenia": "am", "Azerbaijan": "az",
    "Kazakhstan": "kz", "Kyrgyzstan": "kg", "Tajikistan": "tj",
    "Turkmenistan": "tm", "India": "in", "China": "cn", "Thailand": "th",
    "Vietnam": "vn", "Philippines": "ph", "Indonesia": "id", "Myanmar": "mm",
    "Singapore": "sg", "Malaysia": "my", "Lebanon": "lb", "Jordan": "jo",
    "Syria": "sy", "Palestine": "ps", "Bahrain": "bh", "Kuwait": "kw",
    "Oman": "om", "Yemen": "ye", "Libya": "ly", "Sudan": "sd",
    "Ethiopia": "et", "Tanzania": "tz", "Uganda": "ug", "Rwanda": "rw",
    "Zimbabwe": "zw", "Zambia": "zm", "Mozambique": "mz", "Angola": "ao",
    "Cape Verde": "cv", "Cabo Verde": "cv", "Benin": "bj", "Burkina Faso": "bf", "Congo": "cg",
    "Mauritania": "mr", "Niger": "ne", "Togo": "tg", "Gabon": "ga",
    "Equatorial Guinea": "gq", "Liberia": "lr", "Sierra Leone": "sl",
    "Guinea-Bissau": "gw", "Gambia": "gm", "New Caledonia": "nc", 
    "Fiji": "fj", "Papua New Guinea": "pg", "Tahiti": "pf", "Vanuatu": "vu", 
    "Solomon Islands": "sb"
};

const PT_NAMES = {
    "Brazil": "Brasil", "Argentina": "Argentina", "France": "França", "Germany": "Alemanha",
    "Spain": "Espanha", "England": "Inglaterra", "Portugal": "Portugal", "Netherlands": "Holanda",
    "Belgium": "Bélgica", "Uruguay": "Uruguai", "Italy": "Itália", "Croatia": "Croácia",
    "Colombia": "Colômbia", "Mexico": "México", "USA": "Estados Unidos", "United States": "Estados Unidos", "Canada": "Canadá",
    "Morocco": "Marrocos", "Japan": "Japão", "South Korea": "Coreia do Sul", "Senegal": "Senegal",
    "Ecuador": "Equador", "Switzerland": "Suíça", "Denmark": "Dinamarca", "Poland": "Polônia",
    "Australia": "Austrália", "Serbia": "Sérvia", "Cameroon": "Camarões", "Ghana": "Gana",
    "Tunisia": "Tunísia", "Qatar": "Catar", "Saudi Arabia": "Arábia Saudita", "Iran": "Irã",
    "Wales": "País de Gales", "Czechia": "República Tcheca", "Hungary": "Hungria", "Türkiye": "Turquia",
    "Turkey": "Turquia", "Ukraine": "Ucrânia", "Chile": "Chile", "Peru": "Peru",
    "Bolivia": "Bolívia", "Paraguay": "Paraguai", "Venezuela": "Venezuela", "Costa Rica": "Costa Rica",
    "Panama": "Panamá", "Jamaica": "Jamaica", "Honduras": "Honduras", "El Salvador": "El Salvador",
    "Algeria": "Argélia", "Egypt": "Egito", "Nigeria": "Nigéria", "Ivory Coast": "Costa do Marfim",
    "Côte d'Ivoire": "Costa do Marfim", "Mali": "Mali", "DR Congo": "RD Congo", "Congo DR": "RD Congo",
    "South Africa": "África do Sul", "New Zealand": "Nova Zelândia", "Norway": "Noruega", "Sweden": "Suécia", 
    "Austria": "Áustria", "Scotland": "Escócia", "Slovakia": "Eslováquia", "Romania": "Romênia", "Georgia": "Geórgia", 
    "Albania": "Albânia", "Cuba": "Cuba", "Trinidad and Tobago": "Trinidad e Tobago", 
    "Curaçao": "Curaçau", "Guatemala": "Guatemala", "Haiti": "Haiti",
    "Bosnia-Herzegovina": "Bósnia e Herzegovina", "Bosnia & Herzegovina": "Bósnia e Herzegovina",
    "Oman": "Omã", "Cabo Verde": "Cabo Verde", "Cape Verde": "Cabo Verde"
};

function t(name) {
    return PT_NAMES[name] || name;
}

function getFlag(team, size = 30) {
    if (team === "—" || !team) return `<div class="empty-flag" style="width:${size}px;height:${size}px;"></div>`;
    const code = FLAG_CODES[team];
    if (!code) return `<div class="empty-flag" style="width:${size}px;height:${size}px;"></div>`;
    return `<img src="https://flagcdn.com/w40/${code}.png"
                 alt="${team}" loading="lazy"
                 class="circle-flag"
                 style="width:${size}px;height:${size}px;">`;
}

// ── CSV loader (PapaParse) ───────────────────────────────────────────────────
async function loadCSV(path) {
    try {
        const res = await fetch(path);
        if (!res.ok) throw new Error("not found");
        const text = await res.text();
        return new Promise(resolve => {
            Papa.parse(text, {
                header: true, dynamicTyping: true, skipEmptyLines: true,
                complete: r => resolve(r.data)
            });
        });
    } catch (e) {
        console.warn(`Não foi possível carregar ${path}. Use Live Server ou servidor local.`);
        return [];
    }
}

// ── SECTION 1 — Favorites Podium ─────────────────────────────────────────────
function renderFavorites(data) {
    const el = document.getElementById("favorites-podium");
    el.innerHTML = "";
    data.slice(0, 5).forEach((row, i) => {
        const pct = Number(row["Campeão (%)"]).toFixed(2);
        const rank = i + 1;
        const cls = rank === 1 ? "rank-1" : rank === 2 ? "rank-2" : rank === 3 ? "rank-3" : "";
        el.innerHTML += `
        <div class="fav-card ${cls}">
            <div class="fav-rank">#${rank}</div>
            <div class="fav-team">${getFlag(row["Seleção"], 40)} ${t(row["Seleção"])}</div>
            <div class="fav-pct">${pct}%</div>
            <div class="fav-pct-label">Chance de Título</div>
        </div>`;
    });
}

// ── SECTION 2 — Knockout Bracket (tree - Split Layout) ──────────────────────
function renderBracket(data) {
    const el = document.getElementById("bracket-wrapper");
    el.innerHTML = "";

    // Helper: avança o time que tiver a maior chance geral de título
    function pickWinners(matches) {
        return matches.map(([a, b]) => {
            const pA = (data.find(r => r["Seleção"] === a) || {})["Campeão (%)"] || 0;
            const pB = (data.find(r => r["Seleção"] === b) || {})["Campeão (%)"] || 0;
            return pA >= pB ? a : b;
        });
    }

    // Fixed 16-avos (Round of 32)
    // Conforme o chaveamento definido (8 jogos na Esquerda, 8 jogos na Direita)
    const r32L = [
        ['Germany',       'Paraguay'],
        ['France',        'Sweden'],
        ['South Africa',  'Canada'],
        ['Netherlands',   'Morocco'],
        ['Portugal',      'Croatia'],
        ['Spain',         'Austria'],
        ['United States', 'Bosnia-Herzegovina'],
        ['Belgium',       'Senegal']
    ];

    const r32R = [
        ['Brazil',        'Japan'],
        ['Ivory Coast',   'Norway'],
        ['Mexico',        'Ecuador'],
        ['England',       'Congo DR'],
        ['Argentina',     'Cape Verde'],
        ['Australia',     'Egypt'],
        ['Switzerland',   'Algeria'],
        ['Colombia',      'Ghana']
    ];

    function resolveRounds(r32) {
        const r16 = [];
        const r32_w = pickWinners(r32);
        for(let i=0; i<r32_w.length; i+=2) r16.push([r32_w[i], r32_w[i+1]]);
        
        const qf = [];
        const r16_w = pickWinners(r16);
        for(let i=0; i<r16_w.length; i+=2) qf.push([r16_w[i], r16_w[i+1]]);
        
        const sf = [];
        const qf_w = pickWinners(qf);
        for(let i=0; i<qf_w.length; i+=2) sf.push([qf_w[i], qf_w[i+1]]);
        
        const finalist = pickWinners(sf)[0];
        return { r16, qf, sf, finalist };
    }

    const resL = resolveRounds(r32L);
    const resR = resolveRounds(r32R);
    const champion = pickWinners([[resL.finalist, resR.finalist]])[0];

    function createMatch(a, b, winners, isRightSide = false) {
        const m = document.createElement("div");
        m.className = "bracket-match";
        const wA = winners.includes(a);
        const wB = winners.includes(b);
        const reverseStyle = isRightSide ? 'style="flex-direction:row-reverse;text-align:right;"' : '';
        m.innerHTML = `
            <div class="bracket-team ${wA ? "winner" : ""}" ${reverseStyle}>
                <span class="bracket-team-flag">${getFlag(a)}</span><span class="truncate" style="flex:1">${t(a)}</span>
            </div>
            <div class="bracket-team ${wB ? "winner" : ""}" ${reverseStyle}>
                <span class="bracket-team-flag">${getFlag(b)}</span><span class="truncate" style="flex:1">${t(b)}</span>
            </div>
        `;
        return m;
    }

    function buildHalfCol(matches, winners, isRightSide = false) {
        const col = document.createElement("div");
        col.className = "bracket-col";
        matches.forEach(match => {
            const m = document.createElement("div");
            m.className = "match-container";
            if (isRightSide) {
                const conn = document.createElement("div");
                conn.className = "connector";
                m.appendChild(conn);
                m.appendChild(createMatch(match[0], match[1], winners, true));
            } else {
                m.appendChild(createMatch(match[0], match[1], winners, false));
                const conn = document.createElement("div");
                conn.className = "connector";
                m.appendChild(conn);
            }
            col.appendChild(m);
        });
        return col;
    }

    const bracket = document.createElement("div");
    bracket.className = "split-bracket";

    const leftSide = document.createElement("div");
    leftSide.className = "bracket-side left-side";
    leftSide.appendChild(buildHalfCol(r32L, pickWinners(r32L), false));
    leftSide.appendChild(buildHalfCol(resL.r16, pickWinners(resL.r16), false));
    leftSide.appendChild(buildHalfCol(resL.qf, pickWinners(resL.qf), false));
    leftSide.appendChild(buildHalfCol(resL.sf, pickWinners(resL.sf), false));

    const center = document.createElement("div");
    center.className = "bracket-center";
    center.innerHTML = `
        <div class="final-match-title">MATA-MATA</div>
        <div class="champion-trophy-large">🏆</div>
        <div class="final-match">
            <div class="bracket-team ${champion === resL.finalist ? "winner" : ""}">
                <span class="bracket-team-flag">${getFlag(resL.finalist, 40)}</span><b>${t(resL.finalist)}</b>
            </div>
            <div class="vs-badge">X</div>
            <div class="bracket-team ${champion === resR.finalist ? "winner" : ""}">
                <span class="bracket-team-flag">${getFlag(resR.finalist, 40)}</span><b>${t(resR.finalist)}</b>
            </div>
        </div>
        <div class="champion-label">Campeão Previsto:</div>
        <div class="champion-name-large">${t(champion)}</div>
    `;

    const rightSide = document.createElement("div");
    rightSide.className = "bracket-side right-side";
    rightSide.appendChild(buildHalfCol(resR.sf, pickWinners(resR.sf), true));
    rightSide.appendChild(buildHalfCol(resR.qf, pickWinners(resR.qf), true));
    rightSide.appendChild(buildHalfCol(resR.r16, pickWinners(resR.r16), true));
    rightSide.appendChild(buildHalfCol(r32R, pickWinners(r32R), true));

    bracket.appendChild(leftSide);
    bracket.appendChild(center);
    bracket.appendChild(rightSide);

    el.appendChild(bracket);
}

// ── SECTION 3 — Player Golden Cards ──────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
    // Starfield setup
    const sc = document.querySelector(".stars-container");
    if (sc) {
        for (let i = 0; i < 60; i++) {
            const s = document.createElement("div");
            s.style.cssText = `position:absolute;border-radius:50%;background:#fff;
                width:${Math.random()*2+1}px;height:${Math.random()*2+1}px;
                left:${Math.random()*100}%;top:${Math.random()*100}%;
                opacity:${Math.random()*0.6+0.2}`;
            sc.appendChild(s);
        }
    }

    // Carregar arquivos CSV do mata-mata real (criados por prev_mata_mata_real.py)
    const [chances, artilheiros, assistentes] = await Promise.all([
        loadCSV("../outputs/mata_mata_real_chances.csv"),
        loadCSV("../outputs/mata_mata_real_artilheiros.csv"),
        loadCSV("../outputs/mata_mata_real_assistentes.csv")
    ]);

    if (chances.length) {
        renderFavorites(chances);
        renderBracket(chances);
    } else {
        document.getElementById("favorites-podium").innerHTML = "<div style='text-align:center;width:100%'>Erro ou aguardando os dados CSV do Mata-Mata...</div>";
    }
    
    if (artilheiros && artilheiros.length > 0) {
        const top = artilheiros[0];
        const match = top["Jogador"].match(/(.*?)\s*\((.*?)\)/);
        const name = match ? match[1] : top["Jogador"];
        const team = match ? match[2] : "";
        document.getElementById("golden-boot-card").innerHTML = `
            <div class="golden-icon">🎯</div>
            <div class="golden-title">Chuteira de Ouro</div>
            <div class="golden-name">${name}</div>
            <div class="golden-team">${getFlag(team, 24)} ${t(team)}</div>
            <div style="margin-top: 10px; font-size: 0.9rem; opacity: 0.8;">Gols Esperados (Copa): ${Math.ceil(Number(top["Média_Gols_Copa_Total"]))}</div>
        `;
    }
    
    if (assistentes && assistentes.length > 0) {
        const top = assistentes[0];
        const match = top["Jogador"].match(/(.*?)\s*\((.*?)\)/);
        const name = match ? match[1] : top["Jogador"];
        const team = match ? match[2] : "";
        document.getElementById("golden-playmaker-card").innerHTML = `
            <div class="golden-icon">👟</div>
            <div class="golden-title">Maior Assistente</div>
            <div class="golden-name">${name}</div>
            <div class="golden-team">${getFlag(team, 24)} ${t(team)}</div>
            <div style="margin-top: 10px; font-size: 0.9rem; opacity: 0.8;">Assistências (Copa): ${Math.ceil(Number(top["Média_Assists_Copa_Total"]))}</div>
        `;
    }
});
