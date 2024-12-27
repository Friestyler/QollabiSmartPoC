// Global variables for Quill editors
let deGoudseQuill;
let baloiseQuill;

// Initialize page based on current route
document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    console.log('Current path:', path);

    // Initialize admin page
    if (path === '/' || path === '/admin') {
        console.log('Initializing admin page');
        initializeAdminPage();
    }
    // Initialize De Goudse page
    else if (path === '/degoudse') {
        console.log('Initializing De Goudse page');
        loadDeGoudseContent();
    }
    // Initialize Baloise page
    else if (path === '/baloise') {
        console.log('Initializing Baloise page');
        loadBaloiseContent();
    }
});

function initializeAdminPage() {
    // Initialize Quill editors
    if (document.getElementById('degoudse-editor')) {
        deGoudseQuill = new Quill('#degoudse-editor', {
            theme: 'snow',
            modules: {
                toolbar: [
                    ['bold', 'italic', 'underline'],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    ['link']
                ]
            }
        });
        deGoudseQuill.disable();
    }

    if (document.getElementById('baloise-editor')) {
        baloiseQuill = new Quill('#baloise-editor', {
            theme: 'snow',
            modules: {
                toolbar: [
                    ['bold', 'italic', 'underline'],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    ['link']
                ]
            }
        });
        baloiseQuill.disable();
    }

    // Add link update handlers for both companies
    for (let i = 1; i <= 4; i++) {
        handleLinkUpdate('degoudse', i);
        handleLinkUpdate('baloise', i);
    }

    // Load admin content
    loadAdminContent();
}

function loadAdminContent() {
    console.log('Loading admin content');
    loadAdminDeGoudseContent();
    loadAdminBaloiseContent();
}

function loadAdminDeGoudseContent() {
    console.log('Loading De Goudse admin content');
    fetch('/get_degoudse_settings')
        .then(response => response.json())
        .then(data => {
            console.log('Received De Goudse admin data:', data);
            data.forEach((item, index) => {
                if (index < 4) {
                    const titleInput = document.getElementById(`degoudse-title-${index + 1}`);
                    const linkInput = document.getElementById(`degoudse-link-${index + 1}`);
                    if (titleInput) titleInput.value = item.title || '';
                    if (linkInput) linkInput.value = item.link || '';
                } else if (deGoudseQuill && item.content) {
                    deGoudseQuill.root.innerHTML = item.content || '';
                }
            });
        })
        .catch(error => console.error('Error loading De Goudse admin content:', error));
}

function loadAdminBaloiseContent() {
    console.log('Loading Baloise admin content');
    fetch('/get_baloise_settings')
        .then(response => response.json())
        .then(data => {
            console.log('Received Baloise admin data:', data);
            data.forEach((item, index) => {
                if (index < 4) {
                    const titleInput = document.getElementById(`baloise-title-${index + 1}`);
                    const linkInput = document.getElementById(`baloise-link-${index + 1}`);
                    if (titleInput) titleInput.value = item.title || '';
                    if (linkInput) linkInput.value = item.link || '';
                } else if (baloiseQuill && item.content) {
                    baloiseQuill.root.innerHTML = item.content || '';
                }
            });
        })
        .catch(error => console.error('Error loading Baloise admin content:', error));
}

function toggleDeGoudseEdit(section) {
    const form = document.getElementById('degoudse-form');
    const sectionDiv = form.children[section - 1];
    const inputs = sectionDiv.querySelectorAll('input[type="text"]');
    const editBtn = sectionDiv.querySelector('.edit-btn');
    const saveBtn = sectionDiv.querySelector('.save-btn');
    
    if (section === 5) {
        if (deGoudseQuill) {
            deGoudseQuill.enable(!deGoudseQuill.isEnabled());
        }
    } else {
        inputs.forEach(input => {
            input.disabled = !input.disabled;
            input.style.backgroundColor = input.disabled ? '#f5f5f5' : 'white';
        });
    }
    
    if (editBtn) editBtn.style.display = 'none';
    if (saveBtn) saveBtn.style.display = 'block';
}

function toggleBaloiseEdit(section) {
    const form = document.getElementById('baloise-form');
    const sectionDiv = form.children[section - 1];
    const inputs = sectionDiv.querySelectorAll('input[type="text"]');
    const editBtn = sectionDiv.querySelector('.edit-btn');
    const saveBtn = sectionDiv.querySelector('.save-btn');
    
    if (section === 5) {
        if (baloiseQuill) {
            baloiseQuill.enable(!baloiseQuill.isEnabled());
        }
    } else {
        inputs.forEach(input => {
            input.disabled = !input.disabled;
            input.style.backgroundColor = input.disabled ? '#f5f5f5' : 'white';
        });
    }
    
    if (editBtn) editBtn.style.display = 'none';
    if (saveBtn) saveBtn.style.display = 'block';
}

function saveDeGoudseSettings(section) {
    console.log('Saving De Goudse section:', section);
    console.log('Starting save for De Goudse section:', section);
    const form = document.getElementById('degoudse-form');
    const sectionDiv = form.children[section - 1];
    const editBtn = sectionDiv.querySelector('.edit-btn');
    const saveBtn = sectionDiv.querySelector('.save-btn');
    
    let sectionData = {
        section: section,
        title: '',
        link: '',
        content: ''
    };

    if (section === 5) {
        sectionData.content = deGoudseQuill ? deGoudseQuill.root.innerHTML : '';
    } else {
        sectionData.title = document.getElementById(`degoudse-title-${section}`).value;
        sectionData.link = document.getElementById(`degoudse-link-${section}`).value;
    }

    console.log('Saving De Goudse data:', sectionData);

    fetch('/save_degoudse_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(sectionData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Settings saved successfully!');
            if (section === 5) {
                deGoudseQuill.disable();
            } else {
                const inputs = sectionDiv.querySelectorAll('input[type="text"]');
                inputs.forEach(input => {
                    input.disabled = true;
                    input.style.backgroundColor = '#f5f5f5';
                });
            }
            // Toggle buttons back
            if (editBtn) editBtn.style.display = 'block';
            if (saveBtn) saveBtn.style.display = 'none';
            
            // Reload the admin content
            loadAdminContent();
        } else {
            alert('Error saving settings: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error saving settings');
    });
}

function saveBaloiseSettings(section) {
    console.log('Starting save for Baloise section:', section);
    
    let sectionData = {
        section_number: section,
        title: '',
        link: '',
        content: ''
    };

    if (section === 5) {
        // Handle rich text content
        sectionData.content = baloiseQuill ? baloiseQuill.root.innerHTML : '';
        console.log('Saving Baloise rich text:', sectionData.content);
    } else {
        // Handle regular section
        sectionData.title = document.getElementById(`baloise-title-${section}`).value;
        sectionData.link = document.getElementById(`baloise-link-${section}`).value;
        console.log('Saving Baloise section data:', sectionData);
    }

    fetch('/save_baloise_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(sectionData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Baloise settings saved successfully');
            
            // Disable inputs after saving
            if (section === 5) {
                baloiseQuill.disable();
            } else {
                const form = document.getElementById('baloise-form');
                const sectionDiv = form.children[section - 1];
                const inputs = sectionDiv.querySelectorAll('input[type="text"]');
                inputs.forEach(input => {
                    input.disabled = true;
                    input.style.backgroundColor = '#f5f5f5';
                });
            }

            // Toggle buttons
            const sectionDiv = document.getElementById('baloise-form').children[section - 1];
            const editBtn = sectionDiv.querySelector('.edit-btn');
            const saveBtn = sectionDiv.querySelector('.save-btn');
            if (editBtn) editBtn.style.display = 'block';
            if (saveBtn) saveBtn.style.display = 'none';

            // Reload the content
            loadAdminContent();
        } else {
            console.error('Error saving Baloise settings:', data.message);
            alert('Error saving settings: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error saving Baloise settings:', error);
        alert('Error saving settings');
    });
}

function createEmptyState() {
    console.log('Creating empty state');
    const emptyState = `
        <div class="empty-state">
            <div class="empty-state-content">
                <div class="empty-state-icon">📊</div>
                <h3>Ask the Qollabi Team for new Dashboard</h3>
                <a href="mailto:support@qollabi.com" class="contact-button">
                    Contact support@qollabi.com
                </a>
            </div>
        </div>
    `;
    console.log('Empty state HTML:', emptyState);
    return emptyState;
}

function loadDeGoudseContent() {
    console.log('Loading De Goudse content');
    fetch('/get_degoudse_settings')
        .then(response => response.json())
        .then(data => {
            console.log('Received De Goudse data:', data);
            
            // Handle sections 1-4
            for(let i = 0; i < 4; i++) {
                const titleElement = document.getElementById(`degoudse-title-${i+1}`);
                const contentFrame = document.getElementById(`degoudse-content-${i+1}`);
                const frameElement = document.getElementById(`degoudse-frame-${i+1}`);
                
                console.log(`Processing De Goudse section ${i+1}:`, {
                    title: data[i]?.title,
                    link: data[i]?.link,
                    hasContentFrame: !!contentFrame,
                    hasFrame: !!frameElement
                });

                if (contentFrame && frameElement) {
                    if (data[i]?.link && data[i].link.trim()) {
                        // Has valid link - show iframe and remove empty state
                        console.log(`Section ${i+1}: Showing iframe`);
                        frameElement.style.display = 'block';
                        frameElement.src = data[i].link;
                        const existingEmptyState = contentFrame.querySelector('.empty-state');
                        if (existingEmptyState) {
                            existingEmptyState.remove();
                        }
                    } else {
                        // No link - hide iframe and show empty state
                        console.log(`Section ${i+1}: Showing empty state`);
                        frameElement.style.display = 'none';
                        if (!contentFrame.querySelector('.empty-state')) {
                            contentFrame.innerHTML = createEmptyState();
                        }
                    }
                    
                    if (titleElement) {
                        titleElement.textContent = data[i]?.title || `Section ${i + 1}`;
                    }
                }
            }

            // Handle section 5
            const contentElement = document.getElementById('degoudse-text-content-5');
            if (contentElement) {
                if (!data[4]?.content || !data[4].content.trim()) {
                    contentElement.innerHTML = createEmptyState();
                } else {
                    contentElement.innerHTML = data[4].content;
                }
            }
        })
        .catch(error => console.error('Error:', error));
}

function loadBaloiseContent() {
    console.log('Loading Baloise content');
    fetch('/get_baloise_settings')
        .then(response => response.json())
        .then(data => {
            console.log('Received Baloise data:', data);
            
            // Handle sections 1-4
            for(let i = 0; i < 4; i++) {
                const titleElement = document.getElementById(`baloise-title-${i+1}`);
                const contentFrame = document.getElementById(`baloise-content-${i+1}`);
                const frameElement = document.getElementById(`baloise-frame-${i+1}`);
                
                console.log(`Processing Baloise section ${i+1}:`, {
                    title: data[i]?.title,
                    link: data[i]?.link,
                    hasContentFrame: !!contentFrame,
                    hasFrame: !!frameElement
                });

                if (contentFrame && frameElement) {
                    if (data[i]?.link && data[i].link.trim()) {
                        // Has valid link - show iframe and remove empty state
                        console.log(`Section ${i+1}: Showing iframe`);
                        frameElement.style.display = 'block';
                        frameElement.src = data[i].link;
                        const existingEmptyState = contentFrame.querySelector('.empty-state');
                        if (existingEmptyState) {
                            existingEmptyState.remove();
                        }
                    } else {
                        // No link - hide iframe and show empty state
                        console.log(`Section ${i+1}: Showing empty state`);
                        frameElement.style.display = 'none';
                        if (!contentFrame.querySelector('.empty-state')) {
                            contentFrame.innerHTML = createEmptyState();
                        }
                    }
                    
                    if (titleElement) {
                        titleElement.textContent = data[i]?.title || `Section ${i + 1}`;
                    }
                }
            }

            // Handle section 5
            const contentElement = document.getElementById('baloise-text-content-5');
            if (contentElement) {
                if (!data[4]?.content || !data[4].content.trim()) {
                    contentElement.innerHTML = createEmptyState();
                } else {
                    contentElement.innerHTML = data[4].content;
                }
            }
        })
        .catch(error => console.error('Error:', error));
}

// Add this to ensure content is loaded when the page loads
document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    if (path === '/degoudse') {
        loadDeGoudseContent();
    }
});

// Make sure we call this function when on the Baloise page
document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    if (path === '/baloise') {
        loadBaloiseContent();
    }
});

function handleIframeError(frameElement) {
    frameElement.onerror = function() {
        console.error('Failed to load iframe content');
        frameElement.insertAdjacentHTML('afterend', 
            '<div class="error-message">Failed to load content. Please try again later.</div>'
        );
    };
}

// Add this to your load functions
if (frameElement) {
    handleIframeError(frameElement);
}

function setupIframe(frameElement) {
    if (!frameElement) return;

    frameElement.onload = function() {
        // Fade in the iframe
        this.style.opacity = '1';
        
        // Try to adjust height based on content
        try {
            const height = frameElement.contentWindow.document.body.scrollHeight;
            frameElement.style.height = `${height}px`;
        } catch (e) {
            console.log('Could not adjust iframe height (expected for cross-origin content)');
            // Use default height from CSS
        }
    };

    // Add error handling
    frameElement.onerror = function() {
        console.error('Failed to load iframe content');
        frameElement.insertAdjacentHTML('afterend', 
            '<div class="error-message">Failed to load content. Please try again later.</div>'
        );
    };
} 

window.addEventListener('error', function(e) {
    if (e.message.includes('CORS') || e.message.includes('cross-origin')) {
        console.log('CORS error detected - this is expected for third-party content');
    }
}); 

// Add this function to handle real-time updates
function handleLinkUpdate(company, sectionNumber) {
    const linkInput = document.getElementById(`${company}-link-${sectionNumber}`);
    const titleInput = document.getElementById(`${company}-title-${sectionNumber}`);
    
    if (!linkInput) return;

    linkInput.addEventListener('input', function() {
        // Automatically save when link is updated
        const formData = new FormData();
        formData.append('section_number', sectionNumber);
        formData.append('title', titleInput ? titleInput.value : '');
        formData.append('link', this.value.trim());

        fetch(`/update_${company}_settings`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log(`Updated ${company} section ${sectionNumber}:`, data);
            // Reload the corresponding page content
            if (company === 'degoudse') {
                loadDeGoudseContent();
            } else if (company === 'baloise') {
                loadBaloiseContent();
            }
        })
        .catch(error => console.error('Error updating settings:', error));
    });
} 