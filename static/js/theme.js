(function () {
  var saved = localStorage.getItem('theme');
  if (saved === 'dark') {
    document.documentElement.classList.add('theme-pending-dark');
    document.body.classList.add('dark');
  }

  function updateToggleIcon() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
    btn.setAttribute('aria-label', document.body.classList.contains('dark') ? 'Modo claro' : 'Modo oscuro');
  }

  function toggleTheme() {
    document.body.classList.toggle('dark');
    localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
    updateToggleIcon();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.documentElement.classList.remove('theme-pending-dark');
    var btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', toggleTheme);
      updateToggleIcon();
    }
  });
})();
