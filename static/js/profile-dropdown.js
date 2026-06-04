(function() {
  'use strict';
  
  const toggle = document.getElementById('nav-profile-toggle');
  const menu = document.getElementById('nav-dropdown-menu');
  
  if (!toggle || !menu) return;
  
  toggle.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = menu.hidden === false;
    
    if (isOpen) {
      menu.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
    } else {
      menu.hidden = false;
      toggle.setAttribute('aria-expanded', 'true');
    }
  });
  
  // Close on outside click
  document.addEventListener('click', () => {
    menu.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
  });
  
  // Close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !menu.hidden) {
      menu.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
      toggle.focus();
    }
  });
  
  // Prevent menu clicks from closing dropdown
  menu.addEventListener('click', (e) => {
    // Let logout form submit close the menu
    if (!e.target.closest('form')) {
      e.stopPropagation();
    }
  });
})();
