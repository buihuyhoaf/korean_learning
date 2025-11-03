/**
 * Image Upload Widget for Question Media Field
 * Automatically injects upload button and preview for JSONB media fields
 */

(function() {
    'use strict';

    console.log('🖼️ Image Upload Widget loaded');

    /**
     * Initialize upload widget for Question model forms
     */
    function initializeUploadWidget() {
        // Only run on Question pages
        if (!window.location.pathname.toLowerCase().includes('/question')) {
            return;
        }

        console.log('📍 Initializing upload widget for Question model');

        // Find media field - try multiple selectors
        const mediaField = findMediaField();
        if (!mediaField) {
            console.warn('⚠️ Media field not found');
            return;
        }

        console.log('✅ Media field found:', mediaField.name || mediaField.id);

        // Check if widget already exists
        const existingWidget = mediaField.closest('.form-group')?.querySelector('.image-upload-widget');
        if (existingWidget) {
            console.log('⏭️ Widget already initialized');
            return;
        }

        // Create and inject widget
        createUploadWidget(mediaField);
    }

    /**
     * Find the media textarea field
     */
    function findMediaField() {
        const selectors = [
            'textarea[name="media"]',
            'textarea[id="media"]',
            'textarea[id*="media" i]',
        ];

        for (const selector of selectors) {
            const field = document.querySelector(selector);
            if (field) return field;
        }

        // Fallback: search by label text
        const labels = document.querySelectorAll('label');
        for (const label of labels) {
            if (label.textContent.toLowerCase().includes('media')) {
                const forAttr = label.getAttribute('for');
                if (forAttr) {
                    const field = document.getElementById(forAttr);
                    if (field && field.tagName === 'TEXTAREA') return field;
                }
                // Also check next sibling
                const field = label.nextElementSibling;
                if (field && field.tagName === 'TEXTAREA') return field;
            }
        }

        return null;
    }

    /**
     * Create and inject upload widget into the DOM
     */
    function createUploadWidget(mediaField) {
        const formGroup = mediaField.closest('.form-group');
        if (!formGroup) return;

        // Create widget container
        const widget = document.createElement('div');
        widget.className = 'image-upload-widget';
        widget.innerHTML = `
            <div class="upload-controls">
                <button type="button" class="upload-button" id="imageUploadButton">
                    📤 Upload Image
                </button>
                <input type="file" id="imageFileInput" accept="image/jpeg,image/png,image/webp" style="display: none;">
                <div class="upload-status" id="uploadStatus"></div>
            </div>
            <div class="image-preview" id="imagePreview"></div>
        `;

        // Insert after the media field
        mediaField.parentNode.insertBefore(widget, mediaField.nextSibling);

        // Set up event listeners
        const fileInput = widget.querySelector('#imageFileInput');
        const uploadButton = widget.querySelector('#imageUploadButton');
        const statusDiv = widget.querySelector('#uploadStatus');
        const previewDiv = widget.querySelector('#imagePreview');

        // Button click triggers file input
        uploadButton.addEventListener('click', () => fileInput.click());

        // File selection triggers upload
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;

            await uploadImage(file, mediaField, statusDiv, previewDiv);
            // Clear file input for re-upload
            fileInput.value = '';
        });

        // Load existing image if present
        loadExistingImage(mediaField, previewDiv);
    }

    /**
     * Upload image to Supabase via API
     */
    async function uploadImage(file, mediaField, statusDiv, previewDiv) {
        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            showStatus(statusDiv, '❌ Invalid file type. Please upload JPG, PNG, or WebP.', 'error');
            return;
        }

        // Validate file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
            showStatus(statusDiv, '❌ File too large. Maximum size is 5MB.', 'error');
            return;
        }

        // Show uploading status
        showStatus(statusDiv, '⏳ Uploading...', 'uploading');

        // Create FormData
        const formData = new FormData();
        formData.append('file', file);

        try {
            // Upload to API
            const response = await fetch('/api/v1/upload-image', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok || !data.url) {
                throw new Error(data.detail || 'Upload failed');
            }

            // Update media field with image URL
            updateMediaField(mediaField, data.url);

            // Show success status
            showStatus(statusDiv, '✅ Uploaded successfully!', 'success');

            // Show preview
            showPreview(previewDiv, data.url);

        } catch (error) {
            console.error('Upload error:', error);
            showStatus(statusDiv, `❌ Upload failed: ${error.message}`, 'error');
        }
    }

    /**
     * Update media field with image URL
     */
    function updateMediaField(mediaField, imageUrl) {
        try {
            let mediaData = {};
            const currentValue = mediaField.value.trim();

            if (currentValue) {
                mediaData = JSON.parse(currentValue);
            }

            mediaData.image_url = imageUrl;
            mediaField.value = JSON.stringify(mediaData, null, 2);

            // Trigger change event for form validation
            mediaField.dispatchEvent(new Event('change', { bubbles: true }));

            console.log('✅ Media field updated with image URL');

        } catch (parseError) {
            console.error('Error updating media field:', parseError);
            throw new Error('Failed to update media field');
        }
    }

    /**
     * Load and display existing image from media field
     */
    function loadExistingImage(mediaField, previewDiv) {
        try {
            const value = mediaField.value.trim();
            if (!value) return;

            const mediaData = JSON.parse(value);
            const imageUrl = mediaData.image_url || mediaData.image;

            if (imageUrl) {
                showPreview(previewDiv, imageUrl);
                console.log('✅ Loaded existing image from media field');
            }

        } catch (error) {
            // Silently ignore invalid JSON or missing image
        }
    }

    /**
     * Show status message
     */
    function showStatus(statusDiv, message, type) {
        statusDiv.textContent = message;
        statusDiv.className = `upload-status ${type}`;
    }

    /**
     * Show image preview
     */
    function showPreview(previewDiv, imageUrl) {
        previewDiv.innerHTML = `
            <img src="${imageUrl}" alt="Preview" onerror="this.parentElement.innerHTML=''">
        `;
    }

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeUploadWidget);
    } else {
        initializeUploadWidget();
    }

    // Re-initialize on HTMX navigation (CRUDAdmin uses HTMX)
    document.body.addEventListener('htmx:afterSwap', function() {
        setTimeout(initializeUploadWidget, 100);
    });

})();

