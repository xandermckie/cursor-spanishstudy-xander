(function () {
  'use strict';

  var PEZ_BY_PAGE = {
    home: { expression: 'happy', hint: '¡Bienvenido!' },
    reader: { expression: 'thinking', hint: '¡A leer!' },
    vocab: { expression: 'excited', hint: '¡Practica!' },
    phrasebook: { expression: 'thinking', hint: 'Tus frases' },
    travel: { expression: 'happy', hint: 'Explora Barcelona' },
    news: { expression: 'thinking', hint: 'Últimas noticias' },
    history: { expression: 'thinking', hint: 'Historia de España' },
    resources: { expression: 'happy', hint: 'Más recursos' },
  };

  var ANGLE_STEP = 22;
  var DRAG_PX_PER_INDEX = 72;

  function mod(n, m) {
    return ((n % m) + m) % m;
  }

  function pathnameMatches(href) {
    try {
      var url = new URL(href, window.location.origin);
      return url.pathname === window.location.pathname;
    } catch (e) {
      return false;
    }
  }

  function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function AquariumNav() {
    this.dock = document.getElementById('aquarium-dock');
    if (!this.dock) return;

    this.peek = document.getElementById('aquarium-peek');
    this.sheet = document.getElementById('aquarium-sheet');
    this.scrim = document.getElementById('aquarium-scrim');
    this.wheel = document.getElementById('aquarium-wheel');
    this.track = document.getElementById('aquarium-wheel-track');
    this.segments = Array.prototype.slice.call(
      this.track ? this.track.querySelectorAll('.aquarium-segment') : []
    );
    this.hintEl = document.getElementById('aquarium-pez-hint');
    this.pezVariants = Array.prototype.slice.call(
      document.querySelectorAll('.aquarium-pez-variant')
    );
    this.peekIcon = document.getElementById('aquarium-peek-icon');
    this.peekLabel = document.getElementById('aquarium-peek-label');
    this.sheetGrab = document.getElementById('aquarium-sheet-grab');
    this.minimizeBtn = document.getElementById('aquarium-peek-minimize');

    this.activeIndex = 0;
    this.dragOffset = 0;
    this.wheelDragging = false;
    this.sheetDragging = false;
    this.pointerStartY = 0;
    this.pointerStartX = 0;
    this.wheelStartIndex = 0;
    this.state = 'peek';
    this.reducedMotion = prefersReducedMotion();
    this.scrollCollapse = this.dock.dataset.scrollCollapse !== 'off';

    this.initIndex();
    this.bindEvents();
    this.applyWheelLayout(0);
    this.updatePezForIndex(this.activeIndex);
    this.syncPeekFromIndex(this.activeIndex);

    var saved = sessionStorage.getItem('aquariumDockState');
    if (saved === 'hidden') {
      this.setState('hidden');
    } else if (saved === 'expanded') {
      this.setState('expanded');
    } else {
      this.setState('peek');
    }
  }

  AquariumNav.prototype.initIndex = function () {
    var page = document.body.dataset.page;
    var idx = 0;
    this.segments.forEach(function (seg, i) {
      if (seg.dataset.page === page) idx = i;
    });
    this.activeIndex = idx;
  };

  AquariumNav.prototype.setState = function (next) {
    this.state = next;
    this.dock.classList.remove('is-peek', 'is-expanded', 'is-hidden');
    document.body.classList.remove('aquarium-dock-hidden');

    if (next === 'expanded') {
      this.dock.classList.add('is-expanded');
      if (this.scrim) {
        this.scrim.removeAttribute('hidden');
      }
      if (this.sheet) {
        this.sheet.setAttribute('aria-hidden', 'false');
      }
      if (this.peek) {
        this.peek.setAttribute('aria-expanded', 'true');
      }
      sessionStorage.setItem('aquariumDockState', 'expanded');
      this.applyWheelLayout(0);
      this.trapFocus();
    } else if (next === 'hidden') {
      this.dock.classList.add('is-hidden');
      document.body.classList.add('aquarium-dock-hidden');
      if (this.scrim) {
        this.scrim.setAttribute('hidden', '');
      }
      if (this.sheet) {
        this.sheet.setAttribute('aria-hidden', 'true');
      }
      if (this.peek) {
        this.peek.setAttribute('aria-expanded', 'false');
        this.peek.setAttribute('aria-label', 'Abrir navegación');
      }
      sessionStorage.setItem('aquariumDockState', 'hidden');
      this.releaseFocus();
    } else {
      this.dock.classList.add('is-peek');
      if (this.scrim) {
        this.scrim.setAttribute('hidden', '');
      }
      if (this.sheet) {
        this.sheet.setAttribute('aria-hidden', 'true');
      }
      if (this.peek) {
        this.peek.setAttribute('aria-expanded', 'false');
        this.peek.setAttribute('aria-label', 'Abrir navegación');
      }
      sessionStorage.setItem('aquariumDockState', 'peek');
      this.releaseFocus();
    }
  };

  AquariumNav.prototype.applyWheelLayout = function (dragOffset) {
    if (this.reducedMotion) {
      this.layoutWheelFlat(dragOffset);
      return;
    }
    var virtual = this.activeIndex + dragOffset;
    this.segments.forEach(function (seg, i) {
      var delta = i - virtual;
      if (delta > 4) delta -= 8;
      if (delta < -4) delta += 8;
      var angle = delta * ANGLE_STEP;
      var scale = Math.abs(delta) < 0.45 ? 1.1 : Math.max(0.72, 1 - Math.abs(delta) * 0.11);
      var opacity = Math.abs(delta) < 0.45 ? 1 : Math.max(0.38, 1 - Math.abs(delta) * 0.22);
      var translateX = delta * 58;
      var translateZ = -Math.abs(delta) * 24;
      seg.style.transform =
        'translateX(calc(-50% + ' + translateX + 'px)) translateY(-50%) ' +
        'translateZ(' + translateZ + 'px) rotateY(' + angle + 'deg) scale(' + scale + ')';
      seg.style.opacity = String(opacity);
      seg.classList.toggle('is-center', Math.abs(delta) < 0.45);
    });
  };

  AquariumNav.prototype.layoutWheelFlat = function () {
    this.segments.forEach(function (seg, i) {
      seg.style.transform = 'none';
      seg.style.opacity = '1';
      seg.classList.toggle('is-center', i === this.activeIndex);
    }, this);
    var center = this.segments[this.activeIndex];
    if (center && this.track) {
      center.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'instant' in window ? 'instant' : 'auto' });
    }
  };

  AquariumNav.prototype.updatePezForIndex = function (index) {
    var seg = this.segments[index];
    if (!seg) return;
    var page = seg.dataset.page;
    var meta = PEZ_BY_PAGE[page] || PEZ_BY_PAGE.home;
    if (this.hintEl) {
      this.hintEl.textContent = meta.hint;
    }
    this.pezVariants.forEach(function (el) {
      el.classList.toggle('is-visible', el.dataset.expression === meta.expression);
    });
  };

  AquariumNav.prototype.syncPeekFromIndex = function (index) {
    var seg = this.segments[index];
    if (!seg) return;
    if (this.peekIcon) this.peekIcon.textContent = seg.dataset.icon || '';
    if (this.peekLabel) this.peekLabel.textContent = seg.dataset.label || '';
  };

  AquariumNav.prototype.snapWheel = function () {
    var total = this.segments.length;
    if (!total) return;
    var next = Math.round(this.activeIndex + this.dragOffset);
    this.activeIndex = mod(next, total);
    this.dragOffset = 0;
    this.applyWheelLayout(0);
    this.updatePezForIndex(this.activeIndex);
    this.syncPeekFromIndex(this.activeIndex);
  };

  AquariumNav.prototype.navigateIfCenter = function (seg) {
    if (!seg.classList.contains('is-center')) {
      var idx = this.segments.indexOf(seg);
      if (idx >= 0) {
        this.activeIndex = idx;
        this.dragOffset = 0;
        this.applyWheelLayout(0);
        this.updatePezForIndex(this.activeIndex);
        this.syncPeekFromIndex(this.activeIndex);
      }
      return;
    }
    var href = seg.dataset.href;
    if (!href) return;
    if (pathnameMatches(href)) {
      this.setState('peek');
      return;
    }
    window.location.href = href;
  };

  AquariumNav.prototype.trapFocus = function () {
    var self = this;
    this._focusHandler = function (e) {
      if (self.state !== 'expanded' || !self.sheet) return;
      if (!self.sheet.contains(e.target) && e.target !== self.peek) {
        e.stopPropagation();
        var first = self.sheet.querySelector(
          'button, a, summary, [tabindex]:not([tabindex="-1"])'
        );
        if (first) first.focus();
      }
    };
    document.addEventListener('focusin', this._focusHandler, true);
  };

  AquariumNav.prototype.releaseFocus = function () {
    if (this._focusHandler) {
      document.removeEventListener('focusin', this._focusHandler, true);
      this._focusHandler = null;
    }
  };

  AquariumNav.prototype.bindEvents = function () {
    var self = this;

    if (this.peek) {
      this.peek.addEventListener('click', function (e) {
        if (e.target.closest('.aquarium-peek-minimize')) return;
        if (self.state === 'hidden' || self.state === 'peek') {
          self.setState('expanded');
        } else if (self.state === 'expanded') {
          self.setState('peek');
        }
      });
    }

    if (this.minimizeBtn) {
      this.minimizeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (self.state === 'expanded') {
          self.setState('peek');
        }
        self.setState('hidden');
      });
    }

    if (this.scrim) {
      this.scrim.addEventListener('click', function () {
        self.setState('peek');
      });
    }

    this.segments.forEach(function (seg) {
      seg.addEventListener('click', function () {
        self.navigateIfCenter(seg);
      });
    });

    if (this.wheel) {
      this.wheel.addEventListener('pointerdown', function (e) {
        if (e.button !== 0) return;
        self.wheelDragging = true;
        self.wheelStartIndex = self.activeIndex;
        self.pointerStartX = e.clientX;
        self.dragOffset = 0;
        self.wheel.classList.add('is-dragging');
        self.wheel.setPointerCapture(e.pointerId);
      });

      this.wheel.addEventListener('pointermove', function (e) {
        if (!self.wheelDragging) return;
        var dx = e.clientX - self.pointerStartX;
        self.dragOffset = -dx / DRAG_PX_PER_INDEX;
        self.applyWheelLayout(self.dragOffset);
        var preview = mod(Math.round(self.wheelStartIndex + self.dragOffset), self.segments.length);
        self.updatePezForIndex(preview);
      });

      this.wheel.addEventListener('pointerup', function (e) {
        if (!self.wheelDragging) return;
        self.wheelDragging = false;
        self.wheel.classList.remove('is-dragging');
        self.activeIndex = self.wheelStartIndex;
        self.snapWheel();
        try {
          self.wheel.releasePointerCapture(e.pointerId);
        } catch (err) { /* ignore */ }
      });

      this.wheel.addEventListener('pointercancel', function () {
        self.wheelDragging = false;
        self.wheel.classList.remove('is-dragging');
        self.snapWheel();
      });
    }

    var dragHandle = this.sheetGrab || this.peek;
    if (dragHandle) {
      dragHandle.addEventListener('pointerdown', function (e) {
        if (e.target.closest('.aquarium-peek-minimize')) return;
        if (self.state !== 'expanded' && self.state !== 'peek') return;
        self.sheetDragging = true;
        self.pointerStartY = e.clientY;
        e.preventDefault();
      });
    }

    document.addEventListener('pointermove', function (e) {
      if (!self.sheetDragging) return;
      var dy = e.clientY - self.pointerStartY;
      if (self.state === 'expanded' && dy > 48) {
        self.sheetDragging = false;
        self.setState('peek');
      } else if (self.state === 'peek' && dy < -40) {
        self.sheetDragging = false;
        self.setState('expanded');
      }
    });

    document.addEventListener('pointerup', function () {
      self.sheetDragging = false;
    });

    document.addEventListener('keydown', function (e) {
      if (self.state !== 'expanded') return;
      if (e.key === 'Escape') {
        e.preventDefault();
        self.setState('peek');
        if (self.peek) self.peek.focus();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        self.activeIndex = mod(self.activeIndex - 1, self.segments.length);
        self.applyWheelLayout(0);
        self.updatePezForIndex(self.activeIndex);
        self.syncPeekFromIndex(self.activeIndex);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        self.activeIndex = mod(self.activeIndex + 1, self.segments.length);
        self.applyWheelLayout(0);
        self.updatePezForIndex(self.activeIndex);
        self.syncPeekFromIndex(self.activeIndex);
      } else if (e.key === 'Enter') {
        var focused = document.activeElement;
        if (focused && focused.classList.contains('aquarium-segment')) {
          e.preventDefault();
          self.navigateIfCenter(focused);
        }
      }
    });

    if (this.scrollCollapse && !document.body.classList.contains('travel-page')) {
      var scrollTicking = false;
      window.addEventListener(
        'scroll',
        function () {
          if (!scrollTicking) {
            window.requestAnimationFrame(function () {
              if (self.state === 'expanded' && window.scrollY > 24) {
                self.setState('peek');
              }
              scrollTicking = false;
            });
            scrollTicking = true;
          }
        },
        { passive: true }
      );
    }

    if (this.reducedMotion && this.track) {
      this.track.addEventListener('scroll', function () {
        var trackRect = this.track.getBoundingClientRect();
        var centerX = trackRect.left + trackRect.width / 2;
        var best = 0;
        var bestDist = Infinity;
        self.segments.forEach(function (seg, i) {
          var r = seg.getBoundingClientRect();
          var cx = r.left + r.width / 2;
          var d = Math.abs(cx - centerX);
          if (d < bestDist) {
            bestDist = d;
            best = i;
          }
        });
        if (best !== self.activeIndex) {
          self.activeIndex = best;
          self.updatePezForIndex(best);
          self.syncPeekFromIndex(best);
        }
      }.bind(this), { passive: true });
    }

    window.addEventListener('resize', function () {
      self.applyWheelLayout(0);
    });
  };

  function init() {
    var dock = document.getElementById('aquarium-dock');
    if (!dock || dock.dataset.aquariumInit === '1') return;
    dock.dataset.aquariumInit = '1';
    new AquariumNav();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
