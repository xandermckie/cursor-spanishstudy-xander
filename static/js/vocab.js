(function () {
  document.addEventListener('DOMContentLoaded', function () {
    var card = document.getElementById('flashcard');
    var revealBtn = document.getElementById('flash-reveal-btn');
    var actions = document.getElementById('flash-actions');
    var form = document.getElementById('vocab-form');
    if (!card) return;

    function reveal() {
      card.classList.add('is-revealed');
      if (revealBtn) revealBtn.classList.add('hidden');
      if (actions) actions.classList.remove('hidden');
      if (form) form.classList.remove('hidden');
    }

    if (revealBtn) {
      revealBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        reveal();
      });
    }
    card.addEventListener('click', function (e) {
      if (e.target.closest('button, form, a')) return;
      if (!card.classList.contains('is-revealed')) reveal();
    });

    if (!form) return;

    var correctBtn = form.querySelector('[data-action="correct"]');
    if (correctBtn) {
      correctBtn.addEventListener('click', function (e) {
        e.preventDefault();
        var overlay = document.createElement('div');
        overlay.className = 'celeb-overlay';
        overlay.innerHTML =
          '<div class="celeb-overlay-inner">' +
          '<div style="font-size:64px">🎉</div>' +
          '<p class="celeb-title">¡Correcto!</p>' +
          '<p class="celeb-xp">+10 XP</p>' +
          '</div>';
        document.body.appendChild(overlay);
        setTimeout(function () {
          overlay.remove();
          form.querySelector('input[name="missed"]').value = '0';
          form.submit();
        }, 1800);
      });
    }

    var missedBtn = form.querySelector('[data-action="missed"]');
    if (missedBtn) {
      missedBtn.addEventListener('click', function () {
        form.querySelector('input[name="missed"]').value = '1';
      });
    }
  });
})();
