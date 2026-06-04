(function () {
  var saved = localStorage.getItem('theme');
  if (saved === 'dark') {
    document.documentElement.classList.add('theme-pending-dark');
    document.body.classList.add('dark');
  }

  function updateToggleIcons() {
    var isDark = document.body.classList.contains('dark');
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
      btn.textContent = isDark ? '☀️' : '🌙';
      btn.setAttribute('aria-label', isDark ? 'Modo claro' : 'Modo oscuro');
    });
  }

  function toggleTheme() {
    document.body.classList.toggle('dark');
    localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
    updateToggleIcons();
  }

  function bindToggles() {
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
      if (btn.dataset.themeBound === '1') return;
      btn.dataset.themeBound = '1';
      btn.addEventListener('click', toggleTheme);
    });
    updateToggleIcons();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.documentElement.classList.remove('theme-pending-dark');
    bindToggles();
  });
})();
