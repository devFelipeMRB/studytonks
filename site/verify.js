"use strict";

// Offline regression checks: no dependencies and no request to GitHub.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const code = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
const releaseRoot = "https://github.com/devFelipeMRB/studytonks/releases/download/v1.0.0/";
const installerUrl = `${releaseRoot}Studytonks-Setup.exe`;
const portableUrl = `${releaseRoot}Studytonks-Portable.zip`;
const validManifest = { available: true, version: "v1.0.0", installer_url: installerUrl, portable_url: portableUrl };

function element() {
  return {
    href: "https://github.com/devFelipeMRB/studytonks/releases",
    hidden: true,
    textContent: "",
    dataset: {},
    setAttribute() {},
    addEventListener() {},
  };
}

async function run(manifest, release) {
  const elements = Object.fromEntries(["installer-download", "installer-label", "release-status", "portable-download", "theme-toggle"].map((id) => [id, element()]));
  const requested = [];
  const context = {
    URL, AbortController,
    localStorage: { getItem() { return null; }, setItem() {} },
    document: {
      documentElement: { dataset: {} },
      getElementById(id) { return elements[id]; },
      querySelector() { return {}; },
    },
    window: {
      matchMedia() { return { matches: false, addEventListener() {} }; },
      setTimeout, clearTimeout,
    },
    async fetch(url) {
      requested.push(url);
      const result = url === "release.json" ? manifest : release;
      if (result instanceof Error) throw result;
      return { ok: result != null, async json() { return result; } };
    },
  };
  vm.runInNewContext(code, context, { filename: "app.js" });
  await new Promise(setImmediate);
  return { elements, requested };
}

async function main() {
  let result = await run(validManifest, null);
  assert.equal(result.elements["installer-download"].dataset.available, "true");
  assert.equal(result.elements["installer-download"].href, installerUrl);
  assert.equal(result.elements["portable-download"].hidden, false);
  assert.equal(result.requested.length, 1, "valid manifest avoids an unnecessary API request");

  for (const manifest of [null, { available: false }, { ...validManifest, installer_url: "https://other.example/Studytonks-Setup.exe" }, { ...validManifest, installer_url: `${installerUrl}?redirect=1` }]) {
    result = await run(manifest, null);
    assert.equal(result.elements["installer-download"].dataset.available, "false");
    assert.equal(result.elements["installer-download"].href, "https://github.com/devFelipeMRB/studytonks/releases");
    assert.equal(result.elements["portable-download"].hidden, true);
  }

  const release = {
    draft: false,
    prerelease: false,
    tag_name: "v1.0.0",
    assets: [{ name: "Studytonks-Setup.exe", state: "uploaded", size: 123, browser_download_url: installerUrl }],
  };
  result = await run({ available: false }, release);
  assert.equal(result.elements["installer-download"].dataset.available, "true");
  assert.equal(result.elements["portable-download"].hidden, true);
  assert.equal(result.requested.length, 2);

  for (const invalid of [
    { ...release, draft: true },
    { ...release, prerelease: true },
    { ...release, assets: [{ ...release.assets[0], size: 0 }] },
    { ...release, assets: [{ ...release.assets[0], state: "uploading" }] },
    { ...release, assets: [{ ...release.assets[0], browser_download_url: "https://github.com/another/repository/releases/download/v1.0.0/Studytonks-Setup.exe" }] },
    new Error("Offline"),
  ]) {
    result = await run({ available: false }, invalid);
    assert.equal(result.elements["installer-download"].dataset.available, "false");
  }

  console.log("12 release checks passed: published artifacts, preparation, unsafe links, invalid releases, and offline fallback.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
