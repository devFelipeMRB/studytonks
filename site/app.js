"use strict";

(() => {
  const repository = "devFelipeMRB/studytonks";
  const releasesUrl = `https://github.com/${repository}/releases`;
  const latestDownloadPrefix = `https://github.com/${repository}/releases/latest/download/`;
  const releaseDownloadPrefix = `https://github.com/${repository}/releases/download/`;
  const installerName = "Studytonks-Setup.exe";
  const portableName = "Studytonks-Portable.zip";
  const installer = document.getElementById("installer-download");
  const installerLabel = document.getElementById("installer-label");
  const status = document.getElementById("release-status");
  const portable = document.getElementById("portable-download");
  const themeButton = document.getElementById("theme-toggle");
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  let chosenTheme = null;

  try {
    const saved = localStorage.getItem("studytonks-site-theme");
    if (saved === "light" || saved === "dark") chosenTheme = saved;
  } catch (_) {
    // The page remains usable when the browser denies local storage.
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    const label = theme === "dark" ? "Ativar tema claro" : "Ativar tema escuro";
    themeButton.setAttribute("aria-label", label);
    themeButton.title = label;
    document.querySelector('meta[name="theme-color"]').content = theme === "dark" ? "#151B25" : "#FAF9F6";
  }

  applyTheme(chosenTheme || (systemTheme.matches ? "dark" : "light"));
  themeButton.addEventListener("click", () => {
    chosenTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(chosenTheme);
    try {
      localStorage.setItem("studytonks-site-theme", chosenTheme);
    } catch (_) {
      // Theme preference is optional; no tracking or remote storage is used.
    }
  });
  systemTheme.addEventListener("change", (event) => {
    if (!chosenTheme) applyTheme(event.matches ? "dark" : "light");
  });

  function trustedDownload(url, filename) {
    if (typeof url !== "string") return false;
    try {
      const parsed = new URL(url);
      return parsed.protocol === "https:" && parsed.hostname === "github.com"
        && !parsed.username && !parsed.password && !parsed.search && !parsed.hash
        && (url.startsWith(latestDownloadPrefix) || url.startsWith(releaseDownloadPrefix))
        && parsed.pathname.endsWith(`/${filename}`);
    } catch (_) {
      return false;
    }
  }

  function showRelease(release) {
    if (!release || release.available !== true || !trustedDownload(release.installer_url, installerName)) return false;
    installer.href = release.installer_url;
    installerLabel.textContent = "Baixar instalador para Windows";
    installer.dataset.available = "true";
    const version = typeof release.version === "string" ? release.version.slice(0, 40) : "";
    status.textContent = `${version ? `${version} · ` : ""}Instalador disponível · dependências incluídas.`;
    if (trustedDownload(release.portable_url, portableName)) {
      portable.href = release.portable_url;
      portable.hidden = false;
    }
    return true;
  }

  async function getJson(url) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 4500);
    try {
      const response = await fetch(url, {
        signal: controller.signal,
        cache: "no-store",
        credentials: "omit",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return null;
      return await response.json();
    } catch (_) {
      return null;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function checkAvailability() {
    // CI writes this manifest only after publishing validated Windows artifacts.
    // Opening index.html directly may block this request; the public API is a fallback.
    const manifest = await getJson("release.json");
    if (showRelease(manifest)) return;
    const latest = await getJson(`https://api.github.com/repos/${repository}/releases/latest`);
    if (latest && latest.draft !== true && latest.prerelease !== true && Array.isArray(latest.assets)) {
      const asset = latest.assets.find((item) => item.name === installerName && item.state === "uploaded" && item.size > 0);
      const portableAsset = latest.assets.find((item) => item.name === portableName && item.state === "uploaded" && item.size > 0);
      if (asset && showRelease({
        available: true,
        version: latest.tag_name,
        installer_url: asset.browser_download_url,
        portable_url: portableAsset ? portableAsset.browser_download_url : null,
      })) return;
    }
    // A missing release, blocked request, or offline browser never enables a pretend download.
    installer.href = releasesUrl;
    installerLabel.textContent = "Ver versões no GitHub";
    installer.dataset.available = "false";
    portable.hidden = true;
    status.textContent = "Instalador em preparação · confira as versões publicadas.";
  }

  checkAvailability();
})();
