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
                ondblclick="handleFileClick('${filePath}', ${isFolder}, event)"
                onclick="toggleSelection('${filePath}', true)"
                oncontextmenu="showContextMenu(event, '${filePath}', ${isFolder})">
                
                <!-- Selection Checkbox -->
                <div class="absolute top-4 left-4 z-20 opacity-0 group-hover:opacity-100 transition-opacity ${isSelected ? 'opacity-100' : ''}">
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
                        ${file.size ? formatSize(file.size) : (isFolder ? `${file.items || 0} items` : '')}
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
                ondblclick="handleFileClick('${filePath}', ${isFolder}, event)"
                onclick="toggleSelection('${filePath}', true)"
                oncontextmenu="showContextMenu(event, '${filePath}', ${isFolder})">
                
                <div class="w-8 flex items-center justify-center mr-2">
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
            const url = `${API_BASE}files/download_by_path/?path=${encodeURIComponent(filePath)}&bucket=documents`;
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
            const url = `${API_BASE}files/browse/?path=&bucket=documents`;
            console.log('Loading folder list:', url);
            const response = await fetch(url, { headers });
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

    // ============= EXPOSE TO GLOBAL SCOPE =============
    window.loadFolder = loadFolder;
    window.handleFileClick = handleFileClick;
    window.previewFile = previewFile;
    window.downloadFile = downloadFile;
    window.toggleSelection = toggleSelection;
    window.clearSelection = clearSelection;
    window.bulkDownload = bulkDownload;
    window.bulkDelete = bulkDelete;
    window.refreshFolders = refreshFolders;
    window.closePreview = closePreview;
    window.downloadFromPreview = downloadFromPreview;
    window.contextAction = contextAction;
    // Stub for createFolder helper
    window.createFolder = function () {
        showAlert('Tính năng tạo thư mục đang phát triển', 'info');
    };

})(); // End of IIFE
