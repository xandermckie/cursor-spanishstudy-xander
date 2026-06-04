(function() {
  'use strict';
  
  // Configuration
  const CONFIG = {
    SWIPE_THRESHOLD: 50,
    TAP_MAX_DURATION: 300,
    SEGMENT_COUNT: 12,
    DEBOUNCE_RESIZE: 150,
    SESSION_KEY: 'wheelNavState'
  };
  
  // Main class
  class WheelNav {
    constructor() {
      this.wheelNav = document.getElementById('wheel-nav');
      if (!this.wheelNav) return;
      
      this.container = document.getElementById('wheel-container');
      this.scrim = document.getElementById('wheel-scrim');
      this.segments = Array.from(document.querySelectorAll('.wheel-segment'));
      this.hub = document.getElementById('wheel-hub');
      this.hint = document.getElementById('wheel-swipe-hint');
      
      this.state = 'expanded'; // expanded | minimized
      this.touchStartY = 0;
      this.touchStartTime = 0;
      this.isDragging = false;
      
      this.init();
    }
    
    init() {
      this.loadSavedState();
      this.bindEvents();
      this.positionSegments();
      this.updateActiveSegment();
    }
    
    loadSavedState() {
      const saved = sessionStorage.getItem(CONFIG.SESSION_KEY);
      const initialState = this.wheelNav.dataset.initialState || 'expanded';
      
      if (saved && saved === 'minimized') {
        this.setState('minimized', false);
      } else if (!saved && initialState === 'expanded') {
        this.setState('expanded', false);
        // Mark as visited so next load is minimized
        sessionStorage.setItem(CONFIG.SESSION_KEY, 'visited');
      } else if (saved === 'visited') {
        this.setState('minimized', false);
      } else {
        this.setState('minimized', false);
      }
    }
    
    setState(newState, animated = true) {
      if (this.state === newState) return;
      
      this.wheelNav.classList.remove('expanded', 'minimized');
      if (!animated) {
        this.wheelNav.classList.add('no-transition');
      }
      
      this.state = newState;
      this.wheelNav.classList.add(newState);
      
      // Update scrim visibility
      if (newState === 'expanded') {
        this.scrim.classList.add('visible');
        if (this.hint) {
          this.hint.classList.remove('visible');
        }
        document.body.style.overflow = 'hidden'; // Prevent scroll
      } else {
        this.scrim.classList.remove('visible');
        if (this.hint) {
          this.hint.classList.add('visible');
        }
        document.body.style.overflow = '';
      }
      
      // Save to session
      sessionStorage.setItem(CONFIG.SESSION_KEY, newState);
      
      if (!animated) {
        setTimeout(() => {
          this.wheelNav.classList.remove('no-transition');
        }, 50);
      }
    }
    
    positionSegments() {
      const angleStep = 360 / CONFIG.SEGMENT_COUNT;
      const radius = this.getWheelRadius();
      
      this.segments.forEach((segment, index) => {
        const angle = index * angleStep;
        const radian = (angle - 90) * (Math.PI / 180); // -90 to start at top
        
        const x = Math.cos(radian) * radius;
        const y = Math.sin(radian) * radius;
        
        segment.style.transform = `translate(${x}px, ${y}px)`;
      });
    }
    
    getWheelRadius() {
      const isMobile = window.innerWidth <= 900;
      const diameter = isMobile ? 280 : 420;
      const segmentSize = isMobile ? 72 : 80;
      return (diameter / 2) - (segmentSize / 2);
    }
    
    updateActiveSegment() {
      const currentPage = document.body.dataset.page;
      this.segments.forEach(seg => {
        seg.classList.toggle('is-active', seg.dataset.page === currentPage);
      });
    }
    
    bindEvents() {
      // Scrim click → minimize
      this.scrim.addEventListener('click', () => {
        this.setState('minimized');
      });
      
      // Hub click → expand (when minimized)
      this.hub.addEventListener('click', (e) => {
        if (this.state === 'minimized') {
          e.preventDefault();
          this.setState('expanded');
        }
      });
      
      // Touch gestures on container
      this.container.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
      this.container.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
      this.container.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
      
      // Keyboard navigation
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.state === 'expanded') {
          e.preventDefault();
          this.setState('minimized');
        }
      });
      
      // Window resize → reposition segments
      let resizeTimer;
      window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
          this.positionSegments();
        }, CONFIG.DEBOUNCE_RESIZE);
      });
    }
    
    handleTouchStart(e) {
      this.touchStartY = e.touches[0].clientY;
      this.touchStartTime = Date.now();
      this.isDragging = false;
    }
    
    handleTouchMove(e) {
      if (Math.abs(e.touches[0].clientY - this.touchStartY) > 10) {
        this.isDragging = true;
      }
    }
    
    handleTouchEnd(e) {
      const touchEndY = e.changedTouches[0].clientY;
      const deltaY = this.touchStartY - touchEndY;
      const duration = Date.now() - this.touchStartTime;
      
      // Swipe up detection (when minimized)
      if (
        this.state === 'minimized' &&
        deltaY > CONFIG.SWIPE_THRESHOLD &&
        duration < 500
      ) {
        e.preventDefault();
        this.setState('expanded');
        return;
      }
      
      // Swipe down detection (when expanded)
      if (
        this.state === 'expanded' &&
        deltaY < -CONFIG.SWIPE_THRESHOLD &&
        duration < 500
      ) {
        e.preventDefault();
        this.setState('minimized');
        return;
      }
      
      // Tap detection on minimized wheel → expand
      if (
        this.state === 'minimized' &&
        !this.isDragging &&
        duration < CONFIG.TAP_MAX_DURATION
      ) {
        this.setState('expanded');
      }
    }
  }
  
  // Initialize on DOM ready
  function init() {
    if (document.getElementById('wheel-nav')) {
      new WheelNav();
    }
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
