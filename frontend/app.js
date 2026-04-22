const API_BASE = "";

// ── Utilidades ──

function formatNumber(n) {
    if (!n && n !== 0) return "—";
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "K";
    return n.toLocaleString("es-EC");
}

function proxyUrl(url) {
    if (!url) return "";
    return `${API_BASE}/proxy/image?url=${encodeURIComponent(url)}`;
}

function showError(msg) {
    const box = document.getElementById("errorBox");
    document.getElementById("errorText").textContent = msg;
    box.style.display = "flex";
    setTimeout(() => (box.style.display = "none"), 6000);
}

function hideError() {
    document.getElementById("errorBox").style.display = "none";
}

function setLoader(active, text = "Procesando...") {
    const loader = document.getElementById("loader");
    const loaderText = document.getElementById("loaderText");
    loaderText.textContent = text;
    loader.classList.toggle("active", active);
}

function setBtnLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    if (btnId === "authBtn") {
        btn.querySelector(".btn-text").textContent = loading ? "Autenticando..." : "Autenticar";
    }
}

// ── Estado de autenticación ──

async function checkAuthStatus() {
    try {
        const res = await fetch(`${API_BASE}/auth/status`);
        const data = await res.json();
        const dot = document.getElementById("statusDot");
        const text = document.getElementById("statusText");

        if (data.authenticated) {
            dot.className = "status-dot active";
            text.textContent = "Sesión activa";
            document.getElementById("authPanel").style.opacity = "0.5";
        } else {
            dot.className = "status-dot inactive";
            text.textContent = "Sin sesión";
        }
    } catch {
        document.getElementById("statusText").textContent = "API no disponible";
    }
}

// ── Autenticación ──

async function doAuth() {
    setBtnLoading("authBtn", true);
    hideError();

    try {
        const res = await fetch(`${API_BASE}/auth`, {
            method: "POST",
        });

        const data = await res.json();

        if (!res.ok) {
            showError(data.detail || "Error de autenticación.");
            return;
        }

        // Éxito
        document.getElementById("statusDot").className = "status-dot active";
        document.getElementById("statusText").textContent = "Sesión activa";
        document.getElementById("authPanel").style.opacity = "0.5";

        alert("✓ Autenticación exitosa. Ahora puedes extraer perfiles.");
    } catch (err) {
        showError("No se pudo conectar con el servidor. ¿Está corriendo el backend?");
    } finally {
        setBtnLoading("authBtn", false);
    }
}

// ── Scraping ──

async function doScrape() {
    const username = document.getElementById("targetUser").value.trim().replace(/^@/, "");

    if (!username) {
        showError("Ingresa un nombre de usuario.");
        return;
    }

    hideError();
    document.getElementById("results").style.display = "none";
    setLoader(true, "Navegando al perfil de @" + username + "...");
    document.getElementById("scrapeBtn").disabled = true;

    try {
        const steps = [
            "Cargando sesión guardada...",
            "Abriendo Playwright...",
            "Aceptando cookies de Instagram...",
            "Extrayendo datos del perfil...",
            "Obteniendo publicaciones recientes...",
        ];
        let stepIdx = 0;
        const stepInterval = setInterval(() => {
            stepIdx = (stepIdx + 1) % steps.length;
            setLoader(true, steps[stepIdx]);
        }, 2000);

        const res = await fetch(`${API_BASE}/scrape`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username }),
        });

        clearInterval(stepInterval);
        const body = await res.json();

        if (!res.ok) {
            showError(body.detail || "Error al extraer datos.");
            return;
        }

        renderResults(body.data);
    } catch (err) {
        showError("No se pudo conectar con el servidor. ¿Está corriendo el backend?");
    } finally {
        setLoader(false);
        document.getElementById("scrapeBtn").disabled = false;
    }
}

// ── Renderizado de resultados ──

function renderResults(data) {
    const container = document.getElementById("results");

    // Username y nombre
    document.getElementById("profileUsername").textContent = "@" + data.username;
    document.getElementById("profileName").textContent = data.full_name || "";
    document.getElementById("profileBio").textContent = data.bio || "";

    // Verificado
    const badge = document.getElementById("verifiedBadge");
    badge.style.display = data.is_verified ? "block" : "none";

    // Stats
    document.getElementById("statFollowers").textContent = formatNumber(data.followers);
    document.getElementById("statFollowing").textContent = formatNumber(data.following);
    document.getElementById("statPosts").textContent = formatNumber(data.posts_count);

    // Posts
    const grid = document.getElementById("postsGrid");
    grid.innerHTML = "";

    const posts = data.recent_posts || [];
    document.getElementById("postsCountLabel").textContent = `${posts.length} encontradas`;

    posts.forEach((post, idx) => {
        const item = document.createElement("div");
        item.className = "post-item";
        item.style.animationDelay = `${idx * 0.04}s`;

        const img = document.createElement("img");
        img.src = proxyUrl(post.thumbnail_url);
        img.alt = post.alt_text || `Post ${idx + 1}`;
        img.loading = "lazy";
        img.onerror = () => {
            item.style.background = "#1a1a1a";
            img.style.display = "none";
        };

        const overlay = document.createElement("div");
        overlay.className = "post-overlay";
        overlay.innerHTML = `<span class="post-overlay-icon">↗</span>`;
        overlay.onclick = () => window.open(post.post_url, "_blank");

        item.appendChild(img);
        item.appendChild(overlay);
        item.onclick = () => window.open(post.post_url, "_blank");
        grid.appendChild(item);
    });

    // JSON completo
    document.getElementById("jsonOutput").textContent = JSON.stringify(data, null, 2);

    // Mostrar resultados
    container.style.display = "block";
    container.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Toggle JSON ──

function toggleJSON() {
    const out = document.getElementById("jsonOutput");
    out.style.display = out.style.display === "none" ? "block" : "none";
}

// ── Download Data ──
function downloadData() {
    const out = document.getElementById("jsonOutput").textContent;
    if (!out) {
        alert("No hay datos para descargar");
        return;
    }
    try {
        const data = JSON.parse(out);
        const username = data.username || "perfil";
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `instagram_${username}_data.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (e) {
        alert("Error al descargar los datos");
    }
}

// ── Init ──

document.addEventListener("DOMContentLoaded", () => {
    checkAuthStatus();

    // (Eliminados los event listeners de igUser e igPass)
});