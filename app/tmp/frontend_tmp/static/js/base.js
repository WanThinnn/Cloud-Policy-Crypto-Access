/**
 * BASE JAVASCRIPT
 * Common functionality for all pages
 */

class BaseApp {
  constructor() {
    this.currentTheme = 'auto';
    this.init();
  }

  init() {
    this.initTheme();
    this.setupMobileMenu();
    this.setupFlashMessages();
    this.setupLoadingStates();
    this.setupGlobalEventListeners();
    this.setupApiHelpers();
    this.initializeTooltips();
    this.setupThemeSwitcher();
    this.setupProfileDropdown();
  }

  /**
   * Initialize theme system
   */
  initTheme() {
    // Load saved theme preference
    const savedTheme = localStorage.getItem('theme') || 'auto';
    this.setTheme(savedTheme);
    
    // Listen for system theme changes
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addListener(() => {
        if (this.currentTheme === 'auto') {
          this.updateThemeDisplay();
        }
      });
    }
  }

  /**
   * Setup theme switcher button
   */
  setupThemeSwitcher() {
    const themeSwitcher = document.getElementById('themeSwitcher');
    if (themeSwitcher) {
      themeSwitcher.addEventListener('click', () => {
        this.toggleTheme();
      });
    }
  }

  /**
   * Toggle between themes
   */
  toggleTheme() {
    const themes = ['auto', 'light', 'dark'];
    const currentIndex = themes.indexOf(this.currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    const nextTheme = themes[nextIndex];
    
    this.setTheme(nextTheme);
    this.showToast(`Theme switched to ${nextTheme}`, 'info', 2000);
  }

  /**
   * Set theme
   */
  setTheme(theme) {
    this.currentTheme = theme;
    localStorage.setItem('theme', theme);
    
    const html = document.documentElement;
    const body = document.body;
    
    if (theme === 'light') {
      html.setAttribute('data-theme', 'light');
      body.setAttribute('data-theme', 'light');
    } else if (theme === 'dark') {
      html.setAttribute('data-theme', 'dark');
      body.setAttribute('data-theme', 'dark');
    } else {
      // Auto theme - detect system preference
      const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      const effectiveTheme = isDark ? 'dark' : 'light';
      html.setAttribute('data-theme', effectiveTheme);
      body.setAttribute('data-theme', effectiveTheme);
    }
    
    this.updateThemeDisplay();
  }

  /**
   * Update theme switcher display
   */
  updateThemeDisplay() {
    const themeSwitcher = document.getElementById('themeSwitcher');
    const themeIcon = themeSwitcher?.querySelector('.theme-icon');
    
    if (!themeIcon) return;
    
    let icon, title;
    
    if (this.currentTheme === 'light') {
      icon = '☀️';
      title = 'Switch to dark theme';
    } else if (this.currentTheme === 'dark') {
      icon = '🌙';
      title = 'Switch to auto theme';
    } else {
      // Auto theme - show current system preference
      const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      icon = isDark ? '🌓' : '🌗';
      title = 'Switch to light theme (currently auto)';
    }
    
    themeIcon.textContent = icon;
    themeSwitcher.title = title;
  }

  /**
   * Get current effective theme (resolving auto)
   */
  getEffectiveTheme() {
    if (this.currentTheme === 'auto') {
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return this.currentTheme;
  }
  setupMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileMenuBtn && navMenu) {
      mobileMenuBtn.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        mobileMenuBtn.classList.toggle('active');
        
        // Animate hamburger menu
        const spans = mobileMenuBtn.querySelectorAll('span');
        if (mobileMenuBtn.classList.contains('active')) {
          spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
          spans[1].style.opacity = '0';
          spans[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
        } else {
          spans[0].style.transform = 'none';
          spans[1].style.opacity = '1';
          spans[2].style.transform = 'none';
        }
      });

      // Close mobile menu when clicking outside
      document.addEventListener('click', (e) => {
        if (!mobileMenuBtn.contains(e.target) && !navMenu.contains(e.target)) {
          navMenu.classList.remove('active');
          mobileMenuBtn.classList.remove('active');
          
          // Reset hamburger menu
          const spans = mobileMenuBtn.querySelectorAll('span');
          spans[0].style.transform = 'none';
          spans[1].style.opacity = '1';
          spans[2].style.transform = 'none';
        }
      });

      // Close mobile menu on window resize
      window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
          navMenu.classList.remove('active');
          mobileMenuBtn.classList.remove('active');
          
          const spans = mobileMenuBtn.querySelectorAll('span');
          spans[0].style.transform = 'none';
          spans[1].style.opacity = '1';
          spans[2].style.transform = 'none';
        }
      });
    }
  }

  /**
   * Setup flash message auto-dismiss
   */
  setupFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    
    flashMessages.forEach(message => {
      // Auto-dismiss after 5 seconds
      setTimeout(() => {
        this.dismissFlashMessage(message);
      }, 5000);
      
      // Setup close button
      const closeBtn = message.querySelector('.flash-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => {
          this.dismissFlashMessage(message);
        });
      }
    });
  }

  /**
   * Dismiss flash message with animation
   */
  dismissFlashMessage(message) {
    message.style.transform = 'translateX(100%)';
    message.style.opacity = '0';
    
    setTimeout(() => {
      if (message.parentNode) {
        message.parentNode.removeChild(message);
      }
    }, 300);
  }

  /**
   * Setup loading states for forms and buttons
   */
  setupLoadingStates() {
    // Form submissions
    document.addEventListener('submit', (e) => {
      const form = e.target;
      if (form.tagName === 'FORM' && !form.hasAttribute('data-no-loading')) {
        this.setFormLoading(form, true);
      }
    });

    // Button clicks
    document.addEventListener('click', (e) => {
      const button = e.target.closest('button, .btn');
      if (button && button.hasAttribute('data-loading')) {
        this.setButtonLoading(button, true);
      }
    });
  }

  /**
   * Set form loading state
   */
  setFormLoading(form, isLoading) {
    const submitBtns = form.querySelectorAll('button[type="submit"], input[type="submit"]');
    
    submitBtns.forEach(btn => {
      if (isLoading) {
        btn.disabled = true;
        btn.style.opacity = '0.7';
        btn.style.cursor = 'not-allowed';
        
        // Add loading text if not present
        if (!btn.hasAttribute('data-original-text')) {
          btn.setAttribute('data-original-text', btn.textContent);
          btn.innerHTML = '<span class="spinner-small"></span> Processing...';
        }
      } else {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
        
        // Restore original text
        const originalText = btn.getAttribute('data-original-text');
        if (originalText) {
          btn.textContent = originalText;
          btn.removeAttribute('data-original-text');
        }
      }
    });
  }

  /**
   * Set button loading state
   */
  setButtonLoading(button, isLoading) {
    if (isLoading) {
      button.disabled = true;
      button.style.opacity = '0.7';
      
      if (!button.hasAttribute('data-original-text')) {
        button.setAttribute('data-original-text', button.textContent);
        button.innerHTML = '<span class="spinner-small"></span> Loading...';
      }
    } else {
      button.disabled = false;
      button.style.opacity = '1';
      
      const originalText = button.getAttribute('data-original-text');
      if (originalText) {
        button.textContent = originalText;
        button.removeAttribute('data-original-text');
      }
    }
  }

  /**
   * Setup global event listeners
   */
  setupGlobalEventListeners() {
    // Escape key handling
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.handleEscapeKey();
      }
    });

    // Copy to clipboard functionality
    document.addEventListener('click', (e) => {
      if (e.target.hasAttribute('data-copy')) {
        e.preventDefault();
        const textToCopy = e.target.getAttribute('data-copy');
        this.copyToClipboard(textToCopy);
      }
    });

    // Confirm dialogs
    document.addEventListener('click', (e) => {
      const confirmMsg = e.target.getAttribute('data-confirm');
      if (confirmMsg) {
        if (!confirm(confirmMsg)) {
          e.preventDefault();
          e.stopPropagation();
        }
      }
    });

    // Auto-resize textareas
    document.addEventListener('input', (e) => {
      if (e.target.tagName === 'TEXTAREA' && e.target.hasAttribute('data-auto-resize')) {
        this.autoResizeTextarea(e.target);
      }
    });
  }

  /**
   * Handle escape key press
   */
  handleEscapeKey() {
    // Close modals
    const activeModals = document.querySelectorAll('.modal.active');
    activeModals.forEach(modal => {
      modal.classList.remove('active');
      modal.style.display = 'none';
    });

    // Close mobile menu
    const mobileMenu = document.querySelector('.nav-menu.active');
    if (mobileMenu) {
      mobileMenu.classList.remove('active');
      const mobileMenuBtn = document.getElementById('mobileMenuBtn');
      if (mobileMenuBtn) {
        mobileMenuBtn.classList.remove('active');
      }
    }

    // Clear focus from active elements
    if (document.activeElement && document.activeElement.blur) {
      document.activeElement.blur();
    }
  }

  /**
   * Copy text to clipboard
   */
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      this.showToast('Copied to clipboard!', 'success');
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      this.showToast('Failed to copy to clipboard', 'error');
    }
  }

  /**
   * Auto-resize textarea
   */
  autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
  }

  /**
   * Setup API helpers
   */
  setupApiHelpers() {
    // Set up CSRF token for all requests if available
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    if (csrfToken) {
      this.csrfToken = csrfToken.getAttribute('content');
    }

    // Setup default fetch options
    this.defaultFetchOptions = {
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    };

    if (this.csrfToken) {
      this.defaultFetchOptions.headers['X-CSRFToken'] = this.csrfToken;
    }
  }

  /**
   * Make API request with error handling
   */
  async apiRequest(url, options = {}) {
    const config = {
      ...this.defaultFetchOptions,
      ...options,
      headers: {
        ...this.defaultFetchOptions.headers,
        ...(options.headers || {})
      }
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      } else {
        return await response.text();
      }
    } catch (error) {
      console.error('API request failed:', error);
      this.showToast('Request failed. Please try again.', 'error');
      throw error;
    }
  }

  /**
   * Initialize tooltips
   */
  initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
      this.setupTooltip(element);
    });
  }

  /**
   * Setup tooltip for element
   */
  setupTooltip(element) {
    const tooltipText = element.getAttribute('data-tooltip');
    
    element.addEventListener('mouseenter', (e) => {
      this.showTooltip(e.target, tooltipText);
    });
    
    element.addEventListener('mouseleave', () => {
      this.hideTooltip();
    });
  }

  /**
   * Show tooltip
   */
  showTooltip(element, text) {
    // Remove existing tooltip
    this.hideTooltip();
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = `
      position: absolute;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--border-radius-small);
      padding: var(--space-sm);
      font-size: var(--font-size-xs);
      color: var(--text-primary);
      backdrop-filter: blur(20px);
      box-shadow: var(--shadow-soft);
      z-index: 10000;
      pointer-events: none;
      max-width: 200px;
      word-wrap: break-word;
      opacity: 0;
      transition: opacity 0.2s ease;
    `;

    document.body.appendChild(tooltip);

    // Position tooltip
    const rect = element.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    
    let top = rect.top - tooltipRect.height - 8;
    let left = rect.left + (rect.width - tooltipRect.width) / 2;

    // Adjust if tooltip goes off screen
    if (top < 0) {
      top = rect.bottom + 8;
    }
    if (left < 0) {
      left = 8;
    }
    if (left + tooltipRect.width > window.innerWidth) {
      left = window.innerWidth - tooltipRect.width - 8;
    }

    tooltip.style.top = top + window.scrollY + 'px';
    tooltip.style.left = left + 'px';

    // Show tooltip
    setTimeout(() => {
      tooltip.style.opacity = '1';
    }, 10);

    this.currentTooltip = tooltip;
  }

  /**
   * Hide tooltip
   */
  hideTooltip() {
    if (this.currentTooltip) {
      this.currentTooltip.style.opacity = '0';
      setTimeout(() => {
        if (this.currentTooltip && this.currentTooltip.parentNode) {
          this.currentTooltip.parentNode.removeChild(this.currentTooltip);
        }
        this.currentTooltip = null;
      }, 200);
    }
  }

  /**
   * Show toast notification
   */
  showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-content">
        <span class="toast-icon">${this.getToastIcon(type)}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
      </div>
    `;

    // Add styles
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--border-radius);
      padding: var(--space-md);
      backdrop-filter: blur(20px);
      box-shadow: var(--shadow-soft);
      z-index: 10000;
      transform: translateY(100%);
      transition: var(--transition);
      max-width: 300px;
      margin-bottom: var(--space-sm);
    `;

    // Type-specific styles
    if (type === 'success') {
      toast.style.borderColor = 'rgba(74, 222, 128, 0.3)';
      toast.style.background = 'rgba(74, 222, 128, 0.1)';
    } else if (type === 'error') {
      toast.style.borderColor = 'rgba(239, 68, 68, 0.3)';
      toast.style.background = 'rgba(239, 68, 68, 0.1)';
    } else if (type === 'warning') {
      toast.style.borderColor = 'rgba(251, 191, 36, 0.3)';
      toast.style.background = 'rgba(251, 191, 36, 0.1)';
    }

    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => {
      toast.style.transform = 'translateY(0)';
    }, 100);

    // Auto-dismiss
    setTimeout(() => {
      toast.style.transform = 'translateY(100%)';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }, duration);
  }

  /**
   * Setup profile dropdown
   */
  setupProfileDropdown() {
    const profileDropdown = document.getElementById('profileDropdown');
    const profileMenu = document.getElementById('profileMenu');

    if (profileDropdown && profileMenu) {
      // Toggle dropdown on click
      profileDropdown.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        profileMenu.classList.toggle('show');
      });

      // Close dropdown when clicking outside
      document.addEventListener('click', (e) => {
        if (!profileDropdown.contains(e.target) && !profileMenu.contains(e.target)) {
          profileMenu.classList.remove('show');
        }
      });

      // Close dropdown on escape key
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          profileMenu.classList.remove('show');
        }
      });
    }

    // Handle logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        await this.handleLogout();
      });
    }

    // Handle Get Private Key
    const getPrivateKeyBtn = document.getElementById('getPrivateKeyBtn');
    if (getPrivateKeyBtn) {
      getPrivateKeyBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        await this.handleGetPrivateKey();
      });
    }
  }

  /**
   * Handle user logout
   */
  async handleLogout() {
    try {
      const response = await fetch('/api/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (response.ok) {
        // Clear local storage
        localStorage.removeItem('user');
        
        // Show success message
        this.showToast('Logged out successfully', 'success', 2000);
        
        // Redirect to login page
        setTimeout(() => {
          window.location.href = '/login';
        }, 1000);
      } else {
        this.showToast(data.error || 'Logout failed', 'error');
      }
    } catch (error) {
      console.error('Logout error:', error);
      this.showToast('Network error during logout', 'error');
    }
  }

  /**
   * Handle Get Private Key
   */
  async handleGetPrivateKey() {
    // Close dropdown first
    const profileMenu = document.getElementById('profileMenu');
    if (profileMenu) {
      profileMenu.classList.remove('show');
    }

    // Get current user info
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const userId = user.user_id;

    if (!userId) {
      this.showToast('User not found. Please login again.', 'error');
      return;
    }

    // Show password input modal
    const password = await this.showPasswordModal('Enter password to protect your private key:');
    
    if (!password) {
      return; // User cancelled
    }

    try {
      // First, get user attributes
      const userResponse = await fetch(`/api/users/${userId}/attributes`);
      const userData = await userResponse.json();

      if (!userResponse.ok) {
        throw new Error(userData.error || 'Failed to get user attributes');
      }

      const attributes = userData.attributes || [];

      if (attributes.length === 0) {
        this.showToast('No attributes found. Contact admin to set your attributes.', 'error');
        return;
      }

      // Generate private key
      const response = await fetch('/api/user/private-key/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          password: password,
          attributes: attributes
        })
      });

      const result = await response.json();

      if (response.ok) {
        if (result.has_existing_key) {
          this.showToast('Private key already exists. Use authenticate to access it.', 'info');
        } else {
          this.showToast('Private key generated successfully!', 'success');
          this.showPrivateKeyInfo(result);
        }
      } else {
        throw new Error(result.error || 'Failed to generate private key');
      }
    } catch (error) {
      console.error('Get private key error:', error);
      this.showToast(`Error: ${error.message}`, 'error');
    }
  }

  /**
   * Show password input modal
   */
  async showPasswordModal(message) {
    return new Promise((resolve) => {
      // Create modal
      const modal = document.createElement('div');
      modal.className = 'password-modal';
      modal.innerHTML = `
        <div class="modal-backdrop">
          <div class="modal-content">
            <h3>🔐 Private Key Protection</h3>
            <p>${message}</p>
            <input type="password" id="passwordInput" placeholder="Enter password" class="form-input">
            <div class="modal-actions">
              <button id="cancelBtn" class="btn btn-secondary">Cancel</button>
              <button id="confirmBtn" class="btn btn-primary">Generate</button>
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      const passwordInput = modal.querySelector('#passwordInput');
      const cancelBtn = modal.querySelector('#cancelBtn');
      const confirmBtn = modal.querySelector('#confirmBtn');

      // Focus password input
      passwordInput.focus();

      // Handle cancel
      cancelBtn.addEventListener('click', () => {
        document.body.removeChild(modal);
        resolve(null);
      });

      // Handle confirm
      const handleConfirm = () => {
        const password = passwordInput.value.trim();
        if (!password) {
          this.showToast('Password is required', 'error');
          return;
        }
        document.body.removeChild(modal);
        resolve(password);
      };

      confirmBtn.addEventListener('click', handleConfirm);
      passwordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          handleConfirm();
        }
      });

      // Handle escape key
      modal.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          document.body.removeChild(modal);
          resolve(null);
        }
      });
    });
  }

  /**
   * Show private key information
   */
  showPrivateKeyInfo(result) {
    const modal = document.createElement('div');
    modal.className = 'info-modal';
    modal.innerHTML = `
      <div class="modal-backdrop">
        <div class="modal-content large">
          <h3>🔐 Private Key Generated</h3>
          <div class="key-info">
            <p><strong>User ID:</strong> ${result.user_id}</p>
            <p><strong>Attributes:</strong> ${result.attributes.join(', ')}</p>
            <p><strong>Created:</strong> ${new Date().toLocaleString()}</p>
            <p class="success-message">✅ Your private key has been generated and encrypted with your password.</p>
            <p class="info-message">ℹ️ Keep your password safe - you'll need it to decrypt files!</p>
          </div>
          <div class="modal-actions">
            <button id="closeBtn" class="btn btn-primary">Close</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const closeBtn = modal.querySelector('#closeBtn');
    closeBtn.addEventListener('click', () => {
      document.body.removeChild(modal);
    });
  }

  /**
   * Get toast icon
   */
  getToastIcon(type) {
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };
    return icons[type] || icons.info;
  }

  /**
   * Utility: Format file size
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Utility: Format date
   */
  formatDate(dateString, options = {}) {
    const defaultOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    };
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { ...defaultOptions, ...options });
  }

  /**
   * Utility: Debounce function
   */
  debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        timeout = null;
        if (!immediate) func(...args);
      };
      const callNow = immediate && !timeout;
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      if (callNow) func(...args);
    };
  }

  /**
   * Utility: Throttle function
   */
  throttle(func, limit) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
}

// Initialize base app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.baseApp = new BaseApp();
});

// Add CSS for dynamic elements
const dynamicStyles = document.createElement('style');
dynamicStyles.textContent = `
  .spinner-small {
    display: inline-block;
    width: 12px;
    height: 12px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-right: var(--space-xs);
  }

  .toast-content {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
  }

  .toast-close {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: var(--font-size-lg);
    margin-left: auto;
    padding: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: var(--transition);
  }

  .toast-close:hover {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text-primary);
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;
document.head.appendChild(dynamicStyles);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = BaseApp;
}
