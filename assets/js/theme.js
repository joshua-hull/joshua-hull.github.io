// Colour-scheme toggle. jh.css already ships both palettes, keyed on
// prefers-color-scheme with a [data-theme] escape hatch, so this only has to
// set that attribute. head.html applies any stored value before first paint.
(function () {
  var KEY = "theme";
  var root = document.documentElement;

  function systemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function current() {
    return root.getAttribute("data-theme") || systemTheme();
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    try { localStorage.setItem(KEY, theme); } catch (e) {}
  }

  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      apply(current() === "dark" ? "light" : "dark");
    });
  });

  // Follow the OS while the viewer has expressed no preference of their own.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
    var stored;
    try { stored = localStorage.getItem(KEY); } catch (e) {}
    if (stored !== "light" && stored !== "dark") root.removeAttribute("data-theme");
  });
})();
