(function() {
  var KEY = "theme";

  function getTheme() {
    var saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) return "dark";
    return "light";
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(KEY, theme);
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute("data-theme") || getTheme();
    setTheme(current === "light" ? "dark" : "light");
  }

  setTheme(getTheme());

  var btn = document.querySelector("[data-theme-toggle]");
  if (btn) btn.addEventListener("click", toggleTheme);
})();
