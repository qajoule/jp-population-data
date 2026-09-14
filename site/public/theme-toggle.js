(() => {
  const button = document.querySelector(".theme-control");
  if (!button) return;

  const root = document.documentElement;
  const applyTheme = (theme) => {
    root.dataset.theme = theme;
    button.setAttribute("aria-pressed", String(theme === "dark"));
  };

  try {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "light" || savedTheme === "dark") applyTheme(savedTheme);
  } catch {
    // Theme selection remains usable when storage is unavailable.
  }

  button.addEventListener("click", () => {
    const effectiveTheme = root.dataset.theme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const theme = effectiveTheme === "dark" ? "light" : "dark";
    applyTheme(theme);
    try {
      localStorage.setItem("theme", theme);
    } catch {
      // Theme selection remains usable when storage is unavailable.
    }
  });
})();
