/**
 * HOME PAGE JAVASCRIPT
 * Handles interactive elements and data updates for the home page
 */

class HomePage {
  constructor() {
    this.apiBaseUrl = '/api';
    this.init();
  }

  init() {
    this.bindEvents();
    this.animateElements();
    this.loadDashboardData();
    this.initCharts();
    this.setupProgressBars();
    this.setupAutoRefresh();
  }

  /**
   * Load dashboard data from backend API
   */
  async loadDashboardData() {
    try {
      this.showLoading(true);
      
      // Fetch dashboard data from multiple endpoints
      const [filesData, usersData, systemData] = await Promise.allSettled([
        this.fetchFiles(),
        this.fetchUsers(),
        this.fetchSystemStats()
      ]);
      
      // Update dashboard with real data
      if (filesData.status === 'fulfilled') {
        this.updateFilesStats(filesData.value);
      }
      
      if (usersData.status === 'fulfilled') {
        this.updateUsersStats(usersData.value);
      }
      
      if (systemData.status === 'fulfilled') {
        this.updateSystemStats(systemData.value);
      }
      
      this.updateStats();
      
    } catch (error) {
      console.error('Dashboard data load error:', error);
      this.showNotification('Failed to load dashboard data', 'error');
    } finally {
      this.showLoading(false);
    }
  }

  /**
   * Fetch files from API
   */
  async fetchFiles() {
    const response = await fetch(`${this.apiBaseUrl}/files?user_id=current`);
    if (!response.ok) throw new Error('Failed to fetch files');
    return await response.json();
  }

  /**
   * Fetch users from API (admin only)
   */
  async fetchUsers() {
    try {
      const response = await fetch(`${this.apiBaseUrl}/admin/users`);
      if (!response.ok) throw new Error('Failed to fetch users');
      return await response.json();
    } catch (error) {
      // Not admin user, return empty data
      return { users: [], total: 0 };
    }
  }

  /**
   * Fetch system statistics
   */
  async fetchSystemStats() {
    try {
      const response = await fetch(`${this.apiBaseUrl}/admin/stats`);
      if (!response.ok) throw new Error('Failed to fetch system stats');
      return await response.json();
    } catch (error) {
      // Return mock data if API not available
      return {
        storage_used: 2400000000, // 2.4GB in bytes
        storage_total: 5000000000, // 5GB in bytes
        uptime: 99.9,
        response_time: 1.2,
        security_score: 98
      };
    }
  }

  /**
   * Update files statistics
   */
  updateFilesStats(data) {
    const totalFiles = data.files?.length || 0;
    const totalFilesElement = document.querySelector('[data-value="1247"]');
    if (totalFilesElement) {
      totalFilesElement.setAttribute('data-value', totalFiles.toString());
    }
  }

  /**
   * Update users statistics  
   */
  updateUsersStats(data) {
    const totalUsers = data.total || 0;
    const usersElement = document.querySelector('[data-value="89"]');
    if (usersElement) {
      usersElement.setAttribute('data-value', totalUsers.toString());
    }
  }

  /**
   * Update system statistics
   */
  updateSystemStats(data) {
    // Update storage usage
    if (data.storage_used && data.storage_total) {
      const percentage = Math.round((data.storage_used / data.storage_total) * 100);
      const progressBar = document.querySelector('.progress-fill[data-progress="48%"]');
      if (progressBar) {
        progressBar.setAttribute('data-progress', `${percentage}%`);
      }
    }
    
    // Update other metrics
    if (data.uptime) {
      const uptimeElement = document.querySelector('.stat-number:contains("99.9%")');
      if (uptimeElement) {
        uptimeElement.textContent = `${data.uptime}%`;
      }
    }
  }

  /**
   * Setup auto refresh
   */
  setupAutoRefresh() {
    // Refresh dashboard data every 5 minutes
    setInterval(() => {
      this.loadDashboardData();
    }, 5 * 60 * 1000);
  }

  /**
   * Show/hide loading state
   */
  showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
      if (show) {
        overlay.classList.add('active');
      } else {
        overlay.classList.remove('active');
      }
    }
  }

  /**
   * Bind event listeners
   */
  bindEvents() {
    // Navigation highlighting
    this.highlightCurrentNav();

    // Card hover effects
    this.setupCardHoverEffects();

    // Refresh data button
    const refreshBtn = document.querySelector('.refresh-data');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        this.refreshDashboardData();
      });
    }

    // Quick action cards
    this.setupQuickActions();
  }

  /**
   * Animate elements on page load
   */
  animateElements() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('fade-in');
        }
      });
    }, {
      threshold: 0.1
    });

    // Observe all bento cards
    document.querySelectorAll('.bento-card').forEach(card => {
      observer.observe(card);
    });

    // Observe quick action cards
    document.querySelectorAll('.quick-action-card').forEach(card => {
      observer.observe(card);
    });
  }

  /**
   * Highlight current navigation item
   */
  highlightCurrentNav() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
      if (item.querySelector('a').getAttribute('href') === '/') {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  }

  /**
   * Setup card hover effects
   */
  setupCardHoverEffects() {
    document.querySelectorAll('.bento-card').forEach(card => {
      card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-4px) scale(1.02)';
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'translateY(0) scale(1)';
      });
    });
  }

  /**
   * Update statistics with animation
   */
  updateStats() {
    const statNumbers = document.querySelectorAll('.stat-number');
    
    statNumbers.forEach(stat => {
      const targetValue = parseInt(stat.getAttribute('data-value') || stat.textContent.replace(/,/g, ''));
      const duration = 2000; // 2 seconds
      const increment = targetValue / (duration / 16); // 60fps
      let current = 0;

      const timer = setInterval(() => {
        current += increment;
        if (current >= targetValue) {
          current = targetValue;
          clearInterval(timer);
        }
        stat.textContent = this.formatNumber(Math.floor(current));
      }, 16);
    });
  }

  /**
   * Initialize charts (placeholder for actual chart libraries)
   */
  initCharts() {
    // This is where you would integrate with Chart.js, D3.js, or other charting libraries
    const chartContainers = document.querySelectorAll('.chart-container');
    
    chartContainers.forEach(container => {
      // Simulate chart creation
      this.createMockChart(container);
    });
  }

  /**
   * Create a simple mock chart visualization
   */
  createMockChart(container) {
    const canvas = document.createElement('canvas');
    canvas.width = container.offsetWidth;
    canvas.height = container.offsetHeight;
    container.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
    gradient.addColorStop(0, 'rgba(102, 126, 234, 0.8)');
    gradient.addColorStop(1, 'rgba(118, 75, 162, 0.8)');

    // Draw simple line chart
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    const points = 20;
    for (let i = 0; i < points; i++) {
      const x = (canvas.width / points) * i;
      const y = canvas.height / 2 + Math.sin(i * 0.5) * 30 + Math.random() * 20 - 10;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    
    ctx.stroke();
  }

  /**
   * Setup progress bars
   */
  setupProgressBars() {
    const progressBars = document.querySelectorAll('.progress-fill');
    
    progressBars.forEach(bar => {
      const targetWidth = bar.getAttribute('data-progress') || '75%';
      
      // Animate progress bar
      setTimeout(() => {
        bar.style.width = targetWidth;
      }, 500);
    });
  }

  /**
   * Setup quick action interactions
   */
  setupQuickActions() {
    document.querySelectorAll('.quick-action-card').forEach(card => {
      card.addEventListener('click', (e) => {
        e.preventDefault();
        const action = card.getAttribute('data-action');
        this.handleQuickAction(action);
      });
    });
  }

  /**
   * Handle quick action clicks
   */
  handleQuickAction(action) {
    switch (action) {
      case 'upload':
        this.showNotification('Redirecting to file upload...', 'info');
        setTimeout(() => window.location.href = '/upload', 500);
        break;
      case 'manage-users':
        this.showNotification('Opening user management...', 'info');
        setTimeout(() => window.location.href = '/users', 500);
        break;
      case 'security':
        this.showNotification('Opening security settings...', 'info');
        setTimeout(() => window.location.href = '/security', 500);
        break;
      case 'analytics':
        this.showNotification('Loading analytics...', 'info');
        setTimeout(() => window.location.href = '/analytics', 500);
        break;
      default:
        console.log('Unknown action:', action);
    }
  }

  /**
   * Refresh dashboard data
   */
  async refreshDashboardData() {
    this.showNotification('Refreshing dashboard data...', 'info');
    
    try {
      await this.loadDashboardData();
      this.showNotification('Dashboard data updated successfully!', 'success');
    } catch (error) {
      this.showNotification('Failed to refresh dashboard data', 'error');
    }
  }

  /**
   * Show notification
   */
  showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
      <div class="notification-content">
        <span class="notification-icon">${this.getNotificationIcon(type)}</span>
        <span class="notification-message">${message}</span>
      </div>
    `;

    // Add styles
    notification.style.cssText = `
      position: fixed;
      top: 100px;
      right: 20px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--border-radius);
      padding: var(--space-md);
      backdrop-filter: blur(20px);
      box-shadow: var(--shadow-soft);
      z-index: 10000;
      transform: translateX(100%);
      transition: var(--transition);
      max-width: 300px;
    `;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
      notification.style.transform = 'translateX(0)';
    }, 100);

    // Remove after delay
    setTimeout(() => {
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 3000);
  }

  /**
   * Get notification icon based on type
   */
  getNotificationIcon(type) {
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };
    return icons[type] || icons.info;
  }

  /**
   * Format numbers with commas
   */
  formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  /**
   * Utility function to make API calls
   */
  async makeApiCall(endpoint, options = {}) {
    try {
      const response = await fetch(endpoint, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API call failed:', error);
      this.showNotification('Failed to fetch data', 'error');
      throw error;
    }
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new HomePage();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HomePage;
}
