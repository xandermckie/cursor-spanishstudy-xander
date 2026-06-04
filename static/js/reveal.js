(function () {
  function toggleReveal(el) {
    if (el.closest('.flashcard')) return;
    if (el.closest('a, button, input, textarea, select, label, form')) return;
    el.classList.toggle('is-open');
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.reveal-card').forEach(function (el) {
      el.addEventListener('click', function () { toggleReveal(el); });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleReveal(el);
        }
      });
    });

    document.querySelectorAll('.weak-word-item').forEach(function (el) {
      el.addEventListener('click', function (e) {
        if (e.target.closest('a, button')) return;
        el.classList.toggle('is-open');
      });
    });

    document.querySelectorAll('.alert-close').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var alert = btn.closest('.alert');
        if (alert) alert.remove();
      });
    });

    var hamburger = document.getElementById('nav-hamburger');
    var navWrap = document.getElementById('nav-links-wrap');
    if (hamburger && navWrap && !document.body.classList.contains('has-aquarium-dock')) {
      hamburger.addEventListener('click', function () {
        navWrap.classList.toggle('is-open');
        hamburger.setAttribute('aria-expanded', navWrap.classList.contains('is-open'));
      });
    }
  });
})();
