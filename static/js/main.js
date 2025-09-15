// Main JavaScript for the gallery application

// Gallery application logic
function galleryApp() {
    return {
        loading: true,
        images: [],
        lightboxOpen: false,
        currentImage: {},

        // Initialize the gallery
        async init() {
            console.log('Initializing gallery app');
            await this.loadImages();
            this.setupIntersectionObserver();
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
            } catch (error) {
                console.error('Error loading images:', error);
                // Show error message to user
                this.images = [];
            } finally {
                this.loading = false;
            }
        },

        // Open lightbox with selected image
        openLightbox(image) {
            console.log('Opening lightbox for image:', image);
            this.currentImage = image;
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
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
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
        },

        // Add swipe support for mobile lightbox
        addSwipeSupport() {
            let startX = 0;
            let endX = 0;
            
            const touchStart = (e) => {
                startX = e.changedTouches[0].screenX;
            };
            
            const touchEnd = (e) => {
                endX = e.changedTouches[0].screenX;
                this.handleSwipe();
            };
            
            const lightbox = document.querySelector('.fixed.inset-0');
            if (lightbox) {
                lightbox.addEventListener('touchstart', touchStart);
                lightbox.addEventListener('touchend', touchEnd);
                
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

        // Handle swipe gesture
        handleSwipe() {
            // Close lightbox on swipe left or right
            this.closeLightbox();
        }
    };
}

// Initialize Alpine.js when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
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
document.addEventListener('keydown', function(e) {
    // Close lightbox with Escape key
    if (e.key === 'Escape') {
        const lightbox = document.querySelector('[x-data*="galleryApp()"]');
        if (lightbox && lightbox.__x) {
            lightbox.__x.$data.lightboxOpen = false;
            document.body.style.overflow = 'auto';
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