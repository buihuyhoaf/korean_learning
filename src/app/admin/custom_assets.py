"""
Custom assets (CSS, JS) for admin interface customization.
"""
from fastapi import Request
from fastapi.responses import Response


def get_custom_css(settings) -> str:
    """Generate custom CSS for the admin interface."""
    return f"""
/* Korean Learning Admin - Custom Styles */

/* Color Variables */
:root {{
    --primary-color: {settings.CRUD_ADMIN_THEME_PRIMARY};
    --secondary-color: {settings.CRUD_ADMIN_THEME_SECONDARY};
    --accent-color: {settings.CRUD_ADMIN_THEME_ACCENT};
    
    --sidebar-bg: linear-gradient(135deg, {settings.CRUD_ADMIN_THEME_PRIMARY} 0%, {settings.CRUD_ADMIN_THEME_SECONDARY} 100%);
    --header-bg: #ffffff;
    --card-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
    --hover-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
}}

/* Global Styles */
* {{
    box-sizing: border-box;
}}

/* Header Styling */
.app-header {{
    background: var(--header-bg) !important;
    box-shadow: var(--card-shadow) !important;
    border-bottom: 3px solid var(--primary-color);
}}

/* Sidebar Styling */
.app-sidebar {{
    background: var(--sidebar-bg) !important;
}}

.app-sidebar .sidebar-item {{
    transition: all 0.3s ease;
    border-radius: 8px !important;
    margin: 4px 8px !important;
}}

.app-sidebar .sidebar-item:hover {{
    background: rgba(255, 255, 255, 0.15) !important;
    transform: translateX(5px);
}}

.app-sidebar .sidebar-item.active {{
    background: rgba(255, 255, 255, 0.25) !important;
    border-left: 4px solid var(--accent-color);
}}

/* Buttons */
.btn-primary {{
    background-color: var(--primary-color) !important;
    border-color: var(--primary-color) !important;
    transition: all 0.3s ease;
    border-radius: 6px !important;
    font-weight: 500 !important;
}}

.btn-primary:hover {{
    background-color: var(--secondary-color) !important;
    border-color: var(--secondary-color) !important;
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
}}

.btn-secondary {{
    background-color: var(--secondary-color) !important;
    border-color: var(--secondary-color) !important;
    transition: all 0.3s ease;
    border-radius: 6px !important;
}}

.btn-secondary:hover {{
    background-color: var(--primary-color) !important;
    border-color: var(--primary-color) !important;
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
}}

/* Cards */
.card {{
    border-radius: 12px !important;
    box-shadow: var(--card-shadow) !important;
    transition: all 0.3s ease;
    border: none !important;
    overflow: hidden;
}}

.card:hover {{
    box-shadow: var(--hover-shadow);
    transform: translateY(-2px);
}}

.card-header {{
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
    color: white !important;
    padding: 1rem !important;
    font-weight: 600 !important;
    border-bottom: none !important;
}}

/* Table Styling */
table {{
    border-radius: 8px !important;
    overflow: hidden;
}}

thead {{
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
    color: white !important;
}}

thead th {{
    border: none !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    font-size: 0.85rem !important;
    letter-spacing: 0.5px;
}}

tbody tr {{
    transition: all 0.2s ease;
}}

tbody tr:hover {{
    background-color: rgba(255, 107, 107, 0.05) !important;
}}

/* Forms */
.form-control, .form-select {{
    border-radius: 6px !important;
    border: 2px solid #e0e0e0 !important;
    transition: all 0.3s ease;
    padding: 0.6rem 0.8rem !important;
}}

.form-control:focus, .form-select:focus {{
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 0.2rem rgba(255, 107, 107, 0.15) !important;
    outline: none !important;
}}

/* Badges */
.badge {{
    border-radius: 12px !important;
    padding: 0.4rem 0.8rem !important;
    font-weight: 500 !important;
}}

.badge-primary {{
    background-color: var(--primary-color) !important;
}}

.badge-secondary {{
    background-color: var(--secondary-color) !important;
}}

/* Success/Error Messages */
.alert-success {{
    background: linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
}}

.alert-danger {{
    background: linear-gradient(135deg, #FF6B6B 0%, #EE5A6F 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
}}

.alert-warning {{
    background: linear-gradient(135deg, #FFE66D 0%, #FFD93D 100%) !important;
    color: #333 !important;
    border: none !important;
    border-radius: 8px !important;
}}

/* Modals */
.modal-content {{
    border-radius: 12px !important;
    border: none !important;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2) !important;
}}

.modal-header {{
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
    color: white !important;
    border-bottom: none !important;
    border-radius: 12px 12px 0 0 !important;
}}

.modal-header .btn-close {{
    filter: invert(1);
}}

/* Pagination */
.pagination .page-item.active .page-link {{
    background-color: var(--primary-color) !important;
    border-color: var(--primary-color) !important;
}}

.pagination .page-link {{
    color: var(--primary-color) !important;
    transition: all 0.2s ease;
}}

.pagination .page-link:hover {{
    background-color: rgba(255, 107, 107, 0.1) !important;
    color: var(--secondary-color) !important;
}}

/* Dashboard Stats Cards */
.stat-card {{
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: var(--card-shadow);
    transition: all 0.3s ease;
    border-left: 4px solid var(--primary-color);
}}

.stat-card:hover {{
    transform: translateY(-4px);
    box-shadow: var(--hover-shadow);
}}

.stat-card h3 {{
    color: var(--primary-color);
    font-size: 2rem;
    font-weight: 700;
    margin: 0;
}}

.stat-card p {{
    color: #666;
    font-size: 0.9rem;
    margin: 0.5rem 0 0 0;
}}

/* Smooth Transitions */
*, *::before, *::after {{
    transition: background-color 0.2s ease, border-color 0.2s ease;
}}

/* Scrollbar Styling */
::-webkit-scrollbar {{
    width: 8px;
    height: 8px;
}}

::-webkit-scrollbar-track {{
    background: #f1f1f1;
}}

::-webkit-scrollbar-thumb {{
    background: var(--primary-color);
    border-radius: 4px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: var(--secondary-color);
}}

/* Logo/Site Name Styling */
.site-title {{
    font-weight: 700 !important;
    font-size: 1.3rem !important;
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

/* Loading Spinners */
.spinner-border-primary {{
    color: var(--primary-color) !important;
}}

/* Responsive Adjustments */
@media (max-width: 768px) {{
    .app-sidebar {{
        width: 60px !important;
    }}
    
    .card {{
        margin-bottom: 1rem;
    }}
}}

/* Image Upload Widget Styles */
.image-upload-widget {{
    margin-top: 0.5rem;
    padding: 1rem;
    border: 2px dashed #e0e0e0;
    border-radius: 8px;
    background-color: #f8f9fa;
    transition: all 0.3s ease;
}}

.image-upload-widget:hover {{
    border-color: var(--primary-color);
    background-color: #fff;
}}

.image-upload-widget.dragover {{
    border-color: var(--primary-color);
    background-color: rgba(255, 107, 107, 0.1);
}}

.upload-button {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 1.2rem;
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.3s ease;
    margin-bottom: 0.5rem;
}}

.upload-button:hover {{
    background-color: var(--secondary-color);
    transform: translateY(-2px);
    box-shadow: var(--hover-shadow);
}}

.upload-button:disabled {{
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}}

.upload-button input[type="file"] {{
    display: none;
}}

.image-preview-container {{
    margin-top: 1rem;
    display: none;
}}

.image-preview-container.has-image {{
    display: block;
}}

.image-preview {{
    max-width: 100%;
    max-height: 300px;
    border-radius: 8px;
    box-shadow: var(--card-shadow);
    margin-top: 0.5rem;
    object-fit: contain;
}}

.image-preview-info {{
    margin-top: 0.5rem;
    padding: 0.5rem;
    background-color: #e8f5e9;
    border-radius: 6px;
    font-size: 0.875rem;
    color: #2e7d32;
}}

.upload-status {{
    margin-top: 0.5rem;
    padding: 0.5rem;
    border-radius: 6px;
    font-size: 0.875rem;
    display: none;
}}

.upload-status.uploading {{
    display: block;
    background-color: #fff3cd;
    color: #856404;
}}

.upload-status.success {{
    display: block;
    background-color: #d4edda;
    color: #155724;
}}

.upload-status.error {{
    display: block;
    background-color: #f8d7da;
    color: #721c24;
}}

.upload-progress {{
    width: 100%;
    height: 6px;
    background-color: #e0e0e0;
    border-radius: 3px;
    overflow: hidden;
    margin-top: 0.5rem;
    display: none;
}}

.upload-progress.active {{
    display: block;
}}

.upload-progress-bar {{
    height: 100%;
    background-color: var(--primary-color);
    width: 0%;
    transition: width 0.3s ease;
}}
"""


def get_custom_js(settings) -> str:
    """Generate custom JavaScript for the admin interface."""
    js_template = """
// Korean Learning Admin - Custom JavaScript

const ADMIN_BASE_PATH = "__ADMIN_BASE_PATH__";

console.log('🇰🇷 Korean Learning Admin Loaded');
console.log('📍 [Upload Widget] Script loaded at:', new Date().toISOString());
console.log('📍 [Upload Widget] Current path:', window.location.pathname);

// Add smooth scroll behavior
document.documentElement.style.scrollBehavior = 'smooth';

function createProgressTrackerElements() {
    const link = document.createElement('a');
    link.href = ADMIN_BASE_PATH + '/progress-tracker';
    link.textContent = 'Progress Tracker';
    link.classList.add('sidebar-link', 'nav-link');
    link.setAttribute('data-progress-tracker-link', 'true');

    const item = document.createElement('li');
    item.classList.add('sidebar-item', 'nav-item');
    item.appendChild(link);

    return { link, item };
}

function createPushNotificationElements() {
    const link = document.createElement('a');
    link.href = ADMIN_BASE_PATH + '/push-notifications';
    link.textContent = 'Push Notifications';
    link.classList.add('sidebar-link', 'nav-link');
    link.setAttribute('data-push-notifications-link', 'true');

    const item = document.createElement('li');
    item.classList.add('sidebar-item', 'nav-item');
    item.appendChild(link);

    return { link, item };
}

function insertProgressTrackerLink() {
    if (document.querySelector('[data-progress-tracker-link]')) {
        return true;
    }

    const listSelectors = [
        '.app-sidebar nav ul',
        '.app-sidebar .sidebar-nav ul',
        '.app-sidebar ul',
        '.sidebar nav ul',
        '.sidebar-nav ul',
        'nav.sidebar-nav ul',
        '.sidebar-menu ul',
        'nav ul.sidebar-menu'
    ];

    for (const selector of listSelectors) {
        const container = document.querySelector(selector);
        if (!container) {
            continue;
        }

        const { item } = createProgressTrackerElements();
        container.appendChild(item);
        return true;
    }

    const navSelectors = [
        '.app-sidebar nav',
        'nav.sidebar-nav',
        '.sidebar-nav',
        '.sidebar',
        '.app-sidebar'
    ];

    for (const selector of navSelectors) {
        const container = document.querySelector(selector);
        if (!container) {
            continue;
        }

        if (container.querySelector('[data-progress-tracker-link]')) {
            return true;
        }

        const { link } = createProgressTrackerElements();
        container.appendChild(link);
        return true;
    }

    return false;
}

function insertPushNotificationsLink() {
    if (document.querySelector('[data-push-notifications-link]')) {
        return true;
    }

    const listSelectors = [
        '.app-sidebar nav ul',
        '.app-sidebar .sidebar-nav ul',
        '.app-sidebar ul',
        '.sidebar nav ul',
        '.sidebar-nav ul',
        'nav.sidebar-nav ul',
        '.sidebar-menu ul',
        'nav ul.sidebar-menu'
    ];

    for (const selector of listSelectors) {
        const container = document.querySelector(selector);
        if (!container) {
            continue;
        }

        const { item } = createPushNotificationElements();
        container.appendChild(item);
        return true;
    }

    const navSelectors = [
        '.app-sidebar nav',
        'nav.sidebar-nav',
        '.sidebar-nav',
        '.sidebar',
        '.app-sidebar'
    ];

    for (const selector of navSelectors) {
        const container = document.querySelector(selector);
        if (!container) {
            continue;
        }

        if (container.querySelector('[data-push-notifications-link]')) {
            return true;
        }

        const { link } = createPushNotificationElements();
        container.appendChild(link);
        return true;
    }

    return false;
}

function ensureProgressTrackerLink() {
    if (!insertProgressTrackerLink()) {
        setTimeout(insertProgressTrackerLink, 300);
        setTimeout(insertProgressTrackerLink, 1200);
        setTimeout(insertProgressTrackerLink, 3000);
    }
}

function ensurePushNotificationsLink() {
    if (!insertPushNotificationsLink()) {
        setTimeout(insertPushNotificationsLink, 300);
        setTimeout(insertPushNotificationsLink, 1200);
        setTimeout(insertPushNotificationsLink, 3000);
    }
}

// Image Upload Widget for Question Media Field
function initializeImageUploadWidget() {
    console.log('🔍 [Upload Widget] Initializing image upload widget...');
    console.log('🔍 [Upload Widget] Current URL:', window.location.href);
    console.log('🔍 [Upload Widget] Current path:', window.location.pathname);
    
    // Only initialize on Question pages (case-insensitive)
    // Also work on /admin/Question/ because CRUDAdmin uses HTMX to load forms
    const path = window.location.pathname.toLowerCase();
    if (!path.includes('/question')) {
        console.log('⚠️ [Upload Widget] Not a Question page, skipping...');
        console.log('📍 [Upload Widget] Current path:', window.location.pathname);
        return;
    }
    
    console.log('✅ [Upload Widget] Question page detected:', window.location.pathname);
    
    // Check if we're in a form (create or update)
    // CRUDAdmin may load forms via HTMX, so we need to wait for form to appear
    const hasForm = document.querySelector('form') !== null;
    if (!hasForm) {
        console.log('⏳ [Upload Widget] Form not found yet, will retry when form loads...');
        // Don't return - let the function continue to try finding fields
        // The retry mechanism below will handle it
    }
    
    // Find media field in Question forms (both create and update)
    // CRUDAdmin might render JSONB fields as textarea or input
    // Try multiple selectors to find the media field
    const selectors = [
        'input[name="media"]',
        'textarea[name="media"]',
        'input[id*="media"]',
        'textarea[id*="media"]',
        'input[name*="media"]',
        'textarea[name*="media"]',
        'input[id*="Media"]',
        'textarea[id*="Media"]',
        'input[id*="MEDIA"]',
        'textarea[id*="MEDIA"]'
    ];
    
    let mediaFields = [];
    selectors.forEach(selector => {
        try {
            const fields = document.querySelectorAll(selector);
            if (fields.length > 0) {
                console.log(`✅ [Upload Widget] Found ${fields.length} field(s) with selector: ${selector}`);
                mediaFields.push(...Array.from(fields));
            }
        } catch (e) {
            // Skip invalid selectors
        }
    });
    
    // Also search for labels containing "media" and find associated input/textarea
    document.querySelectorAll('label').forEach(label => {
        const labelText = label.textContent.toLowerCase();
        if (labelText.includes('media')) {
            const forAttr = label.getAttribute('for');
            if (forAttr) {
                const field = document.getElementById(forAttr);
                if (field && !mediaFields.includes(field)) {
                    mediaFields.push(field);
                }
            }
            // Also check next sibling
            let sibling = label.nextElementSibling;
            while (sibling) {
                if (sibling.tagName === 'INPUT' || sibling.tagName === 'TEXTAREA') {
                    if (!mediaFields.includes(sibling)) {
                        mediaFields.push(sibling);
                    }
                    break;
                }
                sibling = sibling.nextElementSibling;
            }
        }
    });
    
    console.log(`📝 [Upload Widget] Total media fields found: ${mediaFields.length}`);
    
    if (mediaFields.length === 0) {
        console.warn('⚠️ [Upload Widget] No media field found! Searching all form fields...');
        // Fallback: log all form fields for debugging
        const allInputs = document.querySelectorAll('input, textarea');
        console.log(`📋 [Upload Widget] Total form fields found: ${allInputs.length}`);
        allInputs.forEach(function(field, index) {
            const label = field.closest('div')?.querySelector('label') || 
                         document.querySelector(`label[for="${field.id}"]`);
            const labelText = label ? label.textContent : 'no label';
            console.log(`  Field ${index + 1}: name="${field.name}", id="${field.id}", type="${field.type || 'textarea'}", label="${labelText}"`);
        });
        
        // Try to find by label text containing "media"
        const allLabels = document.querySelectorAll('label');
        allLabels.forEach(function(label) {
            const labelText = label.textContent.toLowerCase();
            if (labelText.includes('media')) {
                console.log(`🏷️ [Upload Widget] Found label with "media": "${label.textContent}"`);
                const forAttr = label.getAttribute('for');
                if (forAttr) {
                    const field = document.getElementById(forAttr);
                    if (field && !mediaFields.includes(field)) {
                        console.log(`✅ [Upload Widget] Adding field from label "for" attribute`);
                        mediaFields.push(field);
                    }
                }
            }
        });
    }
    
    console.log(`📝 [Upload Widget] Final media fields count: ${mediaFields.length}`);
    
    mediaFields.forEach(function(mediaField, index) {
        console.log(`🎨 [Upload Widget] Processing media field ${index + 1}: name="${mediaField.name}", id="${mediaField.id}"`);
        // Skip if already initialized
        const formGroup = mediaField.closest('.form-group') || 
                         mediaField.closest('.form-control-group') || 
                         mediaField.parentElement;
        if (!formGroup) return;
        
        if (formGroup.querySelector('.image-upload-widget')) {
            return;
        }
        
        // Create upload widget
        const uploadWidget = document.createElement('div');
        uploadWidget.className = 'image-upload-widget';
        uploadWidget.innerHTML = `
            <button type="button" class="upload-button">
                <input type="file" accept="image/jpeg,image/png,image/webp" />
                📤 Upload Image
            </button>
            <div class="upload-status"></div>
            <div class="upload-progress">
                <div class="upload-progress-bar"></div>
            </div>
            <div class="image-preview-container">
                <img class="image-preview" alt="Image preview" />
                <div class="image-preview-info"></div>
            </div>
        `;
        
        // Insert widget after the media field or before it
        // Try to insert after the field, or if that doesn't work, append to formGroup
        if (mediaField.nextSibling) {
            formGroup.insertBefore(uploadWidget, mediaField.nextSibling);
        } else {
            formGroup.appendChild(uploadWidget);
        }
        
        console.log(`✅ [Upload Widget] Widget inserted for field ${index + 1}`);
        
        const fileInput = uploadWidget.querySelector('input[type="file"]');
        const uploadButton = uploadWidget.querySelector('.upload-button');
        const previewContainer = uploadWidget.querySelector('.image-preview-container');
        const previewImg = uploadWidget.querySelector('.image-preview');
        const previewInfo = uploadWidget.querySelector('.image-preview-info');
        const statusDiv = uploadWidget.querySelector('.upload-status');
        const progressDiv = uploadWidget.querySelector('.upload-progress');
        const progressBar = uploadWidget.querySelector('.upload-progress-bar');
        
        // Load existing image if media field has value
        try {
            const mediaValue = mediaField.value.trim();
            if (mediaValue) {
                let mediaObj = {};
                try {
                    mediaObj = JSON.parse(mediaValue);
                } catch (e) {
                    // Try to parse as escaped JSON
                    try {
                        mediaObj = JSON.parse(mediaValue.replace(/\\\\/g, '\\\\'));
                    } catch (e2) {
                        console.warn('Could not parse media field:', e2);
                    }
                }
                
                // Support both "image" and "image_url" keys
                const imageUrl = mediaObj.image || mediaObj.image_url;
                if (imageUrl) {
                    previewImg.src = imageUrl;
                    previewContainer.classList.add('has-image');
                    previewInfo.textContent = 'Current image: ' + imageUrl;
                }
            }
        } catch (e) {
            console.warn('Error loading existing image:', e);
        }
        
        // File input change handler
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                uploadImage(file);
            }
        });
        
        // Upload button click handler
        uploadButton.addEventListener('click', function() {
            fileInput.click();
        });
        
        // Drag and drop handlers
        uploadWidget.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadWidget.classList.add('dragover');
        });
        
        uploadWidget.addEventListener('dragleave', function() {
            uploadWidget.classList.remove('dragover');
        });
        
        uploadWidget.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadWidget.classList.remove('dragover');
            
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                uploadImage(file);
            } else {
                showStatus('Please drop an image file (jpg, png, or webp)', 'error');
            }
        });
        
        // Upload image function
        function uploadImage(file) {
            // Validate file type
            const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
            if (!allowedTypes.includes(file.type)) {
                showStatus('Invalid file type. Please upload jpg, png, or webp.', 'error');
                return;
            }
            
            // Validate file size (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                showStatus('File size too large. Maximum size is 5MB.', 'error');
                return;
            }
            
            // Show uploading status
            uploadButton.disabled = true;
            statusDiv.className = 'upload-status uploading';
            statusDiv.textContent = 'Uploading...';
            progressDiv.classList.add('active');
            progressBar.style.width = '30%';
            
            // Create FormData
            const formData = new FormData();
            formData.append('file', file);
            
            // Upload to API - use absolute path to ensure it works from admin interface
            const apiUrl = window.location.origin + '/api/v1/upload-image';
            fetch(apiUrl, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                progressBar.style.width = '70%';
                if (!response.ok) {
                    return response.json().then(err => Promise.reject(err));
                }
                return response.json();
            })
            .then(data => {
                progressBar.style.width = '100%';
                
                // Update media field with image URL
                let mediaObj = {};
                try {
                    const currentValue = mediaField.value.trim();
                    if (currentValue) {
                        mediaObj = JSON.parse(currentValue);
                    }
                } catch (e) {
                    // If parsing fails, start with empty object
                    mediaObj = {};
                }
                
                // Update media field with image URL
                // Support both "image" and "image_url" keys for compatibility
                mediaObj.image = data.url;
                mediaObj.image_url = data.url;  // Also set image_url for backward compatibility
                mediaField.value = JSON.stringify(mediaObj);
                
                // Trigger input event to notify form of change
                mediaField.dispatchEvent(new Event('input', { bubbles: true }));
                mediaField.dispatchEvent(new Event('change', { bubbles: true }));
                
                console.log('[Upload] Media field updated:', mediaField.value);
                
                // Show preview
                previewImg.src = data.url;
                previewContainer.classList.add('has-image');
                previewInfo.textContent = 'Uploaded: ' + data.url;
                
                // Show success status
                setTimeout(() => {
                    showStatus('✓ Image uploaded successfully!', 'success');
                    uploadButton.disabled = false;
                    progressDiv.classList.remove('active');
                    progressBar.style.width = '0%';
                    
                    // Auto-hide success message after 3 seconds
                    setTimeout(() => {
                        statusDiv.className = 'upload-status';
                        statusDiv.textContent = '';
                    }, 3000);
                }, 300);
            })
            .catch(error => {
                console.error('Upload error:', error);
                const errorMsg = error.detail || error.message || 'Upload failed. Please try again.';
                showStatus('✗ ' + errorMsg, 'error');
                uploadButton.disabled = false;
                progressDiv.classList.remove('active');
                progressBar.style.width = '0%';
            });
        }
        
        function showStatus(message, type) {
            statusDiv.textContent = message;
            statusDiv.className = 'upload-status ' + type;
            
            if (type === 'error') {
                setTimeout(() => {
                    statusDiv.className = 'upload-status';
                    statusDiv.textContent = '';
                }, 5000);
            }
        }
    });
}

// Simple Image Upload for Course image_url field
function initializeCourseImageUpload() {
    const path = window.location.pathname.toLowerCase();
    if (!path.includes('/course')) {
        return;
    }

    const selectors = [
        'input[name="image_url"]',
        'input[id*="image_url" i]'
    ];

    let imageFields = [];
    selectors.forEach(s => {
        try {
            document.querySelectorAll(s).forEach(el => imageFields.push(el));
        } catch (e) {}
    });

    if (imageFields.length === 0) {
        return;
    }

    imageFields.forEach(field => {
        const formGroup = field.closest('.form-group') || field.parentElement;
        if (!formGroup || formGroup.querySelector('.image-upload-widget')) return;

        const widget = document.createElement('div');
        widget.className = 'image-upload-widget';
        widget.innerHTML = `
            <button type="button" class="upload-button">
                <input type="file" accept="image/jpeg,image/png,image/webp" />
                📤 Upload Image
            </button>
            <div class="upload-status"></div>
            <div class="image-preview-container">
                <img class="image-preview" alt="Image preview" />
                <div class="image-preview-info"></div>
            </div>
        `;

        if (field.nextSibling) {
            formGroup.insertBefore(widget, field.nextSibling);
        } else {
            formGroup.appendChild(widget);
        }

        const fileInput = widget.querySelector('input[type="file"]');
        const uploadButton = widget.querySelector('.upload-button');
        const previewContainer = widget.querySelector('.image-preview-container');
        const previewImg = widget.querySelector('.image-preview');
        const previewInfo = widget.querySelector('.image-preview-info');
        const statusDiv = widget.querySelector('.upload-status');

        if (field.value) {
            previewImg.src = field.value;
            previewContainer.classList.add('has-image');
            previewInfo.textContent = 'Current image: ' + field.value;
        }

        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                uploadCourseImage(file);
            }
        });
        uploadButton.addEventListener('click', function() { fileInput.click(); });

        function setStatus(msg, type) {
            statusDiv.textContent = msg;
            statusDiv.className = 'upload-status ' + (type || '');
        }

        async function uploadCourseImage(file) {
            const allowed = ['image/jpeg','image/png','image/webp'];
            if (!allowed.includes(file.type)) { setStatus('Invalid file type', 'error'); return; }
            if (file.size > 5 * 1024 * 1024) { setStatus('File too large (>5MB)', 'error'); return; }
            setStatus('Uploading...', 'uploading');

            const formData = new FormData();
            formData.append('file', file);
            const apiUrl = window.location.origin + '/api/v1/upload-image';
            try {
                const resp = await fetch(apiUrl, { method: 'POST', body: formData });
                const data = await resp.json();
                if (!resp.ok || !data.url) throw new Error(data.detail || 'Upload failed');

                field.value = data.url;
                field.dispatchEvent(new Event('input', { bubbles: true }));
                field.dispatchEvent(new Event('change', { bubbles: true }));

                previewImg.src = data.url;
                previewContainer.classList.add('has-image');
                previewInfo.textContent = 'Uploaded: ' + data.url;
                setStatus('✓ Image uploaded successfully!', 'success');
            } catch (err) {
                setStatus('✗ ' + (err.message || 'Upload failed'), 'error');
            }
        }
    });
}

// Add loading animation on page transitions
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 [Upload Widget] DOMContentLoaded event fired');
    
    // Inject Teacher Progress Tracker shortcut into sidebar
    try {
        ensureProgressTrackerLink();
    } catch (err) {
        console.warn('Unable to inject progress tracker link', err);
    }
    try {
        ensurePushNotificationsLink();
    } catch (err) {
        console.warn('Unable to inject push notifications link', err);
    }
    
    // Animate cards on load
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.5s ease';
            
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 50);
        }, index * 50);
    });
    
    // Add success/error message auto-dismiss
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (alert.classList.contains('alert-success') || 
            alert.classList.contains('alert-danger') ||
            alert.classList.contains('alert-warning')) {
            setTimeout(() => {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            }, 5000);
        }
    });
    
    // Add hover effect to table rows
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.2s ease';
        });
    });
    
    // Initialize image upload widget immediately
    console.log('🎯 [Upload Widget] Initializing on DOMContentLoaded...');
    initializeImageUploadWidget();
    initializeCourseImageUpload();
    
    // Also try after a short delay in case form loads asynchronously
    setTimeout(function() {
        console.log('⏰ [Upload Widget] Re-initializing after delay...');
        initializeImageUploadWidget();
        initializeCourseImageUpload();
    }, 500);
    
    setTimeout(function() {
        console.log('⏰ [Upload Widget] Re-initializing after 2s delay...');
        initializeImageUploadWidget();
        initializeCourseImageUpload();
    }, 2000);
    
    setTimeout(function() {
        console.log('⏰ [Upload Widget] Re-initializing after 3s delay (for HTMX forms)...');
        initializeImageUploadWidget();
        initializeCourseImageUpload();
    }, 3000);
    
    setTimeout(function() {
        console.log('⏰ [Upload Widget] Re-initializing after 5s delay (for slow HTMX loads)...');
        initializeImageUploadWidget();
        initializeCourseImageUpload();
    }, 5000);
    
    // Re-initialize on form updates (for dynamic content like HTMX)
    const observer = new MutationObserver(function(mutations) {
        let shouldReinit = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        if (node.tagName === 'INPUT' || node.tagName === 'TEXTAREA' || 
                            node.querySelector && (node.querySelector('input') || node.querySelector('textarea'))) {
                            shouldReinit = true;
                        }
                    }
                });
            }
        });
        if (shouldReinit) {
            console.log('🔄 [Upload Widget] DOM changed, re-initializing...');
            setTimeout(initializeImageUploadWidget, 100);
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Re-initialize on page navigation (for SPA-like behavior like HTMX)
let lastUrl = location.href;
new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
        lastUrl = url;
        console.log('🔄 [Upload Widget] URL changed, re-initializing...');
        setTimeout(initializeImageUploadWidget, 500);
        setTimeout(ensureProgressTrackerLink, 100);
        setTimeout(ensurePushNotificationsLink, 150);
    }
}).observe(document, { subtree: true, childList: true });

// Listen for HTMX events (CRUDAdmin uses HTMX)
document.body.addEventListener('htmx:afterSwap', function(event) {
    console.log('🔄 [Upload Widget] HTMX afterSwap event, re-initializing...');
    setTimeout(initializeImageUploadWidget, 100);
    setTimeout(ensureProgressTrackerLink, 150);
    setTimeout(ensurePushNotificationsLink, 200);
});

document.body.addEventListener('htmx:load', function(event) {
    console.log('🔄 [Upload Widget] HTMX load event, re-initializing...');
    setTimeout(initializeImageUploadWidget, 100);
    setTimeout(ensureProgressTrackerLink, 150);
    setTimeout(ensurePushNotificationsLink, 200);
});

// Also try initializing periodically for dynamic content (especially for HTMX-loaded forms)
let initAttempts = 0;
const maxInitAttempts = 15;  // Increased to wait longer for HTMX forms
const initInterval = setInterval(function() {
    initAttempts++;
    if (initAttempts <= maxInitAttempts) {
        // Only log every 5 attempts to reduce console spam
        if (initAttempts % 5 === 0 || initAttempts <= 3) {
            console.log(`🔄 [Upload Widget] Periodic re-initialization attempt ${initAttempts}/${maxInitAttempts}`);
        }
        initializeImageUploadWidget();
        initializeCourseImageUpload();
        ensureProgressTrackerLink();
        ensurePushNotificationsLink();
    } else {
        clearInterval(initInterval);
        console.log('⏹️ [Upload Widget] Stopped periodic initialization after max attempts');
    }
}, 2000);  // Check every 2 seconds instead of 1

// Add page transition effect
window.addEventListener('beforeunload', function() {
    document.body.style.opacity = '0.5';
    document.body.style.transition = 'opacity 0.3s ease';
});
"""
    admin_base_path = settings.CRUD_ADMIN_MOUNT_PATH.rstrip("/") or "/admin"
    return js_template.replace("__ADMIN_BASE_PATH__", admin_base_path)


async def serve_custom_css(request: Request) -> Response:
    """Serve custom CSS for admin interface."""
    from ..core.config import settings
    css_content = get_custom_css(settings)
    return Response(content=css_content, media_type="text/css")


async def serve_custom_js(request: Request) -> Response:
    """Serve custom JavaScript for admin interface."""
    from ..core.config import settings
    js_content = get_custom_js(settings)
    return Response(content=js_content, media_type="application/javascript")

