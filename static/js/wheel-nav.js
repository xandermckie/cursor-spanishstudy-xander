(function() {
  'use strict';
  
  const CONFIG = {
    SWIPE_THRESHOLD: 80,
    TAP_MAX_DURATION: 200,
    DOT_COUNT: 12,
    DEBOUNCE_RESIZE: 150,
    SESSION_KEY: 'wheelNavState',
    FRICTION: 0.95,
    MIN_VELOCITY: 0.1,
    DRAG_MULTIPLIER: 0.3
  };
  
  class WheelNav {
    constructor() {
      this.wheelNav = document.getElementById('wheel-nav');
      this.container = document.getElementById('wheel-container');
      this.track = document.getElementById('wheel-segments-track');
      this.hub = document.getElementById('wheel-hub');
      this.hint = document.getElementById('wheel-swipe-hint');
      this.tooltip = document.getElementById('wheel-tooltip');
      
      if (!this.wheelNav || !this.container || !this.track) return;
      
      this.isHomepage = document.body.dataset.page === 'home';
      this.state = this.isHomepage ? 'expanded' : 'minimized';
      
      this.touchStartY = 0;
      this.touchStartTime = 0;
      this.isDragging = false;
      
      this.rotation = 0;
      this.targetRotation = 0;
      this.velocity = 0;
      this.lastMouseAngle = 0;
      this.isSpinning = false;
      
      this.tiltX = 0;
      this.tiltY = 0;
      
      this.init();
    }
    
    init() {
      if (!this.isHomepage) {
        this.loadSavedState();
      }
      this.positionDots();
      this.updateActiveSegment();
      this.bindEvents();
      
      if (!this.isHomepage && this.state === 'minimized') {
        this.setState('minimized', false);
      }
      
      requestAnimationFrame(() => this.animate());
    }
    
    loadSavedState() {
      try {
        const saved = sessionStorage.getItem(CONFIG.SESSION_KEY);
        if (saved) {
          this.state = saved;
        }
      } catch (e) {
        console.warn('Failed to load wheel state:', e);
      }
    }
    
    setState(newState, animated = true) {
      if (this.isHomepage) return;
      
      this.state = newState;
      const isExpanded = newState === 'expanded';
      
      if (!animated) {
        this.wheelNav.classList.add('no-transition');
      }
      
      if (isExpanded) {
        this.wheelNav.classList.remove('minimized');
        document.body.style.overflow = 'hidden';
        if (this.hint) {
          this.hint.classList.remove('visible');
        }
      } else {
        this.wheelNav.classList.add('minimized');
        document.body.style.overflow = '';
        setTimeout(() => {
          if (this.hint) {
            this.hint.classList.add('visible');
          }
        }, 400);
      }
      
      try {
        sessionStorage.setItem(CONFIG.SESSION_KEY, newState);
      } catch (e) {
        console.warn('Failed to save wheel state:', e);
      }
      
      if (!animated) {
        setTimeout(() => {
          this.wheelNav.classList.remove('no-transition');
        }, 50);
      }
    }
    
    positionDots() {
      const dotWrappers = this.track.querySelectorAll('.wheel-dot-wrapper');
      const radius = this.getWheelRadius();
      const angleStep = (2 * Math.PI) / CONFIG.DOT_COUNT;
      
      dotWrappers.forEach((wrapper, index) => {
        const angle = index * angleStep - Math.PI / 2;
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;
        wrapper.style.transform = `translate(${x}px, ${y}px)`;
      });
    }
    
    getWheelRadius() {
      const isMobile = window.innerWidth <= 900;
      return isMobile ? 140 : 200;
    }
    
    updateActiveSegment() {
      const currentPage = document.body.dataset.page;
      const dots = this.track.querySelectorAll('.wheel-dot');
      
      dots.forEach(dot => {
        const link = dot;
        if (link.dataset.page === currentPage) {
          link.classList.add('is-active');
        } else {
          link.classList.remove('is-active');
        }
      });
    }
    
    bindEvents() {
      if (this.hub && !this.isHomepage) {
        this.hub.addEventListener('click', () => this.toggleState());
      }
      
      this.container.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
      this.container.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
      this.container.addEventListener('touchend', (e) => this.handleTouchEnd(e));
      
      this.container.addEventListener('mousedown', (e) => this.handleMouseDown(e));
      document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
      document.addEventListener('mouseup', () => this.handleMouseUp());
      
      const dots = this.track.querySelectorAll('.wheel-dot');
      dots.forEach(dot => {
        dot.addEventListener('mouseenter', (e) => this.showTooltip(e.target));
        dot.addEventListener('mouseleave', () => this.hideTooltip());
      });
      
      this.container.addEventListener('mousemove', (e) => this.handle3DTilt(e));
      this.container.addEventListener('mouseleave', () => this.reset3DTilt());
      
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.state === 'expanded' && !this.isHomepage) {
          this.setState('minimized');
        }
      });
      
      let resizeTimeout;
      window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
          this.positionDots();
        }, CONFIG.DEBOUNCE_RESIZE);
      });
    }
    
    toggleState() {
      const newState = this.state === 'expanded' ? 'minimized' : 'expanded';
      this.setState(newState);
    }
    
    handleTouchStart(e) {
      if (!this.isHomepage && this.state === 'minimized') {
        this.touchStartY = e.touches[0].clientY;
        this.touchStartTime = Date.now();
      }
      
      if (this.state === 'expanded' || this.isHomepage) {
        this.startDrag(e.touches[0].clientX, e.touches[0].clientY);
      }
    }
    
    handleTouchMove(e) {
      if (!this.isHomepage && this.state === 'minimized') {
        const deltaY = this.touchStartY - e.touches[0].clientY;
        if (Math.abs(deltaY) > 10) {
          e.preventDefault();
        }
      }
      
      if (this.isDragging) {
        e.preventDefault();
        this.updateDrag(e.touches[0].clientX, e.touches[0].clientY);
      }
    }
    
    handleTouchEnd(e) {
      if (!this.isHomepage && this.state === 'minimized') {
        const deltaY = this.touchStartY - e.changedTouches[0].clientY;
        const duration = Date.now() - this.touchStartTime;
        
        if (deltaY > CONFIG.SWIPE_THRESHOLD && duration < 500) {
          this.setState('expanded');
        }
      }
      
      if (this.isDragging) {
        this.endDrag();
      }
    }
    
    handleMouseDown(e) {
      if (e.target.closest('.wheel-dot') || e.target.closest('.wheel-hub')) {
        return;
      }
      
      if (this.state === 'expanded' || this.isHomepage) {
        this.startDrag(e.clientX, e.clientY);
      }
    }
    
    handleMouseMove(e) {
      if (this.isDragging) {
        this.updateDrag(e.clientX, e.clientY);
      }
    }
    
    handleMouseUp() {
      if (this.isDragging) {
        this.endDrag();
      }
    }
    
    startDrag(x, y) {
      this.isDragging = true;
      this.isSpinning = false;
      this.velocity = 0;
      
      const rect = this.container.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      this.lastMouseAngle = Math.atan2(y - centerY, x - centerX);
      
      this.track.classList.add('spinning');
      this.container.style.cursor = 'grabbing';
    }
    
    updateDrag(x, y) {
      if (!this.isDragging) return;
      
      const rect = this.container.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const angle = Math.atan2(y - centerY, x - centerX);
      
      let delta = angle - this.lastMouseAngle;
      
      if (delta > Math.PI) delta -= 2 * Math.PI;
      if (delta < -Math.PI) delta += 2 * Math.PI;
      
      this.velocity = delta * CONFIG.DRAG_MULTIPLIER;
      this.rotation += delta * (180 / Math.PI);
      this.lastMouseAngle = angle;
      
      this.track.style.transform = `rotate(${this.rotation}deg)`;
    }
    
    endDrag() {
      this.isDragging = false;
      this.isSpinning = true;
      this.track.classList.remove('spinning');
      this.container.style.cursor = '';
    }
    
    animate() {
      if (this.isSpinning && Math.abs(this.velocity) > CONFIG.MIN_VELOCITY) {
        this.rotation += this.velocity * (180 / Math.PI);
        this.velocity *= CONFIG.FRICTION;
        this.track.style.transform = `rotate(${this.rotation}deg)`;
      } else if (this.isSpinning) {
        this.isSpinning = false;
        this.velocity = 0;
      }
      
      requestAnimationFrame(() => this.animate());
    }
    
    handle3DTilt(e) {
      if (this.isDragging) return;
      
      const rect = this.container.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      
      const deltaX = (e.clientX - centerX) / rect.width;
      const deltaY = (e.clientY - centerY) / rect.height;
      
      this.tiltX = deltaY * -10;
      this.tiltY = deltaX * 10;
      
      this.container.style.setProperty('--tilt-x', `${this.tiltX}deg`);
      this.container.style.setProperty('--tilt-y', `${this.tiltY}deg`);
    }
    
    reset3DTilt() {
      this.tiltX = 0;
      this.tiltY = 0;
      this.container.style.setProperty('--tilt-x', '0deg');
      this.container.style.setProperty('--tilt-y', '0deg');
    }
    
    showTooltip(dot) {
      if (!this.tooltip) return;
      
      const tooltipText = dot.dataset.tooltip;
      if (!tooltipText) return;
      
      this.tooltip.textContent = tooltipText;
      this.tooltip.classList.add('visible');
    }
    
    hideTooltip() {
      if (!this.tooltip) return;
      this.tooltip.classList.remove('visible');
    }
  }
  
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
