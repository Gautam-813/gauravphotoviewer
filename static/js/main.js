// Main JavaScript for Gaurav's Baby Photo Gallery

// Gallery application logic
function galleryApp() {
    return {
        loading: true,
        images: [],
        displayedImages: [],
        groupedImages: {},
        lightboxOpen: false,
        currentImage: {},
        currentIndex: 0,
        currentPage: 1,
        photosPerPage: 24,
        totalPages: 1,
        searchQuery: '',
        selectedPhotos: [],
        selectionMode: false,
        slideshowActive: false,
        slideshowInterval: null,
        viewMode: 'grouped', // 'grouped' or 'grid'

        // Initialize the gallery
        async init() {
            console.log('Initializing Gaurav Photo Gallery');
            this.optimizeForDevice();
            await this.loadImages();
            this.setupIntersectionObserver();
            this.initCursorTrail();
            this.addFloatingElements();
            this.setupServiceWorker();
            this.setupAutoRefresh(); // Add auto-refresh
        },

        // Load images from the API
        async loadImages() {
            try {
                console.log('Loading images from API');
                this.loading = true;
                const response = await fetch('/api/images');
                console.log('Response status:', response.status);
                const data = await response.json();
                console.log('Received data:', data);
                this.images = data.images || [];
                console.log('Images loaded:', this.images.length);

                // Sort images by timestamp (newest first)
                this.images.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

                // Group images by month
                this.groupImagesByMonth();

                // Calculate pagination
                this.updatePagination();

            } catch (error) {
                console.error('Error loading images:', error);
                // Show error message to user
                this.images = [];
                this.displayedImages = [];
            } finally {
                this.loading = false;
            }
        },

        // Update pagination and displayed images
        updatePagination() {
            // Filter images based on search query
            let filteredImages = this.images;
            if (this.searchQuery.trim()) {
                filteredImages = this.images.filter(img =>
                    (img.caption && img.caption.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
                    this.formatDate(img.timestamp).toLowerCase().includes(this.searchQuery.toLowerCase())
                );
            }

            // Calculate total pages
            this.totalPages = Math.ceil(filteredImages.length / this.photosPerPage);

            // Ensure current page is valid
            if (this.currentPage > this.totalPages) {
                this.currentPage = 1;
            }

            // Get images for current page
            const startIndex = (this.currentPage - 1) * this.photosPerPage;
            const endIndex = startIndex + this.photosPerPage;
            this.displayedImages = filteredImages.slice(startIndex, endIndex);

            console.log(`Page ${this.currentPage}/${this.totalPages}, showing ${this.displayedImages.length} images`);
        },

        // Go to specific page
        goToPage(page) {
            if (page >= 1 && page <= this.totalPages) {
                this.currentPage = page;
                this.updatePagination();
                // Scroll to top of gallery
                document.querySelector('main').scrollIntoView({ behavior: 'smooth' });
            }
        },

        // Go to next page
        nextPage() {
            this.goToPage(this.currentPage + 1);
        },

        // Go to previous page
        prevPage() {
            this.goToPage(this.currentPage - 1);
        },

        // Search functionality
        searchPhotos() {
            this.currentPage = 1; // Reset to first page
            this.updatePagination();
        },

        // Clear search
        clearSearch() {
            this.searchQuery = '';
            this.searchPhotos();
        },

        // Group images by month and year
        groupImagesByMonth() {
            this.groupedImages = {};

            this.images.forEach(image => {
                const date = new Date(image.timestamp);
                const monthYear = date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long'
                });

                if (!this.groupedImages[monthYear]) {
                    this.groupedImages[monthYear] = {
                        photos: [],
                        count: 0,
                        monthName: date.toLocaleDateString('en-US', { month: 'long' }),
                        year: date.getFullYear(),
                        sortDate: date
                    };
                }

                this.groupedImages[monthYear].photos.push(image);
                this.groupedImages[monthYear].count++;
            });

            console.log('Grouped images:', this.groupedImages);
        },

        // Get sorted month groups (newest first)
        getSortedMonthGroups() {
            return Object.entries(this.groupedImages)
                .sort(([, a], [, b]) => new Date(b.sortDate) - new Date(a.sortDate));
        },

        // Toggle between grouped and grid view
        toggleViewMode() {
            this.viewMode = this.viewMode === 'grouped' ? 'grid' : 'grouped';
            this.currentPage = 1; // Reset to first page
            this.updatePagination();
        },

        // Get month emoji based on month number
        getMonthEmoji(monthName) {
            const monthEmojis = {
                'January': '❄️',
                'February': '💝',
                'March': '🌸',
                'April': '🌷',
                'May': '🌺',
                'June': '☀️',
                'July': '🏖️',
                'August': '🌻',
                'September': '🍂',
                'October': '🎃',
                'November': '🦃',
                'December': '🎄'
            };
            return monthEmojis[monthName] || '📅';
        },

        // Open lightbox with selected image
        openLightbox(image) {
            console.log('Opening lightbox for image:', image);
            this.currentImage = image;
            // Find index in the full images array (not just displayed)
            this.currentIndex = this.images.findIndex(img => img.id === image.id);
            this.lightboxOpen = true;
            document.body.style.overflow = 'hidden'; // Prevent background scrolling

            // Add touch events for mobile swipe
            this.addSwipeSupport();
        },

        // Close lightbox
        closeLightbox() {
            this.lightboxOpen = false;
            document.body.style.overflow = 'auto'; // Re-enable scrolling

            // Remove touch events
            this.removeSwipeSupport();
        },

        // Format timestamp to readable date
        formatDate(timestamp) {
            if (!timestamp) return '';
            const date = new Date(timestamp);
            return '📅 ' + date.toLocaleDateString();
        },

        // Navigate to next image in lightbox
        nextImage() {
            if (this.currentIndex < this.images.length - 1) {
                this.currentIndex++;
                this.currentImage = this.images[this.currentIndex];
            }
        },

        // Navigate to previous image in lightbox
        prevImage() {
            if (this.currentIndex > 0) {
                this.currentIndex--;
                this.currentImage = this.images[this.currentIndex];
            }
        },

        // Download current image
        downloadImage() {
            if (this.currentImage && this.currentImage.full_url) {
                const link = document.createElement('a');
                link.href = this.currentImage.full_url;
                link.download = `gaurav-photo-${this.currentImage.id}.jpg`;
                link.target = '_blank';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                this.showNotification('📥 Photo downloaded! ✨', 'success');
            }
        },

        // Toggle selection mode
        toggleSelectionMode() {
            this.selectionMode = !this.selectionMode;
            if (!this.selectionMode) {
                this.selectedPhotos = [];
            }
        },

        // Toggle photo selection
        togglePhotoSelection(photo) {
            const index = this.selectedPhotos.findIndex(p => p.id === photo.id);
            if (index > -1) {
                this.selectedPhotos.splice(index, 1);
            } else {
                this.selectedPhotos.push(photo);
            }
        },

        // Check if photo is selected
        isPhotoSelected(photo) {
            return this.selectedPhotos.some(p => p.id === photo.id);
        },

        // Select all visible photos
        selectAllVisible() {
            this.displayedImages.forEach(photo => {
                if (!this.isPhotoSelected(photo)) {
                    this.selectedPhotos.push(photo);
                }
            });
        },

        // Clear all selections
        clearSelection() {
            this.selectedPhotos = [];
        },

        // Download selected photos
        async downloadSelected() {
            if (this.selectedPhotos.length === 0) {
                this.showNotification('Please select photos first! 📸', 'error');
                return;
            }

            this.showNotification(`📦 Preparing ${this.selectedPhotos.length} photos for download...`, 'info');

            // Download individually with staggered timing
            for (let i = 0; i < this.selectedPhotos.length; i++) {
                const photo = this.selectedPhotos[i];
                setTimeout(() => {
                    const link = document.createElement('a');
                    link.href = photo.full_url;
                    link.download = `gaurav-photo-${photo.id}.jpg`;
                    link.target = '_blank';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }, i * 500); // Stagger downloads
            }

            setTimeout(() => {
                this.showNotification(`✅ ${this.selectedPhotos.length} photos downloaded!`, 'success');
                this.selectedPhotos = [];
                this.selectionMode = false;
            }, this.selectedPhotos.length * 500 + 1000);
        },

        // Share current photo
        sharePhoto() {
            if (navigator.share && this.currentImage) {
                navigator.share({
                    title: 'Gaurav\'s Photo',
                    text: this.currentImage.caption || 'Check out this adorable photo!',
                    url: this.currentImage.full_url
                }).then(() => {
                    this.showNotification('📤 Photo shared! ✨', 'success');
                }).catch(() => {
                    this.copyPhotoLink();
                });
            } else {
                this.copyPhotoLink();
            }
        },

        // Copy photo link to clipboard
        copyPhotoLink() {
            if (this.currentImage && this.currentImage.full_url) {
                navigator.clipboard.writeText(this.currentImage.full_url).then(() => {
                    this.showNotification('🔗 Photo link copied! ✨', 'success');
                }).catch(() => {
                    this.showNotification('❌ Could not copy link', 'error');
                });
            }
        },

        // Start slideshow
        startSlideshow() {
            if (this.images.length === 0) return;

            this.slideshowActive = true;
            this.currentIndex = 0;
            this.currentImage = this.images[0];
            this.lightboxOpen = true;
            document.body.style.overflow = 'hidden';

            this.slideshowInterval = setInterval(() => {
                this.nextImage();
                if (this.currentIndex === this.images.length - 1) {
                    this.stopSlideshow();
                }
            }, 3000); // 3 seconds per photo

            this.showNotification('🎬 Slideshow started! ✨', 'success');
        },

        // Stop slideshow
        stopSlideshow() {
            this.slideshowActive = false;
            if (this.slideshowInterval) {
                clearInterval(this.slideshowInterval);
                this.slideshowInterval = null;
            }
            this.showNotification('⏹️ Slideshow stopped!', 'info');
        },

        // Toggle fullscreen
        toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().then(() => {
                    this.showNotification('🖥️ Fullscreen mode!', 'success');
                });
            } else {
                document.exitFullscreen().then(() => {
                    this.showNotification('📱 Exited fullscreen', 'info');
                });
            }
        },



        // Initialize cursor trail effect
        initCursorTrail() {
            let trails = [];
            const maxTrails = 5;

            document.addEventListener('mousemove', (e) => {
                // Create trail element
                const trail = document.createElement('div');
                trail.className = 'cursor-trail';
                trail.style.left = e.clientX - 10 + 'px';
                trail.style.top = e.clientY - 10 + 'px';

                document.body.appendChild(trail);
                trails.push(trail);

                // Remove old trails
                if (trails.length > maxTrails) {
                    const oldTrail = trails.shift();
                    if (oldTrail && oldTrail.parentNode) {
                        oldTrail.parentNode.removeChild(oldTrail);
                    }
                }

                // Remove trail after animation
                setTimeout(() => {
                    if (trail && trail.parentNode) {
                        trail.parentNode.removeChild(trail);
                        trails = trails.filter(t => t !== trail);
                    }
                }, 600);
            });
        },

        // Add floating decorative elements
        addFloatingElements() {
            const emojis = ['⭐', '🌟', '✨', '💫', '🎈', '🧸', '🍼', '👶'];

            for (let i = 0; i < 6; i++) {
                setTimeout(() => {
                    const element = document.createElement('div');
                    element.innerHTML = emojis[Math.floor(Math.random() * emojis.length)];
                    element.style.cssText = `
                        position: fixed;
                        font-size: 2rem;
                        pointer-events: none;
                        z-index: 1;
                        opacity: 0.3;
                        left: ${Math.random() * 100}%;
                        top: ${Math.random() * 100}%;
                        animation: float 4s ease-in-out infinite;
                        animation-delay: ${Math.random() * 2}s;
                    `;
                    document.body.appendChild(element);

                    // Remove after 10 seconds
                    setTimeout(() => {
                        if (element && element.parentNode) {
                            element.parentNode.removeChild(element);
                        }
                    }, 10000);
                }, i * 1000);
            }
        },

        // Setup service worker for offline support
        setupServiceWorker() {
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/sw.js')
                    .then(registration => {
                        console.log('Service Worker registered:', registration);
                    })
                    .catch(error => {
                        console.log('Service Worker registration failed:', error);
                    });
            }
        },

        // Setup auto-refresh for new images
        setupAutoRefresh() {
            // Check for new images every 30 seconds
            setInterval(async () => {
                const currentCount = this.images.length;
                await this.loadImages();

                // If new images found, show notification
                if (this.images.length > currentCount) {
                    const newCount = this.images.length - currentCount;
                    this.showNotification(`🎉 ${newCount} new photo${newCount > 1 ? 's' : ''} added! ✨`, 'success');
                }
            }, 30000); // 30 seconds

            console.log('Auto-refresh enabled: checking for new photos every 30 seconds');
        },



        // Set up intersection observer for lazy loading
        setupIntersectionObserver() {
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            const src = img.dataset.src;

                            if (src) {
                                img.src = src;
                                img.removeAttribute('data-src');
                            }

                            observer.unobserve(img);
                        }
                    });
                });

                // Observe all images with data-src attribute
                document.querySelectorAll('img[data-src]').forEach(img => {
                    imageObserver.observe(img);
                });
            }
        },

        // Refresh gallery (useful for manual updates)
        async refreshGallery() {
            await this.loadImages();
            // Show success message
            this.showNotification('📸 Gallery refreshed! ✨', 'success');
        },

        // Fetch historical photos from Telegram
        async fetchHistory() {
            try {
                this.showNotification('📚 Fetching photos from Telegram history...', 'info');

                const response = await fetch('/api/fetch-history');
                const result = await response.json();

                if (result.status === 'success') {
                    // Refresh the gallery to show new photos
                    await this.loadImages();

                    if (result.new_photos_added > 0) {
                        this.showNotification(
                            `🎉 Found ${result.new_photos_added} historical photos! Total: ${result.total_photos}`,
                            'success'
                        );
                    } else {
                        this.showNotification('📚 No new historical photos found', 'info');
                    }
                } else {
                    this.showNotification(`❌ Error: ${result.message}`, 'error');
                }
            } catch (error) {
                console.error('Error fetching history:', error);
                this.showNotification('❌ Failed to fetch history', 'error');
            }
        },

        // Show notification
        showNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.className = `fixed top-4 right-4 z-50 px-6 py-3 rounded-full text-white font-friendly text-sm transition-all duration-300 transform translate-x-full`;

            // Set colors based on type
            if (type === 'success') {
                notification.className += ' bg-mint-green';
            } else if (type === 'error') {
                notification.className += ' bg-baby-pink';
            } else {
                notification.className += ' bg-baby-blue';
            }

            notification.textContent = message;
            document.body.appendChild(notification);

            // Animate in
            setTimeout(() => {
                notification.classList.remove('translate-x-full');
            }, 100);

            // Animate out and remove
            setTimeout(() => {
                notification.classList.add('translate-x-full');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, 3000);
        },

        // Get page numbers for pagination
        getPageNumbers() {
            const pages = [];
            const maxVisible = 5;

            if (this.totalPages <= maxVisible) {
                // Show all pages if total is small
                for (let i = 1; i <= this.totalPages; i++) {
                    pages.push(i);
                }
            } else {
                // Show smart pagination
                const start = Math.max(1, this.currentPage - 2);
                const end = Math.min(this.totalPages, start + maxVisible - 1);

                for (let i = start; i <= end; i++) {
                    pages.push(i);
                }
            }

            return pages;
        },

        // Add advanced swipe support for mobile lightbox
        addSwipeSupport() {
            let startX = 0;
            let startY = 0;
            let endX = 0;
            let endY = 0;
            let startTime = 0;

            const touchStart = (e) => {
                startX = e.changedTouches[0].screenX;
                startY = e.changedTouches[0].screenY;
                startTime = Date.now();
            };

            const touchEnd = (e) => {
                endX = e.changedTouches[0].screenX;
                endY = e.changedTouches[0].screenY;
                this.handleSwipe();
            };

            const lightbox = document.querySelector('.fixed.inset-0');
            if (lightbox) {
                lightbox.addEventListener('touchstart', touchStart, { passive: true });
                lightbox.addEventListener('touchend', touchEnd, { passive: true });

                // Store event listeners for removal
                lightbox.swipeListeners = { touchStart, touchEnd };
            }
        },

        // Remove swipe support
        removeSwipeSupport() {
            const lightbox = document.querySelector('.fixed.inset-0');
            if (lightbox && lightbox.swipeListeners) {
                lightbox.removeEventListener('touchstart', lightbox.swipeListeners.touchStart);
                lightbox.removeEventListener('touchend', lightbox.swipeListeners.touchEnd);
                delete lightbox.swipeListeners;
            }
        },

        // Handle advanced swipe gestures
        handleSwipe() {
            const deltaX = endX - startX;
            const deltaY = endY - startY;
            const swipeTime = Date.now() - startTime;
            const minSwipeDistance = 50;
            const maxSwipeTime = 300;

            // Only process quick swipes
            if (swipeTime > maxSwipeTime) return;

            // Horizontal swipes for navigation
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
                if (deltaX > 0) {
                    // Swipe right - previous image
                    this.prevImage();
                } else {
                    // Swipe left - next image
                    this.nextImage();
                }
            }
            // Vertical swipe down to close
            else if (deltaY > minSwipeDistance && Math.abs(deltaY) > Math.abs(deltaX)) {
                this.closeLightbox();
            }
        },

        // Add pinch-to-zoom support
        addPinchZoom() {
            let initialDistance = 0;
            let currentScale = 1;

            const getDistance = (touches) => {
                const dx = touches[0].clientX - touches[1].clientX;
                const dy = touches[0].clientY - touches[1].clientY;
                return Math.sqrt(dx * dx + dy * dy);
            };

            const touchStart = (e) => {
                if (e.touches.length === 2) {
                    initialDistance = getDistance(e.touches);
                }
            };

            const touchMove = (e) => {
                if (e.touches.length === 2) {
                    e.preventDefault();
                    const currentDistance = getDistance(e.touches);
                    const scale = currentDistance / initialDistance;
                    currentScale = Math.min(Math.max(scale, 0.5), 3);

                    const img = e.target.closest('img');
                    if (img) {
                        img.style.transform = `scale(${currentScale})`;
                    }
                }
            };

            const touchEnd = () => {
                currentScale = 1;
                const img = document.querySelector('.lightbox-overlay img');
                if (img) {
                    img.style.transform = 'scale(1)';
                }
            };

            const lightbox = document.querySelector('.fixed.inset-0');
            if (lightbox) {
                lightbox.addEventListener('touchstart', touchStart, { passive: true });
                lightbox.addEventListener('touchmove', touchMove, { passive: false });
                lightbox.addEventListener('touchend', touchEnd, { passive: true });
            }
        },

        // Detect device type and capabilities
        detectDevice() {
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

            return { isMobile, isTouch, isIOS };
        },

        // Optimize for device
        optimizeForDevice() {
            const device = this.detectDevice();

            if (device.isMobile) {
                // Add mobile-specific optimizations
                document.body.classList.add('mobile-device');

                // Prevent zoom on input focus for iOS
                if (device.isIOS) {
                    const inputs = document.querySelectorAll('input');
                    inputs.forEach(input => {
                        input.addEventListener('focus', () => {
                            input.style.fontSize = '16px';
                        });
                    });
                }
            }

            if (device.isTouch) {
                document.body.classList.add('touch-device');
            }
        }
    };
}

// Initialize Alpine.js when the DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM loaded, initializing Alpine.js');

    // Check if Alpine.js is loaded
    if (typeof Alpine === 'undefined') {
        console.error('Alpine.js not loaded');
        return;
    }

    // Start Alpine.js
    Alpine.start();
});

// Keyboard navigation for lightbox
document.addEventListener('keydown', function (e) {
    const galleryApp = document.querySelector('[x-data*="galleryApp()"]');
    if (galleryApp && galleryApp.__x && galleryApp.__x.$data.lightboxOpen) {
        const data = galleryApp.__x.$data;

        switch (e.key) {
            case 'Escape':
                data.lightboxOpen = false;
                document.body.style.overflow = 'auto';
                break;
            case 'ArrowLeft':
                e.preventDefault();
                if (data.currentIndex > 0) {
                    data.prevImage();
                }
                break;
            case 'ArrowRight':
                e.preventDefault();
                if (data.currentIndex < data.images.length - 1) {
                    data.nextImage();
                }
                break;
            case 'd':
            case 'D':
                e.preventDefault();
                data.downloadImage();
                break;
            case 's':
            case 'S':
                e.preventDefault();
                data.sharePhoto();
                break;
            case 'f':
            case 'F':
                e.preventDefault();
                data.toggleFullscreen();
                break;
            case ' ':
                e.preventDefault();
                if (data.slideshowActive) {
                    data.stopSlideshow();
                } else {
                    data.startSlideshow();
                }
                break;
        }
    } else {
        // Global shortcuts when lightbox is closed
        const data = galleryApp.__x.$data;

        switch (e.key) {
            case 'a':
            case 'A':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    if (!data.selectionMode) {
                        data.toggleSelectionMode();
                    }
                    data.selectAllVisible();
                }
                break;
            case 'Escape':
                if (data.selectionMode) {
                    data.toggleSelectionMode();
                }
                break;
        }
    }
});

// Prevent body scrolling when lightbox is open
document.addEventListener('alpine:init', () => {
    console.log('Alpine init event fired');
    Alpine.directive('scroll-lock', (el, { expression }, { effect, cleanup }) => {
        effect(() => {
            if (expression === 'true') {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = 'auto';
            }
        });

        cleanup(() => {
            document.body.style.overflow = 'auto';
        });
    });
});