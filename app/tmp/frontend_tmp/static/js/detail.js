/**
 * DETAIL PAGE JAVASCRIPT
 * Handles interactive elements for detail pages
 */

class DetailPage {
  constructor() {
    this.currentTab = 'overview';
    this.init();
  }

  init() {
    this.bindEvents();
    this.animateElements();
    this.initTabs();
    this.updateProgressBars();
    this.setupDataTables();
  }

  /**
   * Bind event listeners
   */
  bindEvents() {
    // Tab navigation
    this.setupTabNavigation();

    // Action buttons
    this.setupActionButtons();

    // Data refresh
    const refreshBtn = document.querySelector('.refresh-detail-data');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        this.refreshDetailData();
      });
    }

    // Modal handlers
    this.setupModals();

    // Form submissions
    this.setupForms();
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

    // Observe all sections
    document.querySelectorAll('.content-section, .sidebar-card').forEach(section => {
      observer.observe(section);
    });
  }

  /**
   * Initialize tab system
   */
  initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    if (tabButtons.length > 0) {
      // Show first tab by default
      tabButtons[0].classList.add('active');
      if (tabContents.length > 0) {
        tabContents[0].classList.add('active');
      }
    }
  }

  /**
   * Setup tab navigation
   */
  setupTabNavigation() {
    const tabButtons = document.querySelectorAll('.tab-button');
    
    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const targetTab = button.getAttribute('data-tab');
        this.switchTab(targetTab);
      });
    });
  }

  /**
   * Switch to specific tab
   */
  switchTab(tabId) {
    // Remove active class from all tabs and contents
    document.querySelectorAll('.tab-button').forEach(btn => {
      btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
      content.classList.remove('active');
    });

    // Add active class to selected tab and content
    const activeButton = document.querySelector(`[data-tab="${tabId}"]`);
    const activeContent = document.getElementById(tabId);

    if (activeButton) activeButton.classList.add('active');
    if (activeContent) activeContent.classList.add('active');

    this.currentTab = tabId;

    // Trigger custom event
    this.triggerEvent('tabChanged', { tabId });
  }

  /**
   * Setup action buttons
   */
  setupActionButtons() {
    // Edit buttons
    document.querySelectorAll('.btn-edit').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const entityType = btn.getAttribute('data-entity');
        const entityId = btn.getAttribute('data-id');
        this.handleEdit(entityType, entityId);
      });
    });

    // Delete buttons
    document.querySelectorAll('.btn-delete').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const entityType = btn.getAttribute('data-entity');
        const entityId = btn.getAttribute('data-id');
        this.handleDelete(entityType, entityId);
      });
    });

    // Download buttons
    document.querySelectorAll('.btn-download').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const fileId = btn.getAttribute('data-file-id');
        this.handleDownload(fileId);
      });
    });
  }

  /**
   * Handle edit action
   */
  handleEdit(entityType, entityId) {
    this.showNotification(`Opening ${entityType} editor...`, 'info');
    
    // Simulate loading
    this.showLoading();
    
    setTimeout(() => {
      this.hideLoading();
      // Redirect to edit page or open modal
      window.location.href = `/${entityType}/${entityId}/edit`;
    }, 1000);
  }

  /**
   * Handle delete action
   */
  handleDelete(entityType, entityId) {
    const confirmed = confirm(`Are you sure you want to delete this ${entityType}? This action cannot be undone.`);
    
    if (confirmed) {
      this.showNotification(`Deleting ${entityType}...`, 'warning');
      this.showLoading();

      // Simulate API call
      setTimeout(() => {
        this.hideLoading();
        this.showNotification(`${entityType} deleted successfully!`, 'success');
        
        // Redirect back to list page
        setTimeout(() => {
          window.location.href = `/${entityType}s`;
        }, 1500);
      }, 2000);
    }
  }

  /**
   * Handle download action
   */
  handleDownload(fileId) {
    this.showNotification('Preparing download...', 'info');
    
    // Create download link
    const downloadUrl = `/api/files/${fileId}/download`;
    
    // Simulate download preparation
    setTimeout(() => {
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `file_${fileId}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      this.showNotification('Download started!', 'success');
    }, 1000);
  }

  /**
   * Update progress bars with animation
   */
  updateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-fill-detailed');
    
    progressBars.forEach(bar => {
      const targetWidth = bar.getAttribute('data-progress') || '0%';
      
      // Animate progress bar
      setTimeout(() => {
        bar.style.width = targetWidth;
      }, 500);
    });
  }

  /**
   * Setup data tables
   */
  setupDataTables() {
    const tables = document.querySelectorAll('.data-table');
    
    tables.forEach(table => {
      // Add hover effects
      const rows = table.querySelectorAll('tbody tr');
      rows.forEach(row => {
        row.addEventListener('click', () => {
          const itemId = row.getAttribute('data-id');
          if (itemId) {
            this.handleTableRowClick(itemId);
          }
        });
      });
      
      // Make tables responsive
      this.makeTableResponsive(table);
    });
  }

  /**
   * Handle table row clicks
   */
  handleTableRowClick(itemId) {
    console.log('Table row clicked:', itemId);
    // Implementation depends on the specific use case
  }

  /**
   * Make table responsive
   */
  makeTableResponsive(table) {
    const wrapper = document.createElement('div');
    wrapper.className = 'table-wrapper';
    wrapper.style.overflowX = 'auto';
    wrapper.style.marginTop = 'var(--space-lg)';
    
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  }

  /**
   * Setup modals
   */
  setupModals() {
    // Modal triggers
    document.querySelectorAll('[data-modal-target]').forEach(trigger => {
      trigger.addEventListener('click', (e) => {
        e.preventDefault();
        const modalId = trigger.getAttribute('data-modal-target');
        this.openModal(modalId);
      });
    });

    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(closeBtn => {
      closeBtn.addEventListener('click', () => {
        this.closeAllModals();
      });
    });

    // Close modal on backdrop click
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-backdrop')) {
        this.closeAllModals();
      }
    });

    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeAllModals();
      }
    });
  }

  /**
   * Open modal
   */
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = 'flex';
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }

  /**
   * Close all modals
   */
  closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
      modal.style.display = 'none';
      modal.classList.remove('active');
    });
    document.body.style.overflow = 'auto';
  }

  /**
   * Setup forms
   */
  setupForms() {
    document.querySelectorAll('form[data-ajax]').forEach(form => {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleAjaxForm(form);
      });
    });
  }

  /**
   * Handle AJAX form submission
   */
  async handleAjaxForm(form) {
    const formData = new FormData(form);
    const action = form.getAttribute('action') || window.location.pathname;
    const method = form.getAttribute('method') || 'POST';

    this.showLoading();

    try {
      const response = await fetch(action, {
        method: method,
        body: formData
      });

      const result = await response.json();

      if (response.ok) {
        this.showNotification(result.message || 'Operation completed successfully!', 'success');
        
        // Refresh page data if needed
        if (result.refresh) {
          this.refreshDetailData();
        }
        
        // Close modal if form is in modal
        if (form.closest('.modal')) {
          this.closeAllModals();
        }
      } else {
        throw new Error(result.message || 'Operation failed');
      }
    } catch (error) {
      console.error('Form submission error:', error);
      this.showNotification(error.message || 'An error occurred', 'error');
    } finally {
      this.hideLoading();
    }
  }

  /**
   * Refresh detail data
   */
  refreshDetailData() {
    this.showNotification('Refreshing data...', 'info');
    this.showLoading();

    // Simulate data refresh
    setTimeout(() => {
      this.hideLoading();
      this.updateProgressBars();
      this.showNotification('Data refreshed successfully!', 'success');
      
      // Trigger refresh event
      this.triggerEvent('dataRefreshed');
    }, 2000);
  }

  /**
   * Show loading overlay
   */
  showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
      overlay.classList.add('active');
    }
  }

  /**
   * Hide loading overlay
   */
  hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
      overlay.classList.remove('active');
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
   * Get notification icon
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
   * Trigger custom event
   */
  triggerEvent(eventName, data = {}) {
    const event = new CustomEvent(eventName, { detail: data });
    document.dispatchEvent(event);
  }

  /**
   * Utility function to format dates
   */
  formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Utility function to format file sizes
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new DetailPage();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = DetailPage;
}
