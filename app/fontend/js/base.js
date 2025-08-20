// Base JavaScript for Cloud Firestore Crypto Access Application

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize theme
    initTheme();
    
    // Setup profile dropdown
    setupProfileDropdown();
    
    // Setup modal handlers
    setupModals();
    
    // Check admin privileges
    checkAdminPrivileges();
}

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme) {
        document.documentElement.className = savedTheme;
    } else if (prefersDark) {
        document.documentElement.className = 'dark-theme';
    } else {
        document.documentElement.className = 'light-theme';
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.className;
    const newTheme = currentTheme === 'dark-theme' ? 'light-theme' : 'dark-theme';
    
    document.documentElement.className = newTheme;
    localStorage.setItem('theme', newTheme);
}

// Profile Dropdown Management
function setupProfileDropdown() {
    const profileBtn = document.getElementById('profileBtn');
    const profileDropdown = document.querySelector('.profile-dropdown');
    
    if (profileBtn && profileDropdown) {
        profileBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleDropdown(profileDropdown);
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!profileDropdown.contains(e.target)) {
                closeDropdown(profileDropdown);
            }
        });
    }
}

function toggleDropdown(dropdown) {
    dropdown.classList.toggle('active');
}

function closeDropdown(dropdown) {
    dropdown.classList.remove('active');
}

// GetPrivateKey Functionality
async function handleGetPrivateKey() {
    try {
        // Close profile dropdown
        const profileDropdown = document.querySelector('.profile-dropdown');
        if (profileDropdown) {
            closeDropdown(profileDropdown);
        }
        
        // Show the private key modal
        showPrivateKeyModal();
        
    } catch (error) {
        console.error('Error handling GetPrivateKey:', error);
        alert('Error: Unable to process GetPrivateKey request');
    }
}

function showPrivateKeyModal() {
    const modal = document.getElementById('privateKeyModal');
    const passwordStep = document.getElementById('passwordStep');
    const resultStep = document.getElementById('resultStep');
    const alertDiv = document.getElementById('privateKeyAlert');
    
    if (modal) {
        // Reset modal state
        passwordStep.style.display = 'block';
        resultStep.style.display = 'none';
        alertDiv.innerHTML = '';
        document.getElementById('privateKeyPassword').value = '';
        
        // Show modal
        modal.style.display = 'flex';
        setTimeout(() => {
            modal.classList.add('active');
        }, 10);
    }
}

function closePrivateKeyModal() {
    const modal = document.getElementById('privateKeyModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    }
}

async function generatePrivateKey() {
    const password = document.getElementById('privateKeyPassword').value;
    const alertDiv = document.getElementById('privateKeyAlert');
    
    if (!password) {
        showAlert(alertDiv, 'Please enter a password to protect your private key', 'error');
        return;
    }
    
    try {
        // Step 1: Get user attributes
        showAlert(alertDiv, 'Fetching user attributes...', 'info');
        
        const attributesResponse = await fetch('/api/auth/me');
        if (!attributesResponse.ok) {
            throw new Error('Failed to get user information');
        }
        
        const userData = await attributesResponse.json();
        if (!userData.success) {
            throw new Error(userData.error || 'Failed to get user information');
        }
        
        // Step 2: Generate private key
        showAlert(alertDiv, 'Generating private key...', 'info');
        
        const generateResponse = await fetch('/api/ca/user/private-key/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userData.user_id || userData.id,
                password: password,
                attributes: userData.attributes || []
            })
        });
        
        const generateResult = await generateResponse.json();
        
        if (generateResult.success) {
            // Show success and private key info
            showPrivateKeyResult(generateResult);
        } else {
            showAlert(alertDiv, generateResult.error || 'Failed to generate private key', 'error');
        }
        
    } catch (error) {
        console.error('Error generating private key:', error);
        showAlert(alertDiv, 'Error generating private key: ' + error.message, 'error');
    }
}

function showPrivateKeyResult(result) {
    const passwordStep = document.getElementById('passwordStep');
    const resultStep = document.getElementById('resultStep');
    const resultDiv = document.getElementById('privateKeyResult');
    
    // Switch to result step
    passwordStep.style.display = 'none';
    resultStep.style.display = 'block';
    
    // Display result
    resultDiv.innerHTML = `
        <div class="alert alert-success">
            <h4>Private Key Generated Successfully!</h4>
            <p><strong>Key ID:</strong> ${result.key_id}</p>
            <p><strong>Generated:</strong> ${new Date(result.created_at).toLocaleString()}</p>
            <p><strong>Attributes:</strong> ${result.attributes ? result.attributes.join(', ') : 'None'}</p>
            <div style="margin-top: 1rem; padding: 1rem; background: var(--card-background); border-radius: 8px;">
                <strong>Encrypted Private Key:</strong>
                <pre style="margin-top: 0.5rem; white-space: pre-wrap; word-break: break-all; font-family: monospace; font-size: 0.8rem;">${result.encrypted_private_key}</pre>
            </div>
            <div style="margin-top: 1rem;">
                <small><strong>Note:</strong> Your private key has been encrypted with the password you provided. Keep this key safe and secure.</small>
            </div>
        </div>
    `;
}

// Logout Functionality
async function handleLogout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            window.location.href = '/login';
        } else {
            console.error('Logout failed:', data.error);
            window.location.href = '/login'; // Force redirect anyway
        }
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/login'; // Force redirect anyway
    }
}

// Modal Management
function setupModals() {
    // Close modals when clicking backdrop
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal-backdrop')) {
            const modal = e.target;
            modal.classList.remove('active');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
        }
    });
    
    // Handle ESC key for modals
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const activeModal = document.querySelector('.modal-backdrop.active');
            if (activeModal) {
                activeModal.classList.remove('active');
                setTimeout(() => {
                    activeModal.style.display = 'none';
                }, 300);
            }
        }
    });
}

// Admin Privilege Check
async function checkAdminPrivileges() {
    try {
        const response = await fetch('/api/admin/health');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                // User has admin privileges
                document.querySelectorAll('.admin-only').forEach(el => {
                    el.style.display = 'block';
                });
            }
        }
    } catch (error) {
        // Not admin or error - keep admin elements hidden
        console.debug('Admin check failed (expected for non-admin users)');
    }
}

// Utility Functions
function showAlert(container, message, type = 'info') {
    if (!container) return;
    
    const alertClass = `alert alert-${type}`;
    container.innerHTML = `<div class="${alertClass}">${message}</div>`;
    
    // Auto-hide success messages after 5 seconds
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            if (container.innerHTML.includes(message)) {
                container.innerHTML = '';
            }
        }, 5000);
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// API Helper Functions
async function apiCall(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    };
    
    const response = await fetch(url, { ...defaultOptions, ...options });
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
    }
    
    return data;
}

// Export functions for use in other scripts
window.App = {
    toggleTheme,
    handleGetPrivateKey,
    handleLogout,
    showAlert,
    formatDate,
    formatBytes,
    apiCall
};

// Make functions globally available (for onclick handlers)
window.toggleTheme = toggleTheme;
window.handleGetPrivateKey = handleGetPrivateKey;
window.handleLogout = handleLogout;
window.generatePrivateKey = generatePrivateKey;
window.closePrivateKeyModal = closePrivateKeyModal;
