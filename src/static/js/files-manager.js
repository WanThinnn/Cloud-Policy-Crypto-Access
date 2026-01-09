// Files Manager - Advanced File Management System
const API_BASE = '/api/storage/';
let currentPath = '';
let currentView = 'grid'; // grid or list
let selectedFiles = new Set();
let allFiles = [];
let currentContextFile = null;
let availableFolders = [];

// Get access token from base template
const accessToken = localStorage.getItem('access_token');
const headers = {
    'Authorization': `Bearer ${accessToken}`
};

// ============= INITIALIZATION =============

if (!accessToken) {
    document.getElementById('files-grid').innerHTML = `
        <div class="col-span-full text-center py-8">
            <p class="text-gray-600 mb-4">Bạn cần đăng nhập để xem trang này</p>
            <a href="/auth/login/" class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-md inline-block">Đăng nhập</a>
        </div>`;
} else {
    loadFolder('');
    setupEventListeners();
}

// ============= EVENT LISTENERS =============

function setupEventListeners() {
    // Search
    document.getElementById('search-input').addEventListener('input', handleSearch);
    
    // View toggle
    document.getElementById('grid-view-btn').addEventListener('click', () => switchView('grid'));
    document.getElementById('list-view-btn').addEventListener('click', () => switchView('list'));
    
    // Upload modal
    document.getElementById('upload-btn').addEventListener('click', openUploadModal);
    document.getElementById('cancel-upload').addEventListener('click', closeUploadModal);
    document.getElementById('upload-form').addEventListener('submit', handleUpload);
    
    // Drag & Drop
    const dropZone = document.getElementById('drop-zone');
    const filesContainer = document.querySelector('.bg-white.shadow.rounded-lg');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        filesContainer.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        filesContainer.addEventListener(eventName, () => {
            dropZone.classList.remove('hidden');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('hidden');
        }, false);
    });
    
    dropZone.addEventListener('drop', handleDrop, false);
    dropZone.addEventListener('click', () => document.getElementById('file-input').click());
    
    // Close context menu on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('#context-menu')) {
            hideContextMenu();
        }
    });
    
    // Close alert on ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.getElementById('alert').classList.add('hidden');
            hideContextMenu();
        }
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// ============= FOLDER & FILE LOADING =============

async function loadFolder(path = '') {
    currentPath = path;
    document.getElementById('current-path').textContent = '/' + (path || '');
    updateBreadcrumb(path);
    
    try {
        showLoading();
        const response = await fetch(`${API_BASE}files/browse/?path=${encodeURIComponent(path)}`, { headers });
        
        if (!response.ok) {
            throw new Error('Failed to load files');
        }
        
        const data = await response.json();
        allFiles = data.files || [];
        renderFiles(allFiles);
        
    } catch (error) {
        console.error('Error loading files:', error);
        showError('Không thể tải danh sách files. Vui lòng thử lại.');
        document.getElementById('files-grid').innerHTML = `
            <div class="col-span-full text-center text-gray-500 py-8">
                <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <p class="text-lg font-medium">Không có files</p>
                <p class="text-sm mt-2">Upload file đầu tiên của bạn!</p>
            </div>`;
    }
}

function updateBreadcrumb(path) {
    const parts = path.split('/').filter(p => p);
    let html = '';
    let cumPath = '';
    
    parts.forEach((part, idx) => {
        cumPath += (idx > 0 ? '/' : '') + part;
        const p = cumPath;
        html += ` <svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"></path></svg>
            <button onclick="loadFolder('${p}')" class="text-indigo-600 hover:text-indigo-800">${part}</button>`;
    });
    
    document.getElementById('breadcrumb').innerHTML = html;
}

// ============= RENDERING =============

function renderFiles(files) {
    if (files.length === 0) {
        document.getElementById('files-grid').innerHTML = `
            <div class="col-span-full text-center text-gray-500 py-8">
                <p>Thư mục trống</p>
            </div>`;
        return;
    }
    
    if (currentView === 'grid') {
        renderGridView(files);
    } else {
        renderListView(files);
    }
}

function renderGridView(files) {
    const container = document.getElementById('files-grid');
    container.innerHTML = files.map(file => {
        const isFolder = file.type === 'folder' || file.name.endsWith('/');
        const icon = isFolder ? getFolderIcon() : getFileIcon(file.name);
        const name = file.name.replace(/\/$/, '');
        const filePath = file.path || name;
        const fileId = btoa(filePath); // base64 encode for ID
        
        return `
            <div class="file-item group relative p-4 border-2 rounded-lg hover:border-indigo-300 hover:shadow-md transition cursor-pointer ${selectedFiles.has(filePath) ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200'}"
                data-path="${filePath}"
                data-type="${isFolder ? 'folder' : 'file'}"
                onclick="handleFileClick('${filePath}', ${isFolder}, event)"
                oncontextmenu="showContextMenu(event, '${filePath}', ${isFolder})">
                
                <!-- Checkbox for bulk selection -->
                ${!isFolder ? `
                <div class="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <input type="checkbox" 
                        class="file-checkbox w-4 h-4 text-indigo-600 rounded"
                        onchange="toggleSelection('${filePath}')"
                        onclick="event.stopPropagation()"
                        ${selectedFiles.has(filePath) ? 'checked' : ''}>
                </div>` : ''}
                
                <!-- File Icon -->
                <div class="text-5xl mb-3 text-center">${icon}</div>
                
                <!-- File Name -->
                <p class="text-sm font-medium text-gray-900 truncate text-center mb-1" title="${name}">${name}</p>
                
                <!-- File Size -->
                ${file.size ? `<p class="text-xs text-gray-500 text-center">${formatSize(file.size)}</p>` : ''}
                
                <!-- Quick Actions (visible on hover) -->
                ${!isFolder ? `
                <div class="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                    <button onclick="previewFile('${filePath}', event)" 
                        class="p-1.5 bg-white rounded-full shadow-md hover:bg-indigo-50" 
                        title="Xem trước">
                        <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                        </svg>
                    </button>
                </div>` : ''}
            </div>
        `;
    }).join('');
}

function renderListView(files) {
    const container = document.getElementById('files-list');
    container.classList.remove('hidden');
    document.getElementById('files-grid').classList.add('hidden');
    
    container.innerHTML = files.map(file => {
        const isFolder = file.type === 'folder' || file.name.endsWith('/');
        const icon = isFolder ? getFolderIcon() : getFileIcon(file.name);
        const name = file.name.replace(/\/$/, '');
        const filePath = file.path || name;
        
        return `
            <div class="file-item flex items-center justify-between p-3 hover:bg-gray-50 cursor-pointer ${selectedFiles.has(filePath) ? 'bg-indigo-50' : ''}"
                data-path="${filePath}"
                onclick="handleFileClick('${filePath}', ${isFolder}, event)"
                oncontextmenu="showContextMenu(event, '${filePath}', ${isFolder})">
                
                <div class="flex items-center gap-3 flex-1">
                    ${!isFolder ? `
                    <input type="checkbox" 
                        class="file-checkbox w-4 h-4 text-indigo-600 rounded"
                        onchange="toggleSelection('${filePath}')"
                        onclick="event.stopPropagation()"
                        ${selectedFiles.has(filePath) ? 'checked' : ''}>
                    ` : ''}
                    <span class="text-2xl">${icon}</span>
                    <span class="font-medium text-gray-900">${name}</span>
                </div>
                
                <div class="flex items-center gap-4">
                    ${file.size ? `<span class="text-sm text-gray-500">${formatSize(file.size)}</span>` : ''}
                    ${!isFolder ? `
                    <div class="flex gap-1">
                        <button onclick="previewFile('${filePath}', event)" 
                            class="p-2 hover:bg-gray-100 rounded" title="Xem trước">
                            <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                            </svg>
                        </button>
                        <button onclick="downloadFile('${filePath}', event)" 
                            class="p-2 hover:bg-gray-100 rounded" title="Download">
                            <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                            </svg>
                        </button>
                    </div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ============= FILE ICONS =============

function getFileIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    const icons = {
        'md': '<svg class="w-full h-full text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z"/><path d="M3 8a2 2 0 012-2v10h8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"/></svg>',
        'txt': '<svg class="w-full h-full text-gray-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>',
        'pdf': '<svg class="w-full h-full text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"/></svg>',
        'doc': '<svg class="w-full h-full text-blue-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>',
        'docx': '<svg class="w-full h-full text-blue-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>',
        'jpg': '<svg class="w-full h-full text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>',
        'png': '<svg class="w-full h-full text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>',
        'gif': '<svg class="w-full h-full text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>',
    };
    return icons[ext] || '<svg class="w-full h-full text-gray-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>';
}

function getFolderIcon() {
    return '<svg class="w-full h-full text-yellow-500" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"/></svg>';
}

// ============= SEARCH =============

function handleSearch(e) {
    const query = e.target.value.toLowerCase().trim();
    
    if (!query) {
        renderFiles(allFiles);
        return;
    }
    
    const filtered = allFiles.filter(file => {
        const name = file.name.toLowerCase();
        return name.includes(query);
    });
    
    renderFiles(filtered);
    
    if (filtered.length === 0) {
        document.getElementById('files-grid').innerHTML = `
            <div class="col-span-full text-center text-gray-500 py-8">
                <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
                <p>Không tìm thấy file nào với từ khóa "<strong>${query}</strong>"</p>
            </div>`;
    }
}

// ============= VIEW SWITCHING =============

function switchView(view) {
    currentView = view;
    
    if (view === 'grid') {
        document.getElementById('grid-view-btn').classList.add('bg-indigo-600', 'text-white');
        document.getElementById('grid-view-btn').classList.remove('bg-white', 'text-gray-700');
        document.getElementById('list-view-btn').classList.remove('bg-indigo-600', 'text-white');
        document.getElementById('list-view-btn').classList.add('bg-white', 'text-gray-700');
        document.getElementById('files-grid').classList.remove('hidden');
        document.getElementById('files-list').classList.add('hidden');
    } else {
        document.getElementById('list-view-btn').classList.add('bg-indigo-600', 'text-white');
        document.getElementById('list-view-btn').classList.remove('bg-white', 'text-gray-700');
        document.getElementById('grid-view-btn').classList.remove('bg-indigo-600', 'text-white');
        document.getElementById('grid-view-btn').classList.add('bg-white', 'text-gray-700');
    }
    
    renderFiles(allFiles);
}

// ============= FILE OPERATIONS =============

function handleFileClick(filePath, isFolder, event) {
    if (event.ctrlKey || event.metaKey) {
        // Ctrl+Click for multi-select
        if (!isFolder) {
            toggleSelection(filePath);
        }
        return;
    }
    
    if (isFolder) {
        loadFolder(filePath);
    } else {
        previewFile(filePath, event);
    }
}

async function downloadFile(filePath, event) {
    if (event) event.stopPropagation();
    
    try {
        showAlert('Đang tải file...', 'info');
        const url = `${API_BASE}files/download_by_path/?path=${encodeURIComponent(filePath)}`;
        
        const response = await fetch(url, { headers });
        
        if (response.status === 403) {
            const error = await response.json();
            showAlert('🚫 ' + (error.error || 'Bạn không có quyền download file này'), 'error');
            return;
        }
        
        if (!response.ok) {
            throw new Error('Download failed');
        }
        
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = filePath.split('/').pop();
        if (contentDisposition) {
            const matches = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (matches && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
        
        showAlert('✅ Download thành công!', 'success');
    } catch (error) {
        console.error('Download error:', error);
        showAlert('❌ Lỗi download: ' + error.message, 'error');
    }
}

async function previewFile(filePath, event) {
    if (event) event.stopPropagation();
    
    currentContextFile = filePath;
    const fileName = filePath.split('/').pop();
    const ext = fileName.split('.').pop().toLowerCase();
    
    document.getElementById('preview-title').textContent = fileName;
    document.getElementById('preview-modal').classList.remove('hidden');
    
    const content = document.getElementById('preview-content');
    
    // Show loading
    content.innerHTML = `
        <div class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>`;
    
    try {
        const url = `${API_BASE}files/download_by_path/?path=${encodeURIComponent(filePath)}`;
        const response = await fetch(url, { headers });
        
        if (response.status === 403) {
            const error = await response.json();
            content.innerHTML = `
                <div class="text-center py-12">
                    <svg class="mx-auto h-16 w-16 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                    </svg>
                    <p class="mt-4 text-red-600 font-medium">🚫 Không có quyền xem file này</p>
                    <p class="mt-2 text-sm text-gray-600">${error.error || 'Access denied'}</p>
                </div>`;
            return;
        }
        
        if (!response.ok) {
            throw new Error('Failed to load file');
        }
        
        // Handle different file types
        if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(ext)) {
            // Image preview
            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);
            content.innerHTML = `
                <div class="text-center">
                    <img src="${imageUrl}" alt="${fileName}" class="max-w-full max-h-[600px] mx-auto rounded-lg shadow-lg">
                </div>`;
        } else if (['md', 'txt'].includes(ext)) {
            // Text preview
            const text = await response.text();
            if (ext === 'md') {
                // Simple markdown rendering
                const html = text
                    .replace(/### (.*)/g, '<h3 class="text-lg font-bold mt-4 mb-2">$1</h3>')
                    .replace(/## (.*)/g, '<h2 class="text-xl font-bold mt-6 mb-3">$1</h2>')
                    .replace(/# (.*)/g, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 rounded">$1</code>')
                    .replace(/\n\n/g, '</p><p class="mb-4">')
                    .replace(/\n/g, '<br>');
                content.innerHTML = `<div class="prose max-w-none"><p class="mb-4">${html}</p></div>`;
            } else {
                content.innerHTML = `<pre class="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded">${text}</pre>`;
            }
        } else if (ext === 'pdf') {
            // PDF preview - show message to download
            content.innerHTML = `
                <div class="text-center py-12">
                    <svg class="mx-auto h-16 w-16 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"/>
                    </svg>
                    <p class="mt-4 text-lg font-medium">PDF File</p>
                    <p class="mt-2 text-sm text-gray-600">Không thể xem trước file PDF trong trình duyệt</p>
                    <button onclick="downloadFromPreview()" class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
                        Download để xem
                    </button>
                </div>`;
        } else {
            // Unsupported format
            content.innerHTML = `
                <div class="text-center py-12">
                    <svg class="mx-auto h-16 w-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                    <p class="mt-4 text-lg font-medium">File: ${fileName}</p>
                    <p class="mt-2 text-sm text-gray-600">Không hỗ trợ xem trước định dạng .${ext}</p>
                    <button onclick="downloadFromPreview()" class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
                        Download
                    </button>
                </div>`;
        }
        
    } catch (error) {
        console.error('Preview error:', error);
        content.innerHTML = `
            <div class="text-center py-12 text-red-600">
                <p>❌ Không thể tải file</p>
                <p class="text-sm mt-2">${error.message}</p>
            </div>`;
    }
}

function closePreview() {
    document.getElementById('preview-modal').classList.add('hidden');
    currentContextFile = null;
}

function downloadFromPreview() {
    if (currentContextFile) {
        downloadFile(currentContextFile);
    }
}

// ============= BULK OPERATIONS =============

function toggleSelection(filePath) {
    if (selectedFiles.has(filePath)) {
        selectedFiles.delete(filePath);
    } else {
        selectedFiles.add(filePath);
    }
    
    updateSelectionUI();
    renderFiles(allFiles);
}

function clearSelection() {
    selectedFiles.clear();
    updateSelectionUI();
    renderFiles(allFiles);
}

function updateSelectionUI() {
    const count = selectedFiles.size;
    const bar = document.getElementById('bulk-actions-bar');
    
    if (count > 0) {
        bar.classList.remove('hidden');
        document.getElementById('selected-count').textContent = count;
    } else {
        bar.classList.add('hidden');
    }
}

async function bulkDownload() {
    if (selectedFiles.size === 0) return;
    
    showAlert(`Đang download ${selectedFiles.size} files...`, 'info');
    
    let success = 0;
    let failed = 0;
    
    for (const filePath of selectedFiles) {
        try {
            await downloadFile(filePath);
            success++;
        } catch (error) {
            failed++;
        }
        // Small delay to avoid overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 300));
    }
    
    showAlert(`✅ Downloaded ${success} files${failed > 0 ? `, ${failed} failed` : ''}`, 'success');
    clearSelection();
}

async function bulkDelete() {
    if (selectedFiles.size === 0) return;
    
    if (!confirm(`Xóa ${selectedFiles.size} files đã chọn?`)) return;
    
    showAlert('Chức năng bulk delete sẽ được implement đầy đủ sau', 'info');
    clearSelection();
}

// ============= UPLOAD =============

async function openUploadModal() {
    document.getElementById('upload-modal').classList.remove('hidden');
    await loadFolderList();
}

function closeUploadModal() {
    document.getElementById('upload-modal').classList.add('hidden');
    document.getElementById('upload-form').reset();
    document.getElementById('upload-progress-container').classList.add('hidden');
}

async function loadFolderList() {
    try {
        const response = await fetch(`${API_BASE}files/browse/?path=`, { headers });
        if (!response.ok) throw new Error('Failed to load folders');
        
        const data = await response.json();
        const folders = data.files.filter(f => f.type === 'folder');
        
        availableFolders = folders.map(f => f.name.replace('/', ''));
        
        const select = document.getElementById('folder-select');
        select.innerHTML = `
            <option value="">/ (Root)</option>
            ${availableFolders.map(folder => 
                `<option value="${folder}">${folder}/</option>`
            ).join('')}
        `;
        
        // Select current folder
        if (currentPath && availableFolders.includes(currentPath.split('/')[0])) {
            select.value = currentPath.split('/')[0];
        }
        
    } catch (error) {
        console.error('Error loading folders:', error);
    }
}

function refreshFolders() {
    loadFolderList();
    showAlert('Đã làm mới danh sách thư mục', 'info');
}

async function handleUpload(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData();
    const fileInput = document.getElementById('file-input');
    const folder = document.getElementById('folder-select').value;
    
    if (!fileInput.files[0]) {
        showAlert('Vui lòng chọn file', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    
    // Prepare form data for API
    formData.append('file', file);
    formData.append('bucket_name', 'documents');
    formData.append('file_path', folder ? `${folder}/${file.name}` : file.name);
    
    try {
        // Show progress bar
        const progressContainer = document.getElementById('upload-progress-container');
        const progressBar = document.getElementById('upload-progress-bar');
        const progressText = document.getElementById('upload-progress-text');
        const submitBtn = document.getElementById('submit-upload');
        
        progressContainer.classList.remove('hidden');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Đang upload...';
        
        // Simulate upload progress (in real scenario, use XMLHttpRequest for progress)
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 10;
            if (progress <= 90) {
                progressBar.style.width = progress + '%';
                progressText.textContent = progress + '%';
            }
        }, 200);
        
        const response = await fetch(`${API_BASE}files/upload/`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${accessToken}` },
            body: formData
        });
        
        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        progressText.textContent = '100%';
        
        if (response.status === 403) {
            const err = await response.json();
            showAlert('🚫 ' + (err.error || 'Bạn không có quyền upload file'), 'error');
            return;
        }
        
        if (response.ok) {
            showAlert('✅ Upload thành công!', 'success');
            closeUploadModal();
            loadFolder(currentPath);
        } else {
            const err = await response.json().catch(() => ({ error: 'Upload thất bại' }));
            showAlert('❌ ' + (err.error || err.detail || 'Upload thất bại'), 'error');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        showAlert('❌ Lỗi upload: ' + error.message, 'error');
    } finally {
        const submitBtn = document.getElementById('submit-upload');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Upload';
        setTimeout(() => {
            document.getElementById('upload-progress-container').classList.add('hidden');
        }, 1000);
    }
}

// ============= DRAG & DROP =============

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    
    if (files.length > 0) {
        document.getElementById('file-input').files = files;
        openUploadModal();
    }
}

// ============= CONTEXT MENU =============

function showContextMenu(event, filePath, isFolder) {
    event.preventDefault();
    
    if (isFolder) return; // No context menu for folders
    
    currentContextFile = filePath;
    const menu = document.getElementById('context-menu');
    
    menu.style.left = event.pageX + 'px';
    menu.style.top = event.pageY + 'px';
    menu.classList.remove('hidden');
}

function hideContextMenu() {
    document.getElementById('context-menu').classList.add('hidden');
}

function contextAction(action) {
    hideContextMenu();
    
    if (!currentContextFile) return;
    
    switch (action) {
        case 'preview':
            previewFile(currentContextFile);
            break;
        case 'download':
            downloadFile(currentContextFile);
            break;
        case 'delete':
            if (confirm('Xóa file này?')) {
                showAlert('Chức năng xóa sẽ được implement đầy đủ sau', 'info');
            }
            break;
    }
}

// ============= UTILITIES =============

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showAlert(message, type = 'info') {
    const alert = document.getElementById('alert');
    const alertMessage = document.getElementById('alert-message');
    
    const colors = {
        success: 'bg-green-50 text-green-800 border-green-200',
        error: 'bg-red-50 text-red-800 border-red-200',
        info: 'bg-blue-50 text-blue-800 border-blue-200'
    };
    
    alert.className = `rounded-md p-4 border relative ${colors[type]}`;
    alertMessage.textContent = message;
    alert.classList.remove('hidden');
    
    // Auto hide after 5 seconds
    setTimeout(() => {
        alert.classList.add('hidden');
    }, 5000);
}

function showLoading() {
    document.getElementById('files-grid').innerHTML = `
        <div class="col-span-full flex justify-center items-center py-12">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>`;
}

function showError(message) {
    showAlert(message, 'error');
}

function createFolder() {
    const name = prompt('Tên thư mục mới:');
    if (!name) return;
    
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
        showAlert('❌ Tên thư mục chỉ được chứa chữ, số, gạch ngang và gạch dưới', 'error');
        return;
    }
    
    showAlert('Chức năng tạo thư mục sẽ được implement sau', 'info');
}

