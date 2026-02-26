// Mobile sidebar drawer
(() => {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const menuBtn = document.getElementById("menuBtn");
    const closeBtn = document.getElementById("closeBtn");

    function openMenu() {
        sidebar?.classList.add("open");
        overlay?.classList.add("open");
    }
    function closeMenu() {
        sidebar?.classList.remove("open");
        overlay?.classList.remove("open");
    }

    menuBtn?.addEventListener("click", openMenu);
    closeBtn?.addEventListener("click", closeMenu);
    overlay?.addEventListener("click", closeMenu);
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeMenu();
    });
})();


// Theme toggle (light/dark) using localStorage
(() => {
    const key = "career_os_theme";
    const btn = document.getElementById("themeToggle");

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        if (btn) btn.textContent = theme === "light" ? "☀️" : "🌙";
    }

    const saved = localStorage.getItem(key);
    if (saved === "light" || saved === "dark") applyTheme(saved);
    else applyTheme("light");

    btn?.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "light";
        const next = current === "dark" ? "light" : "dark";
        localStorage.setItem(key, next);
        applyTheme(next);
    });
})();


// Collapsible blocks for profile_form.html (matches your HTML)
(() => {
    document.addEventListener("click", (e) => {
        const toggle = e.target.closest("[data-toggle]");
        if (!toggle) return;

        const block = toggle.closest("[data-block]");
        if (!block) return;

        block.classList.toggle("open");
        toggle.textContent = block.classList.contains("open") ? "Hide" : "Show";
    });

    window.addEventListener("load", () => {
        const expandBtn = document.getElementById("expandAllBtn");
        const collapseBtn = document.getElementById("collapseAllBtn");

        expandBtn?.addEventListener("click", () => {
            document.querySelectorAll("[data-block]").forEach((b) => {
                b.classList.add("open");
                const t = b.querySelector("[data-toggle]");
                if (t) t.textContent = "Hide";
            });
        });

        collapseBtn?.addEventListener("click", () => {
            document.querySelectorAll("[data-block]").forEach((b) => {
                b.classList.remove("open");
                const t = b.querySelector("[data-toggle]");
                if (t) t.textContent = "Show";
            });
        });
    });
})();
