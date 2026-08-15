// Shared boilerplate for the secondary/account pages under frontend/pages/
// (fields, alerts, reports, billing, admin, ops). Not used by index.html or
// login.html. Depends on api.js / auth.js / i18n.js being loaded first.

(function () {
  "use strict";

  // ---- Theme ----------------------------------------------------------
  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("geointel_theme", theme);
    const sun = document.getElementById("themeSun");
    const moon = document.getElementById("themeMoon");
    if (sun && moon) {
      if (theme === "dark") {
        sun.style.display = "block";
        moon.style.display = "none";
      } else {
        sun.style.display = "none";
        moon.style.display = "block";
      }
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    setTheme(current === "dark" ? "light" : "dark");
  }

  function initTheme() {
    setTheme(window.localStorage.getItem("geointel_theme") || "light");
    const btn = document.getElementById("themeToggle");
    if (btn) btn.addEventListener("click", toggleTheme);
  }

  // ---- Language switch --------------------------------------------------
  function initLangSwitch() {
    document.querySelectorAll("[data-lang-btn]").forEach((btn) => {
      if (btn.dataset.langBtn === window.GeoIntelI18n.currentLang()) {
        btn.classList.add("active");
      }
      btn.addEventListener("click", () => {
        window.GeoIntelI18n.setLang(btn.dataset.langBtn);
        document.querySelectorAll("[data-lang-btn]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
      });
    });
  }

  // ---- Toast --------------------------------------------------------------
  let toastTimer = null;
  function showToast(message, isError) {
    const toast = document.getElementById("toast");
    const msg = document.getElementById("toastMsg");
    if (!toast || !msg) return;
    msg.textContent = message;
    toast.style.borderLeftColor = isError ? "#c62828" : "var(--accent-gold)";
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3800);
  }

  // ---- Auth-aware header ----------------------------------------------
  async function initAuthUI(onChange) {
    const box = document.getElementById("authBox");
    function render(user) {
      if (box) {
        if (user) {
          const label = user.email || user.displayName || "Account";
          box.innerHTML =
            '<span class="user-name" style="color:#fff;font-size:0.8rem;margin-right:0.5rem;">' +
            escapeHtml(label) +
            '</span><button class="header-btn" id="signOutBtn" data-i18n="nav.logout">Sign Out</button>';
          const signOutBtn = document.getElementById("signOutBtn");
          if (signOutBtn) {
            signOutBtn.addEventListener("click", async () => {
              await window.geointelAuth.signOutUser();
              window.location.reload();
            });
          }
        } else {
          box.innerHTML =
            '<a class="header-btn header-btn-gold" href="/pages/login.html" data-i18n="nav.login">Sign In</a>';
        }
        if (window.GeoIntelI18n) window.GeoIntelI18n.applyTranslations();
      }
      if (typeof onChange === "function") onChange(user);
    }
    await window.geointelAuth.ready;
    render(window.geointelAuth.currentUser);
    window.geointelAuth.onAuthChange(render);
  }

  function requireAuthOrPrompt() {
    const user = window.geointelAuth && window.geointelAuth.currentUser;
    if (!user) {
      showToast(window.GeoIntelI18n.t("auth.required"), true);
      return false;
    }
    return true;
  }

  // ---- Small utils --------------------------------------------------------
  function escapeHtml(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  function formatDateTime(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString(window.GeoIntelI18n.currentLang() === "en" ? "en-GB" : "ru-RU", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  function formatTiyin(amountTiyin) {
    const som = amountTiyin / 100;
    const somStr = som.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return `${somStr} сом (${amountTiyin.toLocaleString("ru-RU")} тыйын)`;
  }

  function severityClass(severity) {
    const s = (severity || "").toLowerCase();
    if (/(critical|danger|severe|extreme|high)/.test(s)) return "danger";
    if (/(warn|moderate|medium)/.test(s)) return "warning";
    return "info";
  }

  function statusBadgeClass(status) {
    const s = (status || "").toLowerCase();
    if (/(ok|success|paid|confirmed|optimal|active)/.test(s)) return "optimal";
    if (/(pending|issued|advisory|warn)/.test(s)) return "advisory";
    if (/(error|fail|stress|rejected|danger)/.test(s)) return "stress";
    return "advisory";
  }

  // ---- Sidebar active-link highlight --------------------------------------
  function markActiveNav(pageKey) {
    document.querySelectorAll("[data-nav-key]").forEach((el) => {
      el.classList.toggle("active", el.dataset.navKey === pageKey);
    });
  }

  window.GeoIntelPage = {
    initTheme,
    toggleTheme,
    initLangSwitch,
    showToast,
    initAuthUI,
    requireAuthOrPrompt,
    escapeHtml,
    formatDateTime,
    formatTiyin,
    severityClass,
    statusBadgeClass,
    markActiveNav,
  };
})();
