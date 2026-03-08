(function () {
  // Sync theme with system preference when user changes it in OS settings.
  var mql = typeof window.matchMedia !== "undefined" && window.matchMedia("(prefers-color-scheme: light)");
  if (mql && mql.addEventListener) {
    mql.addEventListener("change", function (e) {
      document.documentElement.setAttribute("data-theme", e.matches ? "light" : "dark");
    });
  }
})();
