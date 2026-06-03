// Files Manager - Advanced File Management System
(function () {
    'use strict';

    // Prevent double loading
    if (window.filesManagerLoaded) return;
    window.filesManagerLoaded = true;

    const API_BASE = '/api/storage/';
    let currentPath = '';
    let currentView = 'grid'; // grid or list
    let selectedFiles = new Set();
    let allFiles = [];
    let currentContextFile = null;
    let availableFolders = [];
    let userPermissions = null;
    let availablePolicies = []; // Cache available policies

    // Get access token from localStorage
    const accessToken = localStorage.getItem('access_token');
    const headers = {
        'Authorization': `Bearer ${accessToken}`
    };

    // ============= INITIALIZATION =============

    async function initFileManager() {
        if (!accessToken) {
            showAuthRequired();
            return;
        }

        // Check user permissions first
        try {
            const permResponse = await fetch('/api/auth/permissions/', { headers });
            if (permResponse.status === 401) {
                showAuthRequired();
                return;
            }
            userPermissions = await permResponse.json();
            
            // Update UI based on permissions
            updateUIForPermissions();
            
            // Load files
            await loadFolder('');
            setupEventListeners();
        } catch (error) {
            console.error('Init error:', error);
            showError('Không thể kết nối đến server');
        }
    }

    function showAuthRequired() {
        document.getElementById('files-grid').innerHTML = `
        <div class="col-span-full text-center py-12">
            <div class="text-6xl mb-4">🔐</div>
            <p class="text-gray-600 mb-4">Bạn cần đăng nhập để xem trang này</p>
            <a href="/auth/login/?next=${encodeURIComponent(location.pathname)}" class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-md inline-block">Đăng nhập</a>
        </div>`;
        // Hide upload button
        const uploadBtn = document.getElementById('upload-btn');
        if (uploadBtn) uploadBtn.classList.add('hidden');
    }

    function updateUIForPermissions() {
        // Show/hide upload button based on permission
        const uploadBtn = document.getElementById('upload-btn');
        if (uploadBtn) {
            // User needs file_upload or file_create permission
            const canUpload = userPermissions.can_upload_files !== false;
            uploadBtn.classList.toggle('hidden', !canUpload);
        }
    }

    // Start initialization
    initFileManager();

    // ============= EVENT LISTENERS =============

    function setupEventListeners() {
        // Search
        document.getElementById('search-input').addEventListener('input', handleSearch);

        // View toggle
        document.getElementById('grid-view-btn').addEventListener('click', () => switchView('grid'));
        document.getElementById('list-view-btn').addEventListener('click', () => switchView('list'));

        // Preview modal buttons
        const btnCloseTop = document.getElementById('btn-close-preview-top');
        if (btnCloseTop) btnCloseTop.addEventListener('click', closePreview);
        const btnCloseBottom = document.getElementById('btn-close-preview-bottom');
        if (btnCloseBottom) btnCloseBottom.addEventListener('click', closePreview);
        const btnDownloadPreview = document.getElementById('btn-download-preview');
        if (btnDownloadPreview) btnDownloadPreview.addEventListener('click', downloadFromPreview);

        // Upload modal
        document.getElementById('upload-btn').addEventListener('click', openUploadModal);
        document.getElementById('cancel-upload').addEventListener('click', closeUploadModal);
        document.getElementById('upload-form').addEventListener('submit', handleUpload);

        // Drag & Drop
        const dropZone = document.getElementById('drop-zone');
        const filesContainer = document.getElementById('files-container');

        if (filesContainer) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                filesContainer.addEventListener(eventName, preventDefaults, false);
                document.body.addEventListener(eventName, preventDefaults, false);
            });

            ['dragenter', 'dragover'].forEach(eventName => {
                filesContainer.addEventListener(eventName, () => {
                    if (dropZone) dropZone.classList.remove('hidden');
                }, false);
            });
        }

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

        // Modal Drop Zone logic
        const modalDropZone = document.getElementById('modal-drop-zone');
        const fileInput = document.getElementById('file-input');
        const fileSelectedName = document.getElementById('file-selected-name');

        if (modalDropZone && fileInput) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                modalDropZone.addEventListener(eventName, preventDefaults, false);
            });

            ['dragenter', 'dragover'].forEach(eventName => {
                modalDropZone.addEventListener(eventName, () => {
                    modalDropZone.classList.add('border-indigo-500', 'bg-indigo-50');
                }, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                modalDropZone.addEventListener(eventName, () => {
                    modalDropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
                }, false);
            });

            modalDropZone.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                if (dt.files && dt.files.length > 0) {
                    fileInput.files = dt.files;
                    updateFileSelectedName();
                }
            }, false);

            modalDropZone.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', updateFileSelectedName);

            function updateFileSelectedName() {
                if (fileInput.files && fileInput.files.length > 0) {
                    fileSelectedName.textContent = `Đã chọn: ${fileInput.files[0].name}`;
                    fileSelectedName.classList.remove('hidden');
                } else {
                    fileSelectedName.classList.add('hidden');
                }
            }
        }
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // ============= FOLDER & FILE LOADING =============

    async function loadFolder(path = '') {
        currentPath = path;
        // document.getElementById('current-path').textContent = '/' + (path || '');
        updateBreadcrumb(path);

        try {
            showLoading();
            const url = `${API_BASE}files/browse/?path=${encodeURIComponent(path)}&bucket=documents`;
            console.log('Loading folder:', url);
            const response = await fetch(url, { headers });

            if (!response.ok) {
                // Check for specific error codes
                if (response.status === 403) {
                    const err = await response.json().catch(() => ({ error: 'Access denied' }));
                    console.error('ABAC denied:', err);
                    document.getElementById('files-grid').innerHTML = `
                    <div class="col-span-full text-center text-gray-500 py-8">
                        <svg class="mx-auto h-12 w-12 text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                        </svg>
                        <p class="text-lg font-medium text-red-600">Truy cập bị từ chối</p>
                        <p class="text-sm mt-2">${err.error || 'Bạn không có quyền xem tài liệu này'}</p>
                        <p class="text-xs mt-4 text-gray-400">Resource: ${err.resource || 'document'} | Action: ${err.action || 'read'}</p>
                    </div>`;
                    return;
                }
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

        if (parts.length === 0) {
            document.getElementById('breadcrumb').innerHTML = '<span class="text-gray-400 italic">/</span>';
            return;
        }

        parts.forEach((part, idx) => {
            cumPath += (idx > 0 ? '/' : '') + part;
            const p = cumPath;
            const isLast = idx === parts.length - 1;

            html += `
            <svg class="w-4 h-4 text-gray-400 mx-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
            <button onclick="loadFolder('${p}')" 
                class="${isLast ? 'font-bold text-gray-900 pointer-events-none' : 'text-gray-500 hover:text-indigo-600 hover:underline transition-colors'}">
                ${part}
            </button>`;
        });

        document.getElementById('breadcrumb').innerHTML = html;
    }

    // ============= RENDERING =============

    function renderFiles(files) {
        if (files.length === 0) {
            document.getElementById('files-grid').innerHTML = `
            <div class="col-span-full flex flex-col items-center justify-center py-24 text-gray-500">
                <div class="bg-gray-50 p-6 rounded-full mb-4">
                    <svg class="h-16 w-16 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
                    </svg>
                </div>
                <p class="text-xl font-medium text-gray-600">Thư mục trống</p>
                <p class="text-sm mt-2 text-gray-400">Hãy upload tài liệu mới để bắt đầu</p>
            </div>`;
            document.getElementById('files-list').innerHTML = document.getElementById('files-grid').innerHTML;
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
            let filePath = isFolder ? (currentPath ? `${currentPath}/${name}` : name) : (file.path || (currentPath ? `${currentPath}/${name}` : name));
            const isSelected = selectedFiles.has(filePath);

            return `
            <div class="file-item group relative flex flex-col p-4 bg-white border border-gray-100 rounded-2xl transition-all duration-300 hover:shadow-xl hover:-translate-y-1 hover:border-indigo-200 cursor-pointer ${isSelected ? 'ring-2 ring-indigo-500 bg-indigo-50/50' : ''}"
                onclick="handleFileClick('${filePath}', ${isFolder}, event)"
                oncontextmenu="showContextMenu(event, '${filePath}', ${isFolder})">
                
                <!-- Selection Checkbox -->
                <div class="absolute top-4 left-4 z-20 opacity-0 group-hover:opacity-100 transition-opacity ${isSelected ? 'opacity-100' : ''}" onclick="event.stopPropagation()">
                   <div class="checkbox-wrapper relative w-5 h-5">
                       <input type="checkbox" 
                           class="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                           onchange="toggleSelection('${filePath}')"
                           onclick="event.stopPropagation()"
                           ${isSelected ? 'checked' : ''}>
                   </div>
                </div>
                
                <!-- Icon Area -->
                <div class="h-32 mb-4 rounded-xl bg-gray-50/80 group-hover:bg-indigo-50/30 flex items-center justify-center transition-colors relative overflow-hidden">
                    <div class="transform transition-transform duration-300 group-hover:scale-110 drop-shadow-sm w-16 h-16">
                        ${icon}
                    </div>
                    
                    <!-- Hover Actions Overlay -->
                    ${!isFolder ? `
                    <div class="absolute inset-0 bg-black/40 backdrop-blur-[1px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                        <button onclick="previewFile('${filePath}', event)" 
                            class="p-2 bg-white text-gray-700 rounded-full hover:text-indigo-600 hover:scale-110 transition-transform shadow-lg" title="Xem trước">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                        </button>
                        <button onclick="downloadFile('${filePath}', event)" 
                            class="p-2 bg-white text-gray-700 rounded-full hover:text-green-600 hover:scale-110 transition-transform shadow-lg" title="Download">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                        </button>
                    </div>
                    ` : ''}
                </div>
                
                <!-- Info Area -->
                <div class="text-center">
                    <h3 class="text-sm font-semibold text-gray-700 truncate px-2 mb-1 group-hover:text-indigo-700 transition-colors" title="${name}">${name}</h3>
                    <p class="text-xs text-gray-400">
                        ${file.size ? formatSize(file.size) : (isFolder ? (file.items !== undefined ? `${file.items} items` : '') : '')}
                    </p>
                </div>
            </div>
        `;
        }).join('');
    }

    function renderListView(files) {
        const container = document.getElementById('files-list');
        container.classList.remove('hidden');
        document.getElementById('files-grid').classList.add('hidden');

        // Header Row
        const header = `
        <div class="flex items-center px-6 py-3 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            <div class="w-8 ml-2">#</div>
            <div class="flex-1">Tên</div>
            <div class="w-32">Kích thước</div>
            <div class="w-32">Loại</div>
            <div class="w-24 text-right">Hành động</div>
        </div>
    `;

        container.innerHTML = header + files.map(file => {
            const isFolder = file.type === 'folder' || file.name.endsWith('/');
            const icon = isFolder ? getFolderIcon() : getFileIcon(file.name);
            const name = file.name.replace(/\/$/, '');
            let filePath = isFolder ? (currentPath ? `${currentPath}/${name}` : name) : (file.path || (currentPath ? `${currentPath}/${name}` : name));
            const isSelected = selectedFiles.has(filePath);

            return `
            <div class="file-item group flex items-center px-6 py-4 hover:bg-indigo-50/30 transition-colors border-b border-gray-100 last:border-0 cursor-pointer ${isSelected ? 'bg-indigo-50/60' : ''}"
                onclick="handleFileClick('${filePath}', ${isFolder}, event)"
                oncontextmenu="showContextMenu(event, '${filePath}', ${isFolder})">
                
                <div class="w-8 flex items-center justify-center mr-2" onclick="event.stopPropagation()">
                    <input type="checkbox" 
                        class="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 opacity-0 group-hover:opacity-100 ${isSelected ? 'opacity-100' : ''}"
                        onchange="toggleSelection('${filePath}')"
                        onclick="event.stopPropagation()"
                        ${isSelected ? 'checked' : ''}>
                </div>
                
                <div class="flex-1 flex items-center gap-4">
                    <div class="w-10 h-10 flex items-center justify-center bg-gray-100 rounded-lg text-gray-500">
                        <div class="w-6 h-6">${icon}</div>
                    </div>
                    <div>
                        <p class="font-medium text-gray-900 group-hover:text-indigo-700 transition-colors">${name}</p>
                        ${isFolder ? '<p class="text-xs text-gray-500">Thư mục</p>' : ''}
                    </div>
                </div>
                
                <div class="w-32 text-sm text-gray-500 font-mono">
                    ${file.size ? formatSize(file.size) : '-'}
                </div>
                
                <div class="w-32 text-sm text-gray-500">
                    ${isFolder ? 'Folder' : name.split('.').pop().toUpperCase()}
                </div>
                
                <div class="w-24 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    ${!isFolder ? `
                        <button onclick="previewFile('${filePath}', event)" class="p-1.5 text-gray-500 hover:text-indigo-600 bg-white hover:bg-gray-100 rounded-lg shadow-sm border border-gray-200" title="Xem">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                        </button>
                        <button onclick="downloadFile('${filePath}', event)" class="p-1.5 text-gray-500 hover:text-green-600 bg-white hover:bg-gray-100 rounded-lg shadow-sm border border-gray-200" title="Download">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                        </button>
                    ` : ''}
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
            document.getElementById('grid-view-btn').classList.add('bg-white', 'shadow-sm', 'text-indigo-600');
            document.getElementById('grid-view-btn').classList.remove('text-gray-500');
            document.getElementById('list-view-btn').classList.remove('bg-white', 'shadow-sm', 'text-indigo-600');
            document.getElementById('list-view-btn').classList.add('text-gray-500');

            document.getElementById('files-grid').classList.remove('hidden');
            document.getElementById('files-list').classList.add('hidden');
        } else {
            document.getElementById('list-view-btn').classList.add('bg-white', 'shadow-sm', 'text-indigo-600');
            document.getElementById('list-view-btn').classList.remove('text-gray-500');
            document.getElementById('grid-view-btn').classList.remove('bg-white', 'shadow-sm', 'text-indigo-600');
            document.getElementById('grid-view-btn').classList.add('text-gray-500');

            document.getElementById('files-list').classList.remove('hidden');
            document.getElementById('files-grid').classList.add('hidden');
        }

        renderFiles(allFiles);
    }

    // ============= FILE OPERATIONS =============

    function handleFileClick(filePath, isFolder, event) {
        // Check if click is on checkbox - let checkbox handle it
        if (event.target.type === 'checkbox' || event.target.closest('.checkbox-wrapper')) {
            return;
        }

        // Ctrl+Click or Shift+Click for multi-select
        if (event.ctrlKey || event.metaKey || event.shiftKey) {
            toggleSelection(filePath);
            return;
        }

        // Single click - open file/folder immediately
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
            const url = `${API_BASE}files/download_by_path/?path=${encodeURIComponent(filePath)}&bucket=documents`;

            console.log('Downloading from:', url);
            const response = await fetch(url, { headers });

            if (response.status === 403) {
                const error = await response.json().catch(() => ({ error: 'Access denied' }));
                showAlert('🚫 ' + (error.error || 'Bạn không có quyền download file này'), 'error');
                return;
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: response.statusText }));
                throw new Error(errorData.error || 'Download failed');
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
            const url = `${API_BASE}files/preview_by_path/?path=${encodeURIComponent(filePath)}&bucket=documents`;
            console.log('Previewing file:', url);
            const response = await fetch(url, { headers });

            if (response.status === 403) {
                const error = await response.json().catch(() => ({ error: 'Access denied' }));
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
                const errorData = await response.json().catch(() => ({ error: response.statusText }));
                console.error('Preview error:', errorData);
                throw new Error(errorData.error || 'Failed to load file');
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
                // PDF preview using iframe
                const blob = await response.blob();
                const pdfUrl = URL.createObjectURL(blob);
                content.innerHTML = `
                <div style="width: 100%; height: 75vh; min-height: 500px;">
                    <iframe src="${pdfUrl}#toolbar=0" style="width: 100%; height: 100%; border: none; border-radius: 0.5rem;" type="application/pdf" title="${fileName}"></iframe>
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
        document.getElementById('preview-content').innerHTML = '';
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

        if (!confirm(`Chuyển ${selectedFiles.size} files đã chọn vào thùng rác?`)) return;

        showAlert(`Đang chuyển ${selectedFiles.size} files vào thùng rác...`, 'info');

        let success = 0;
        let failed = 0;

        for (const filePath of selectedFiles) {
            try {
                const url = `${API_BASE}files/delete_by_path/?path=${encodeURIComponent(filePath)}&bucket=documents`;
                const response = await fetch(url, { 
                    method: 'DELETE',
                    headers 
                });
                
                if (response.ok) {
                    success++;
                } else if (response.status === 403) {
                    failed++;
                    showAlert('🚫 Bạn không có quyền xóa một số files', 'error');
                } else {
                    failed++;
                }
            } catch (error) {
                failed++;
            }
            await new Promise(resolve => setTimeout(resolve, 200));
        }

        showAlert(`✅ Đã chuyển ${success} files vào thùng rác${failed > 0 ? `, ${failed} thất bại` : ''}`, 'success');
        clearSelection();
        loadFolder(currentPath);
    }

    async function deleteFile(filePath) {
        if (!confirm(`Chuyển file này vào thùng rác?`)) return;
        
        showAlert(`Đang chuyển file vào thùng rác...`, 'info');
        
        try {
            const url = `${API_BASE}files/delete_by_path/?path=${encodeURIComponent(filePath)}&bucket=documents`;
            const response = await fetch(url, { 
                method: 'DELETE',
                headers 
            });
            
            if (response.ok) {
                showAlert(`✅ Đã chuyển file vào thùng rác`, 'success');
                loadFolder(currentPath);
            } else if (response.status === 403) {
                showAlert('🚫 Bạn không có quyền xóa file này', 'error');
            } else {
                showAlert('❌ Lỗi chuyển file vào thùng rác', 'error');
            }
        } catch (error) {
            showAlert('❌ Lỗi chuyển file vào thùng rác: ' + error.message, 'error');
        }
    }

    // ============= UPLOAD =============

    async function openUploadModal() {
        document.getElementById('upload-modal').classList.remove('hidden');
        
        document.getElementById('new-policy-form-upload').classList.add('hidden');
        if (!document.getElementById('file-input').files.length) {
            document.getElementById('file-selected-name').classList.add('hidden');
        }
        
        // Update destination folder badge
        document.getElementById('upload-destination-folder').textContent = currentPath ? `/${currentPath}` : '/ (Root)';
        
        // Load policies
        await loadPoliciesForUpload();
    }

    function closeUploadModal() {
        document.getElementById('upload-modal').classList.add('hidden');
        document.getElementById('upload-form').reset();
        document.getElementById('upload-progress-container').classList.add('hidden');
        document.getElementById('new-policy-form-upload').classList.add('hidden');
    }
    
    async function loadPoliciesForUpload() {
        const select = document.getElementById('upload-policy-select');
        select.innerHTML = '<option value="">Đang tải policies...</option>';
        
        try {
            const response = await fetch(`${API_BASE}files/available_policies/`, { headers });
            if (response.ok) {
                const policies = await response.json();
                select.innerHTML = `
                    <option value="">-- Không gán policy (sử dụng ABAC mặc định) --</option>
                    ${policies.map(p => `
                        <option value="${p.id}" data-effect="${p.effect}">
                            ${escapeHtml(p.name)} (${p.effect === 'allow' ? '✓ Allow' : '✕ Deny'})
                        </option>
                    `).join('')}
                `;
            } else {
                select.innerHTML = '<option value="">-- Không gán policy --</option>';
            }
        } catch (error) {
            console.error('Error loading policies:', error);
            select.innerHTML = '<option value="">-- Không gán policy --</option>';
        }
    }
    
    // ============= POLICY BUILDER LOGIC =============
    // These will be loaded dynamically from database
    let AVAILABLE_ATTRIBUTES = [];

    const OPERATORS = [
        { key: '==', label: 'bằng' },
        { key: '!=', label: 'khác' },
        { key: 'in', label: 'thuộc danh sách' },
        { key: 'not in', label: 'không thuộc danh sách' },
    ];

    let uploadRuleCounter = 0;
    let assignRuleCounter = 0;
    let uploadAdvancedMode = false;
    let assignAdvancedMode = false;
    let policyBuilderAttributesLoaded = false;

    // Load attributes from database for Policy Builder
    async function loadPolicyBuilderAttributes() {
        if (policyBuilderAttributesLoaded && AVAILABLE_ATTRIBUTES.length > 0) {
            return AVAILABLE_ATTRIBUTES;
        }
        
        try {
            console.log('Loading policy builder attributes...');
            const response = await fetch('/api/admin/policy-builder-attributes/', { 
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                }
            });
            console.log('Response status:', response.status);
            if (response.ok) {
                AVAILABLE_ATTRIBUTES = await response.json();
                policyBuilderAttributesLoaded = true;
                console.log('Loaded policy builder attributes:', AVAILABLE_ATTRIBUTES);
            } else {
                console.error('Failed to load policy builder attributes:', response.status);
                // Fallback to empty - user will need to use advanced mode
                AVAILABLE_ATTRIBUTES = [];
            }
        } catch (error) {
            console.error('Error loading policy builder attributes:', error);
            AVAILABLE_ATTRIBUTES = [];
        }
        return AVAILABLE_ATTRIBUTES;
    }

    function createRuleHTML(prefix, ruleId) {
        const attrOptions = AVAILABLE_ATTRIBUTES.map(a => 
            `<option value="${a.key}">${a.label}</option>`
        ).join('');
        
        const opOptions = OPERATORS.map(o => 
            `<option value="${o.key}">${o.label}</option>`
        ).join('');

        return `
            <div class="${prefix}-rule-wrapper" data-rule-id="${ruleId}">
                <div class="connector-row flex items-center justify-center py-1 ${ruleId === 1 ? 'hidden' : ''}" data-rule-id="${ruleId}">
                    <select class="connector-select bg-gray-100 border border-gray-300 rounded px-2 py-0.5 text-xs font-medium" 
                        data-rule-id="${ruleId}" onchange="${prefix === 'upload' ? 'updateUploadPreview()' : 'updateAssignPreview()'}">
                        <option value="and" class="text-green-700">VÀ (AND)</option>
                        <option value="or" class="text-orange-700">HOẶC (OR)</option>
                    </select>
                </div>
                <div class="${prefix}-rule flex items-center gap-2 p-2 bg-white rounded border text-sm" data-rule-id="${ruleId}">
                    <span class="text-xs text-gray-600">Nếu</span>
                    <select class="attr-select border border-gray-300 rounded px-2 py-1 text-xs" data-rule-id="${ruleId}"
                        onchange="${prefix}UpdateValueSelector(${ruleId})">
                        ${attrOptions}
                    </select>
                    <select class="op-select border border-gray-300 rounded px-2 py-1 text-xs" data-rule-id="${ruleId}"
                        onchange="${prefix}UpdateValueSelector(${ruleId})">
                        ${opOptions}
                    </select>
                    <div class="value-container flex-1" data-rule-id="${ruleId}">
                    </div>
                    <button type="button" class="remove-rule-btn text-red-500 hover:text-red-700" 
                        onclick="${prefix}RemoveRule(${ruleId})">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }

    // Upload Policy Builder functions
    async function addUploadRule() {
        console.log('addUploadRule called');
        // Ensure attributes are loaded
        await loadPolicyBuilderAttributes();
        console.log('Attributes loaded, count:', AVAILABLE_ATTRIBUTES.length);
        
        if (AVAILABLE_ATTRIBUTES.length === 0) {
            showAlert('⚠️ Không có thuộc tính nào. Vui lòng sử dụng chế độ nâng cao.', 'warning');
            return;
        }
        
        const container = document.getElementById('upload-condition-rules');
        console.log('Container found:', container);
        const ruleId = ++uploadRuleCounter;
        const ruleHTML = createRuleHTML('upload', ruleId);
        console.log('Rule HTML created for ruleId:', ruleId);
        container.insertAdjacentHTML('beforeend', ruleHTML);
        uploadUpdateValueSelector(ruleId);
        console.log('Rule added successfully');
    }

    function uploadUpdateValueSelector(ruleId) {
        const wrapper = document.querySelector(`.upload-rule-wrapper[data-rule-id="${ruleId}"]`);
        const rule = wrapper.querySelector('.upload-rule');
        const attrSelect = rule.querySelector('.attr-select');
        const opSelect = rule.querySelector('.op-select');
        const valueContainer = wrapper.querySelector(`.value-container[data-rule-id="${ruleId}"]`);
        
        const selectedAttr = AVAILABLE_ATTRIBUTES.find(a => a.key === attrSelect.value);
        if (!selectedAttr) return;
        
        const isMultiSelect = opSelect.value === 'in' || opSelect.value === 'not in';
        const attrValues = selectedAttr.values || [];

        if (isMultiSelect) {
            valueContainer.innerHTML = `
                <div class="flex flex-wrap gap-1">
                    ${attrValues.map(v => `
                        <label class="inline-flex items-center bg-gray-100 rounded px-1.5 py-0.5 text-xs cursor-pointer hover:bg-gray-200">
                            <input type="checkbox" class="value-checkbox mr-1 w-3 h-3" value="${v}" onchange="updateUploadPreview()">
                            ${v}
                        </label>
                    `).join('')}
                </div>
            `;
        } else {
            valueContainer.innerHTML = `
                <select class="value-select border border-gray-300 rounded px-2 py-1 text-xs" onchange="updateUploadPreview()">
                    ${attrValues.map(v => `<option value="${v}">${v}</option>`).join('')}
                </select>
            `;
        }
        updateUploadPreview();
    }

    function uploadRemoveRule(ruleId) {
        const wrapper = document.querySelector(`.upload-rule-wrapper[data-rule-id="${ruleId}"]`);
        if (wrapper) wrapper.remove();
        uploadUpdateConnectorVisibility();
        updateUploadPreview();
    }

    function uploadUpdateConnectorVisibility() {
        const wrappers = document.querySelectorAll('.upload-rule-wrapper');
        wrappers.forEach((wrapper, index) => {
            const connectorRow = wrapper.querySelector('.connector-row');
            if (connectorRow) {
                connectorRow.classList.toggle('hidden', index === 0);
            }
        });
    }

    function buildUploadCondition() {
        const wrappers = document.querySelectorAll('.upload-rule-wrapper');
        const parts = [];

        wrappers.forEach((wrapper, index) => {
            const rule = wrapper.querySelector('.upload-rule');
            const attr = rule.querySelector('.attr-select').value;
            const op = rule.querySelector('.op-select').value;
            
            let value;
            if (op === 'in' || op === 'not in') {
                const checkboxes = rule.querySelectorAll('.value-checkbox:checked');
                const values = Array.from(checkboxes).map(cb => `'${cb.value}'`);
                if (values.length === 0) return;
                value = `[${values.join(', ')}]`;
            } else {
                const select = rule.querySelector('.value-select');
                if (!select) return;
                value = `'${select.value}'`;
            }

            const condition = `r.sub.${attr} ${op} ${value}`;
            
            if (index > 0) {
                const connectorSelect = wrapper.querySelector('.connector-select');
                const connector = connectorSelect ? connectorSelect.value : 'and';
                parts.push(` ${connector} `);
            }
            parts.push(condition);
        });

        return parts.join('');
    }

    function updateUploadPreview() {
        const preview = document.getElementById('upload-condition-preview');
        const condition = uploadAdvancedMode 
            ? document.getElementById('upload-new-policy-condition').value
            : buildUploadCondition();
        
        if (condition) {
            preview.textContent = condition;
            preview.classList.remove('text-gray-400');
            preview.classList.add('text-green-700');
        } else {
            preview.textContent = '(Chưa có điều kiện nào)';
            preview.classList.remove('text-green-700');
            preview.classList.add('text-gray-400');
        }
        
        document.getElementById('upload-policy-condition-final').value = condition;
    }

    function updateUploadPreviewFromAdvanced() {
        updateUploadPreview();
    }

    function toggleUploadAdvancedMode() {
        uploadAdvancedMode = !uploadAdvancedMode;
        const simpleMode = document.getElementById('upload-simple-mode');
        const advancedMode = document.getElementById('upload-advanced-mode');
        const toggleBtn = document.getElementById('upload-toggle-advanced');

        if (uploadAdvancedMode) {
            const builtCondition = buildUploadCondition();
            document.getElementById('upload-new-policy-condition').value = builtCondition;
            
            simpleMode.classList.add('hidden');
            advancedMode.classList.remove('hidden');
            toggleBtn.textContent = 'Chế độ đơn giản';
        } else {
            simpleMode.classList.remove('hidden');
            advancedMode.classList.add('hidden');
            toggleBtn.textContent = 'Chế độ nâng cao';
        }
        updateUploadPreview();
    }

    // Assign Policy Builder functions (similar but with different prefix)
    async function addAssignRule() {
        // Ensure attributes are loaded
        await loadPolicyBuilderAttributes();
        
        if (AVAILABLE_ATTRIBUTES.length === 0) {
            showAlert('⚠️ Không có thuộc tính nào. Vui lòng sử dụng chế độ nâng cao.', 'warning');
            return;
        }
        
        const container = document.getElementById('assign-condition-rules');
        const ruleId = ++assignRuleCounter;
        container.insertAdjacentHTML('beforeend', createRuleHTML('assign', ruleId));
        assignUpdateValueSelector(ruleId);
    }

    function assignUpdateValueSelector(ruleId) {
        const wrapper = document.querySelector(`.assign-rule-wrapper[data-rule-id="${ruleId}"]`);
        const rule = wrapper.querySelector('.assign-rule');
        const attrSelect = rule.querySelector('.attr-select');
        const opSelect = rule.querySelector('.op-select');
        const valueContainer = wrapper.querySelector(`.value-container[data-rule-id="${ruleId}"]`);
        
        const selectedAttr = AVAILABLE_ATTRIBUTES.find(a => a.key === attrSelect.value);
        if (!selectedAttr) return;
        
        const isMultiSelect = opSelect.value === 'in' || opSelect.value === 'not in';

        if (isMultiSelect) {
            valueContainer.innerHTML = `
                <div class="flex flex-wrap gap-1">
                    ${(selectedAttr.values || []).map(v => `
                        <label class="inline-flex items-center bg-gray-100 rounded px-1.5 py-0.5 text-xs cursor-pointer hover:bg-gray-200">
                            <input type="checkbox" class="value-checkbox mr-1 w-3 h-3" value="${v}" onchange="updateAssignPreview()">
                            ${v}
                        </label>
                    `).join('')}
                </div>
            `;
        } else {
            valueContainer.innerHTML = `
                <select class="value-select border border-gray-300 rounded px-2 py-1 text-xs" onchange="updateAssignPreview()">
                    ${(selectedAttr.values || []).map(v => `<option value="${v}">${v}</option>`).join('')}
                </select>
            `;
        }
        updateAssignPreview();
    }

    function assignRemoveRule(ruleId) {
        const wrapper = document.querySelector(`.assign-rule-wrapper[data-rule-id="${ruleId}"]`);
        if (wrapper) wrapper.remove();
        assignUpdateConnectorVisibility();
        updateAssignPreview();
    }

    function assignUpdateConnectorVisibility() {
        const wrappers = document.querySelectorAll('.assign-rule-wrapper');
        wrappers.forEach((wrapper, index) => {
            const connectorRow = wrapper.querySelector('.connector-row');
            if (connectorRow) {
                connectorRow.classList.toggle('hidden', index === 0);
            }
        });
    }

    function buildAssignCondition() {
        const wrappers = document.querySelectorAll('.assign-rule-wrapper');
        const parts = [];

        wrappers.forEach((wrapper, index) => {
            const rule = wrapper.querySelector('.assign-rule');
            const attr = rule.querySelector('.attr-select').value;
            const op = rule.querySelector('.op-select').value;
            
            let value;
            if (op === 'in' || op === 'not in') {
                const checkboxes = rule.querySelectorAll('.value-checkbox:checked');
                const values = Array.from(checkboxes).map(cb => `'${cb.value}'`);
                if (values.length === 0) return;
                value = `[${values.join(', ')}]`;
            } else {
                const select = rule.querySelector('.value-select');
                if (!select) return;
                value = `'${select.value}'`;
            }

            const condition = `r.sub.${attr} ${op} ${value}`;
            
            if (index > 0) {
                const connectorSelect = wrapper.querySelector('.connector-select');
                const connector = connectorSelect ? connectorSelect.value : 'and';
                parts.push(` ${connector} `);
            }
            parts.push(condition);
        });

        return parts.join('');
    }

    function updateAssignPreview() {
        const preview = document.getElementById('assign-condition-preview');
        const condition = assignAdvancedMode 
            ? document.getElementById('new-policy-condition').value
            : buildAssignCondition();
        
        if (condition) {
            preview.textContent = condition;
            preview.classList.remove('text-gray-400');
            preview.classList.add('text-green-700');
        } else {
            preview.textContent = '(Chưa có điều kiện nào)';
            preview.classList.remove('text-green-700');
            preview.classList.add('text-gray-400');
        }
        
        document.getElementById('assign-policy-condition-final').value = condition;
    }

    function updateAssignPreviewFromAdvanced() {
        updateAssignPreview();
    }

    function toggleAssignAdvancedMode() {
        assignAdvancedMode = !assignAdvancedMode;
        const simpleMode = document.getElementById('assign-simple-mode');
        const advancedMode = document.getElementById('assign-advanced-mode');
        const toggleBtn = document.getElementById('assign-toggle-advanced');

        if (assignAdvancedMode) {
            const builtCondition = buildAssignCondition();
            document.getElementById('new-policy-condition').value = builtCondition;
            
            simpleMode.classList.add('hidden');
            advancedMode.classList.remove('hidden');
            toggleBtn.textContent = 'Chế độ đơn giản';
        } else {
            simpleMode.classList.remove('hidden');
            advancedMode.classList.add('hidden');
            toggleBtn.textContent = 'Chế độ nâng cao';
        }
        updateAssignPreview();
    }
    
    function toggleNewPolicyForm() {
        const form = document.getElementById('new-policy-form-upload');
        form.classList.toggle('hidden');
        
        if (!form.classList.contains('hidden')) {
            // Clear existing policy selection when creating new
            document.getElementById('upload-policy-select').value = '';
            // Initialize with one rule if empty
            if (document.querySelectorAll('.upload-rule-wrapper').length === 0) {
                addUploadRule();
            }
        }
    }
    
    async function assignPolicyToUploadedFile(filePath, policyId, isCreatingNew) {
        try {
            let payload = {
                file_path: filePath,
                bucket_name: 'documents',
                target_type: 'file',
                notes: 'Assigned during upload'
            };
            
            if (isCreatingNew) {
                // Create new policy with all fields from Policy Builder
                const name = document.getElementById('upload-new-policy-name').value.trim();
                const condition = document.getElementById('upload-policy-condition-final').value.trim() 
                    || document.getElementById('upload-new-policy-condition')?.value.trim() || '';
                const effect = document.getElementById('upload-new-policy-effect').value;
                const description = document.getElementById('upload-new-policy-description')?.value.trim() || `Policy for file: ${filePath}`;
                const priority = parseInt(document.getElementById('upload-new-policy-priority')?.value) || 100;
                const resource = document.getElementById('upload-new-policy-resource')?.value || 'document';
                const action = document.getElementById('upload-new-policy-action')?.value || 'read';
                
                if (!name || !condition) {
                    console.warn('New policy info incomplete, skipping policy assignment');
                    return;
                }
                
                payload.create_new_policy = true;
                payload.new_policy_name = name;
                payload.new_policy_description = description;
                payload.new_policy_subject_condition = condition;
                payload.new_policy_effect = effect;
                payload.new_policy_priority = priority;
                payload.new_policy_resource = resource;
                payload.new_policy_action = action;
            } else if (policyId) {
                payload.policy_id = parseInt(policyId);
            } else {
                return; // No policy to assign
            }
            
            const response = await fetch(`${API_BASE}files/assign_policy/`, {
                method: 'POST',
                headers: {
                    ...headers,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (response.ok) {
                console.log('Policy assigned to uploaded file');
            } else {
                const err = await response.json().catch(() => ({}));
                console.error('Failed to assign policy:', err);
                // Don't show error - upload was successful, policy assignment is optional
            }
        } catch (error) {
            console.error('Error assigning policy:', error);
        }
    }



    async function handleUpload(e) {
        e.preventDefault();

        const form = e.target;
        const formData = new FormData();
        const fileInput = document.getElementById('file-input');
        const folder = currentPath;

        if (!fileInput.files[0]) {
            showAlert('Vui lòng chọn file', 'error');
            return;
        }

        const file = fileInput.files[0];

        // Prepare form data for API
        formData.append('file', file);
        formData.append('bucket_name', 'documents');
        formData.append('file_path', folder ? `${folder}/${file.name}` : file.name);
        formData.append('is_public', 'false');

        console.log('Uploading file:', file.name, 'to path:', folder ? `${folder}/${file.name}` : file.name);

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

            console.log('Upload response status:', response.status);

            if (response.status === 403) {
                const err = await response.json().catch(() => ({ error: 'Access denied' }));
                showAlert('🚫 ' + (err.error || 'Bạn không có quyền upload file'), 'error');
                console.error('Upload forbidden:', err);
                return;
            }

            if (response.ok) {
                const result = await response.json();
                console.log('Upload successful:', result);
                
                // Get the uploaded file path from the response (database path)
                const uploadedFilePath = result.file_path;
                
                // Check if user wants to assign a policy
                const policySelect = document.getElementById('upload-policy-select');
                const selectedPolicyId = policySelect.value;
                const newPolicyForm = document.getElementById('new-policy-form-upload');
                const isCreatingNewPolicy = !newPolicyForm.classList.contains('hidden');
                
                if (selectedPolicyId || isCreatingNewPolicy) {
                    // Assign policy to the uploaded file
                    await assignPolicyToUploadedFile(uploadedFilePath, selectedPolicyId, isCreatingNewPolicy);
                }
                
                showAlert('✅ Upload thành công!', 'success');
                closeUploadModal();
                loadFolder(currentPath);
            } else {
                const err = await response.json().catch(() => ({ error: 'Upload thất bại' }));
                console.error('Upload error:', err);
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
            const fileSelectedName = document.getElementById('file-selected-name');
            if (fileSelectedName) {
                fileSelectedName.textContent = `Đã chọn: ${files[0].name}`;
                fileSelectedName.classList.remove('hidden');
            }
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
                deleteFile(currentContextFile);
                break;
            case 'assign_policy':
                openAssignPolicyModal(currentContextFile);
                break;
            case 'view_policies':
                openViewPoliciesModal(currentContextFile);
                break;
        }
    }

    // ============= POLICY ASSIGNMENT =============
    
    let selectedPolicyId = null;
    let currentPolicyTab = 'existing';
    let assigningFilePath = null;
    
    async function loadAvailablePolicies() {
        try {
            const response = await fetch(`${API_BASE}files/available_policies/`, { headers });
            if (response.ok) {
                availablePolicies = await response.json();
                renderPoliciesList(availablePolicies);
            }
        } catch (error) {
            console.error('Error loading policies:', error);
        }
    }
    
    function renderPoliciesList(policies) {
        const container = document.getElementById('policies-list');
        
        if (!policies || policies.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <svg class="w-12 h-12 mx-auto text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                    <p>Chưa có policy nào.</p>
                    <p class="text-sm">Chuyển sang tab "Tạo Policy mới" để tạo.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = policies.map(policy => `
            <div class="policy-item border rounded-lg p-3 cursor-pointer hover:bg-indigo-50 hover:border-indigo-300 transition-all ${selectedPolicyId === policy.id ? 'bg-indigo-50 border-indigo-500 ring-2 ring-indigo-500' : ''}"
                 onclick="selectPolicy(${policy.id})">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2">
                            <span class="font-medium text-gray-900">${escapeHtml(policy.name)}</span>
                            <span class="px-2 py-0.5 text-xs rounded-full ${policy.effect === 'allow' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">
                                ${policy.effect === 'allow' ? '✓ Allow' : '✕ Deny'}
                            </span>
                        </div>
                        <p class="text-sm text-gray-500 mt-1">${escapeHtml(policy.description || 'Không có mô tả')}</p>
                        <div class="flex items-center gap-4 mt-2 text-xs text-gray-400">
                            <span>Resource: ${policy.resource}</span>
                            <span>Action: ${policy.action}</span>
                        </div>
                    </div>
                    <div class="ml-2">
                        ${selectedPolicyId === policy.id 
                            ? '<svg class="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
                            : '<div class="w-6 h-6 border-2 border-gray-300 rounded-full"></div>'
                        }
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    function selectPolicy(policyId) {
        selectedPolicyId = policyId;
        renderPoliciesList(availablePolicies);
    }
    
    function filterPolicies(query) {
        const filtered = availablePolicies.filter(p => 
            p.name.toLowerCase().includes(query.toLowerCase()) ||
            (p.description && p.description.toLowerCase().includes(query.toLowerCase()))
        );
        renderPoliciesList(filtered);
    }
    
    function switchPolicyTab(tab) {
        currentPolicyTab = tab;
        
        // Update tab styles
        document.getElementById('tab-existing').classList.toggle('border-indigo-600', tab === 'existing');
        document.getElementById('tab-existing').classList.toggle('text-indigo-600', tab === 'existing');
        document.getElementById('tab-existing').classList.toggle('border-transparent', tab !== 'existing');
        document.getElementById('tab-existing').classList.toggle('text-gray-500', tab !== 'existing');
        
        document.getElementById('tab-new').classList.toggle('border-indigo-600', tab === 'new');
        document.getElementById('tab-new').classList.toggle('text-indigo-600', tab === 'new');
        document.getElementById('tab-new').classList.toggle('border-transparent', tab !== 'new');
        document.getElementById('tab-new').classList.toggle('text-gray-500', tab !== 'new');
        
        // Show/hide panels
        document.getElementById('panel-existing').classList.toggle('hidden', tab !== 'existing');
        document.getElementById('panel-new').classList.toggle('hidden', tab !== 'new');
        
        // Initialize Policy Builder when switching to new tab
        if (tab === 'new' && document.querySelectorAll('.assign-rule-wrapper').length === 0) {
            addAssignRule();
        }
    }
    
    async function openAssignPolicyModal(filePath) {
        assigningFilePath = filePath;
        selectedPolicyId = null;
        currentPolicyTab = 'existing';
        
        // Reset form
        document.getElementById('policy-search').value = '';
        document.getElementById('new-policy-name').value = '';
        document.getElementById('new-policy-description').value = '';
        const conditionInput = document.getElementById('new-policy-condition');
        if (conditionInput) conditionInput.value = '';
        document.getElementById('assign-notes').value = '';
        
        // Reset Policy Builder
        document.getElementById('assign-condition-rules').innerHTML = '';
        assignRuleCounter = 0;
        assignAdvancedMode = false;
        const simpleMode = document.getElementById('assign-simple-mode');
        const advancedMode = document.getElementById('assign-advanced-mode');
        if (simpleMode) simpleMode.classList.remove('hidden');
        if (advancedMode) advancedMode.classList.add('hidden');
        const toggleBtn = document.getElementById('assign-toggle-advanced');
        if (toggleBtn) toggleBtn.textContent = 'Chế độ nâng cao';
        
        // Reset dropdowns
        const effectSelect = document.getElementById('new-policy-effect');
        if (effectSelect) effectSelect.value = 'allow';
        const resourceSelect = document.getElementById('new-policy-resource');
        if (resourceSelect) resourceSelect.value = 'document';
        const actionSelect = document.getElementById('new-policy-action');
        if (actionSelect) actionSelect.value = 'read';
        const priorityInput = document.getElementById('new-policy-priority');
        if (priorityInput) priorityInput.value = '100';
        
        // Update file name display
        const fileName = filePath.split('/').pop();
        document.getElementById('assign-policy-file-name').textContent = `File: ${fileName}`;
        
        // Show modal
        document.getElementById('assign-policy-modal').classList.remove('hidden');
        
        // Load policies
        switchPolicyTab('existing');
        await loadAvailablePolicies();
    }
    
    function closeAssignPolicyModal() {
        document.getElementById('assign-policy-modal').classList.add('hidden');
        assigningFilePath = null;
        selectedPolicyId = null;
    }
    
    async function submitAssignPolicy() {
        if (!assigningFilePath) return;
        
        const btn = document.getElementById('submit-assign-policy');
        btn.disabled = true;
        btn.innerHTML = '<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div> Đang xử lý...';
        
        try {
            let payload = {
                file_path: assigningFilePath,
                bucket_name: 'documents',
                target_type: 'file',
                notes: document.getElementById('assign-notes').value,
                replace: document.getElementById('assign-replace-policy')?.checked || false
            };
            
            if (currentPolicyTab === 'existing') {
                if (!selectedPolicyId) {
                    showAlert('❌ Vui lòng chọn một policy', 'error');
                    return;
                }
                payload.policy_id = selectedPolicyId;
            } else {
                // Create new policy with all fields from Policy Builder
                const name = document.getElementById('new-policy-name').value.trim();
                const condition = document.getElementById('assign-policy-condition-final').value.trim() 
                    || document.getElementById('new-policy-condition')?.value.trim() || '';
                const effect = document.getElementById('new-policy-effect').value;
                const description = document.getElementById('new-policy-description')?.value.trim() || '';
                const priority = parseInt(document.getElementById('new-policy-priority')?.value) || 100;
                const resource = document.getElementById('new-policy-resource')?.value || 'document';
                const action = document.getElementById('new-policy-action')?.value || 'read';
                
                if (!name || !condition) {
                    showAlert('❌ Vui lòng điền đầy đủ thông tin policy (tên và điều kiện)', 'error');
                    return;
                }
                
                payload.create_new_policy = true;
                payload.new_policy_name = name;
                payload.new_policy_description = description;
                payload.new_policy_subject_condition = condition;
                payload.new_policy_effect = effect;
                payload.new_policy_priority = priority;
                payload.new_policy_resource = resource;
                payload.new_policy_action = action;
            }
            
            const response = await fetch(`${API_BASE}files/assign_policy/`, {
                method: 'POST',
                headers: {
                    ...headers,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showAlert('✅ Đã gán quyền thành công', 'success');
                closeAssignPolicyModal();
                // Reload policies cache
                await loadAvailablePolicies();
            } else {
                showAlert('❌ ' + (result.error || 'Gán quyền thất bại'), 'error');
            }
        } catch (error) {
            console.error('Assign policy error:', error);
            showAlert('❌ Lỗi: ' + error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg> Gán quyền';
        }
    }
    
    async function openViewPoliciesModal(filePath) {
        assigningFilePath = filePath;
        
        const fileName = filePath.split('/').pop();
        document.getElementById('view-policies-file-name').textContent = `File: ${fileName}`;
        document.getElementById('view-policies-modal').classList.remove('hidden');
        
        // Load file policies
        const container = document.getElementById('file-policies-content');
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <div class="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                Đang tải...
            </div>
        `;
        
        try {
            const response = await fetch(
                `${API_BASE}files/file_policies/?path=${encodeURIComponent(filePath)}&bucket=documents`,
                { headers }
            );
            
            if (!response.ok) {
                throw new Error('Failed to load policies');
            }
            
            const data = await response.json();
            renderFilePolicies(data);
        } catch (error) {
            console.error('Error loading file policies:', error);
            container.innerHTML = `
                <div class="text-center py-8 text-red-500">
                    <p>Lỗi khi tải thông tin quyền</p>
                    <p class="text-sm">${error.message}</p>
                </div>
            `;
        }
    }
    
    function renderFilePolicies(data) {
        const container = document.getElementById('file-policies-content');
        const { direct_policies, inherited_folder_policies } = data;
        
        if (direct_policies.length === 0 && inherited_folder_policies.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <svg class="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                    </svg>
                    <p class="text-lg font-medium">Chưa có quyền nào được gán</p>
                    <p class="text-sm mt-1">File này sử dụng quyền ABAC mặc định của hệ thống</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        
        // Direct policies
        if (direct_policies.length > 0) {
            html += `
                <div class="mb-6">
                    <h4 class="font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                        </svg>
                        Quyền trực tiếp (${direct_policies.length})
                    </h4>
                    <div class="space-y-2">
                        ${direct_policies.map(p => renderPolicyItem(p, true)).join('')}
                    </div>
                </div>
            `;
        }
        
        // Inherited folder policies
        if (inherited_folder_policies.length > 0) {
            html += `
                <div>
                    <h4 class="font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                        </svg>
                        Kế thừa từ thư mục (${inherited_folder_policies.length})
                    </h4>
                    <div class="space-y-2">
                        ${inherited_folder_policies.map(p => renderPolicyItem(p, false)).join('')}
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
    }
    
    function renderPolicyItem(policy, canRemove) {
        return `
            <div class="border rounded-lg p-3 bg-gray-50">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2">
                            <span class="font-medium text-gray-900">${escapeHtml(policy.policy_name)}</span>
                            <span class="px-2 py-0.5 text-xs rounded-full ${policy.policy_effect === 'allow' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">
                                ${policy.policy_effect === 'allow' ? '✓ Allow' : '✕ Deny'}
                            </span>
                        </div>
                        ${policy.policy_description ? `<p class="text-sm text-gray-500 mt-1">${escapeHtml(policy.policy_description)}</p>` : ''}
                        <div class="flex items-center gap-4 mt-2 text-xs text-gray-400">
                            <span>Gán bởi: ${policy.assigned_by_username || 'N/A'}</span>
                            <span>Ngày: ${new Date(policy.assigned_at).toLocaleDateString('vi-VN')}</span>
                        </div>
                        ${policy.notes ? `<p class="text-xs text-gray-500 mt-1 italic">"${escapeHtml(policy.notes)}"</p>` : ''}
                    </div>
                    ${canRemove ? `
                        <button onclick="removePolicyAssignment(${policy.id})" 
                            class="ml-2 p-1 text-red-500 hover:bg-red-50 rounded transition-colors" title="Xóa quyền này">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    async function removePolicyAssignment(assignmentId) {
        if (!confirm('Xác nhận xóa quyền này?')) return;
        
        try {
            const response = await fetch(
                `${API_BASE}files/remove_policy/?assignment_id=${assignmentId}`,
                { method: 'DELETE', headers }
            );
            
            if (response.ok) {
                showAlert('✅ Đã xóa quyền', 'success');
                // Reload view
                if (assigningFilePath) {
                    openViewPoliciesModal(assigningFilePath);
                }
            } else {
                const err = await response.json().catch(() => ({ error: 'Failed' }));
                showAlert('❌ ' + (err.error || 'Xóa thất bại'), 'error');
            }
        } catch (error) {
            showAlert('❌ Lỗi: ' + error.message, 'error');
        }
    }
    
    function closeViewPoliciesModal() {
        document.getElementById('view-policies-modal').classList.add('hidden');
    }
    
    function openAssignPolicyFromView() {
        closeViewPoliciesModal();
        if (assigningFilePath) {
            openAssignPolicyModal(assigningFilePath);
        }
    }
    
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async function deleteFile(filePath) {
        if (!confirm(`Xóa file "${filePath.split('/').pop()}"?`)) return;
        
        try {
            const url = `${API_BASE}files/delete_by_path/?path=${encodeURIComponent(filePath)}&bucket=documents`;
            const response = await fetch(url, { 
                method: 'DELETE',
                headers 
            });
            
            if (response.status === 403) {
                const err = await response.json().catch(() => ({ error: 'Access denied' }));
                showAlert('🚫 ' + (err.error || 'Bạn không có quyền xóa file này'), 'error');
                return;
            }
            
            if (response.ok) {
                showAlert('✅ Đã xóa file thành công', 'success');
                loadFolder(currentPath);
            } else {
                const err = await response.json().catch(() => ({ error: 'Delete failed' }));
                showAlert('❌ ' + (err.error || 'Xóa file thất bại'), 'error');
            }
        } catch (error) {
            console.error('Delete error:', error);
            showAlert('❌ Lỗi: ' + error.message, 'error');
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

    async function createFolder() {
        const name = prompt('Tên thư mục mới:');
        if (!name) return;

        if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
            showAlert('❌ Tên thư mục chỉ được chứa chữ, số, gạch ngang và gạch dưới', 'error');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}files/create_folder/`, {
                method: 'POST',
                headers: {
                    ...headers,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    folder_name: name,
                    bucket_name: 'documents',
                    parent_path: currentPath
                })
            });

            if (response.status === 403) {
                showAlert('🚫 Bạn không có quyền tạo thư mục', 'error');
                return;
            }

            if (response.ok) {
                showAlert(`✅ Đã tạo thư mục "${name}"`, 'success');
                loadFolder(currentPath);
            } else {
                const err = await response.json().catch(() => ({ error: 'Failed to create folder' }));
                showAlert('❌ ' + (err.error || 'Tạo thư mục thất bại'), 'error');
            }
        } catch (error) {
            console.error('Create folder error:', error);
            showAlert('❌ Lỗi: ' + error.message, 'error');
        }
    }

    // ============= EXPOSE TO GLOBAL SCOPE =============
    window.loadFolder = loadFolder;
    window.handleFileClick = handleFileClick;
    window.previewFile = previewFile;
    window.downloadFile = downloadFile;
    window.deleteFile = deleteFile;
    window.toggleSelection = toggleSelection;
    window.clearSelection = clearSelection;
    window.bulkDownload = bulkDownload;
    window.bulkDelete = bulkDelete;
    window.refreshFolders = refreshFolders;
    window.closePreview = closePreview;
    window.downloadFromPreview = downloadFromPreview;
    window.contextAction = contextAction;
    window.createFolder = createFolder;
    
    // Upload policy functions
    window.toggleNewPolicyForm = toggleNewPolicyForm;
    window.toggleUploadAdvancedMode = toggleUploadAdvancedMode;
    window.addUploadRule = addUploadRule;
    window.uploadUpdateValueSelector = uploadUpdateValueSelector;
    window.uploadRemoveRule = uploadRemoveRule;
    window.updateUploadPreview = updateUploadPreview;
    window.updateUploadPreviewFromAdvanced = updateUploadPreviewFromAdvanced;
    
    console.log('files-manager.js: Upload policy functions exported to window');
    console.log('window.addUploadRule:', typeof window.addUploadRule);
    
    // Assign Policy Builder functions
    window.toggleAssignAdvancedMode = toggleAssignAdvancedMode;
    window.addAssignRule = addAssignRule;
    window.assignUpdateValueSelector = assignUpdateValueSelector;
    window.assignRemoveRule = assignRemoveRule;
    window.updateAssignPreview = updateAssignPreview;
    window.updateAssignPreviewFromAdvanced = updateAssignPreviewFromAdvanced;
    
    // Policy assignment functions
    window.selectPolicy = selectPolicy;
    window.filterPolicies = filterPolicies;
    window.switchPolicyTab = switchPolicyTab;
    window.openAssignPolicyModal = openAssignPolicyModal;
    window.closeAssignPolicyModal = closeAssignPolicyModal;
    window.submitAssignPolicy = submitAssignPolicy;
    window.openViewPoliciesModal = openViewPoliciesModal;
    window.closeViewPoliciesModal = closeViewPoliciesModal;
    window.removePolicyAssignment = removePolicyAssignment;
    window.openAssignPolicyFromView = openAssignPolicyFromView;
    
    // Context menu functions
    window.showContextMenu = showContextMenu;
    window.hideContextMenu = hideContextMenu;
    window.contextAction = contextAction;

})(); // End of IIFE
