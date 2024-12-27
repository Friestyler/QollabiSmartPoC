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
    console.log('Saving Baloise section:', section);
    console.log('Starting save for Baloise section:', section);
    const form = document.getElementById('baloise-form');
    const sectionDiv = form.children[section - 1];
    const editBtn = sectionDiv.querySelector('.edit-btn');
    const saveBtn = sectionDiv.querySelector('.save-btn');
    
    let sectionData = {
        section_number: section,
        title: '',
        link: '',
        content: ''
    };

    if (section === 5) {
        sectionData.content = baloiseQuill ? baloiseQuill.root.innerHTML : '';
    } else {
        sectionData.title = document.getElementById(`baloise-title-${section}`).value;
        sectionData.link = document.getElementById(`baloise-link-${section}`).value;
    }

    console.log('Saving Baloise data:', sectionData);

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
            alert('Settings saved successfully!');
            if (section === 5) {
                baloiseQuill.disable();
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

function loadDeGoudseContent() {
    console.log('Starting loadDeGoudseContent');
    fetch('/get_degoudse_settings')
        .then(response => response.json())
        .then(data => {
            console.log('Received De Goudse data:', data);
            
            // Handle sections 1-4
            for(let i = 0; i < 4; i++) {
                const titleElement = document.getElementById(`degoudse-title-${i+1}`);
                const frameElement = document.getElementById(`degoudse-frame-${i+1}`);
                
                if (data[i] && titleElement) {
                    titleElement.textContent = data[i].title || 'No title set';
                    if (data[i].link) frameElement.src = data[i].link;
                }
            }

            // Handle section 5 (rich text)
            const contentElement = document.getElementById('degoudse-text-content-5');
            if (data[4] && contentElement) {
                contentElement.innerHTML = data[4].content || '';
            }
        })
        .catch(error => console.error('Error:', error));
}

function loadBaloiseContent() {
    console.log('Starting loadBaloiseContent');
    fetch('/get_baloise_settings')
        .then(response => response.json())
        .then(data => {
            console.log('Received Baloise data:', data);
            
            // Check if we have data
            if (!data || data.length === 0) {
                console.warn('No Baloise data received');
                return;
            }

            // Handle sections 1-4
            for(let i = 0; i < 4; i++) {
                const titleElement = document.getElementById(`baloise-title-${i+1}`);
                const frameElement = document.getElementById(`baloise-frame-${i+1}`);
                
                console.log(`Looking for Baloise section ${i+1}:`, {
                    data: data[i],
                    titleElement: titleElement,
                    frameElement: frameElement
                });

                if (data[i]) {
                    if (titleElement) {
                        console.log(`Setting Baloise title ${i+1} to:`, data[i].title);
                        titleElement.textContent = data[i].title || 'No title set';
                    } else {
                        console.warn(`Title element for Baloise section ${i+1} not found`);
                    }
                    
                    if (frameElement && data[i].link) {
                        console.log(`Setting Baloise frame ${i+1} src to:`, data[i].link);
                        frameElement.src = data[i].link;
                    }
                }
            }

            // Handle section 5 (rich text)
            const contentElement = document.getElementById('baloise-text-content-5');
            console.log('Looking for Baloise section 5:', {
                data: data[4],
                contentElement: contentElement
            });
            
            if (data[4] && contentElement) {
                console.log('Setting Baloise section 5 content:', data[4].content);
                contentElement.innerHTML = data[4].content || '';
            }
        })
        .catch(error => {
            console.error('Error loading Baloise content:', error);
        });
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