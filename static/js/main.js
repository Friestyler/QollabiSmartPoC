// Function to save De Goudse settings
function saveDeGoudseSettings() {
    const settings = {
        degoudse: []
    };

    // Collect first 4 subsections
    for (let i = 1; i <= 4; i++) {
        settings.degoudse.push({
            title: document.getElementById(`degoudse-title-${i}`).value,
            link: document.getElementById(`degoudse-link-${i}`).value
        });
    }

    // Add section 5 with text content
    settings.degoudse.push({
        content: document.getElementById('degoudse-text-5').value
    });

    // Send to backend
    fetch('/save_degoudse_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('De Goudse settings saved successfully!');
        } else {
            alert('Error saving settings: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error saving settings');
    });
}

// Function to save Baloise settings
function saveBaloiseSettings() {
    const settings = {
        baloise: []
    };

    // Collect first 4 subsections
    for (let i = 1; i <= 4; i++) {
        settings.baloise.push({
            title: document.getElementById(`baloise-title-${i}`).value,
            link: document.getElementById(`baloise-link-${i}`).value
        });
    }

    // Add section 5 with text content
    settings.baloise.push({
        content: document.getElementById('baloise-text-5').value
    });

    // Send to backend
    fetch('/save_baloise_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Baloise settings saved successfully!');
        } else {
            alert('Error saving settings: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error saving settings');
    });
}

// Function to load content for De Goudse page
function loadDeGoudseContent() {
    fetch('/get_degoudse_settings')
        .then(response => response.json())
        .then(data => {
            data.forEach((item, index) => {
                if (index < 4) {
                    const title = document.getElementById(`title-${index + 1}`);
                    const frame = document.getElementById(`frame-${index + 1}`);
                    
                    if (title && item.title) {
                        title.textContent = item.title;
                    }
                    
                    if (frame && item.link) {
                        frame.src = item.link;
                    }
                } else {
                    const textContent = document.getElementById('text-content-5');
                    if (textContent && item.content) {
                        textContent.textContent = item.content;
                    }
                }
            });
        })
        .catch(error => console.error('Error:', error));
}

// Function to load content for Baloise page
function loadBaloiseContent() {
    fetch('/get_baloise_settings')
        .then(response => response.json())
        .then(data => {
            data.forEach((item, index) => {
                if (index < 4) {
                    const title = document.getElementById(`baloise-title-${index + 1}`);
                    const frame = document.getElementById(`baloise-frame-${index + 1}`);
                    
                    if (title && item.title) {
                        title.textContent = item.title;
                    }
                    
                    if (frame && item.link) {
                        frame.src = item.link;
                    }
                } else {
                    const textContent = document.getElementById('baloise-text-content-5');
                    if (textContent && item.content) {
                        textContent.textContent = item.content;
                    }
                }
            });
        })
        .catch(error => console.error('Error:', error));
}

function toggleDeGoudseEdit() {
    const form = document.getElementById('degoudse-form');
    const inputs = form.querySelectorAll('input, textarea');
    const editBtn = document.getElementById('degoudse-edit');
    const saveBtn = document.getElementById('degoudse-save');
    
    inputs.forEach(input => {
        input.disabled = !input.disabled;
    });
    
    editBtn.style.display = editBtn.style.display === 'none' ? 'block' : 'none';
    saveBtn.style.display = saveBtn.style.display === 'none' ? 'block' : 'none';
}

function toggleBaloiseEdit() {
    const form = document.getElementById('baloise-form');
    const inputs = form.querySelectorAll('input, textarea');
    const editBtn = document.getElementById('baloise-edit');
    const saveBtn = document.getElementById('baloise-save');
    
    inputs.forEach(input => {
        input.disabled = !input.disabled;
    });
    
    editBtn.style.display = editBtn.style.display === 'none' ? 'block' : 'none';
    saveBtn.style.display = saveBtn.style.display === 'none' ? 'block' : 'none';
}

function loadAdminData() {
    // Load De Goudse settings
    fetch('/get_degoudse_settings')
        .then(response => response.json())
        .then(data => {
            data.forEach((item, index) => {
                if (index < 4) {
                    document.getElementById(`degoudse-title-${index + 1}`).value = item.title || '';
                    document.getElementById(`degoudse-link-${index + 1}`).value = item.link || '';
                } else {
                    document.getElementById('degoudse-text-5').value = item.content || '';
                }
            });
        })
        .catch(error => console.error('Error:', error));

    // Load Baloise settings
    fetch('/get_baloise_settings')
        .then(response => response.json())
        .then(data => {
            data.forEach((item, index) => {
                if (index < 4) {
                    document.getElementById(`baloise-title-${index + 1}`).value = item.title || '';
                    document.getElementById(`baloise-link-${index + 1}`).value = item.link || '';
                } else {
                    document.getElementById('baloise-text-5').value = item.content || '';
                }
            });
        })
        .catch(error => console.error('Error:', error));
}

// Add event listeners based on current page
document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    
    if (path.includes('/degoudse')) {
        loadDeGoudseContent();
    } else if (path.includes('/baloise')) {
        loadBaloiseContent();
    } else if (path.includes('/admin')) {
        loadAdminData();
    }
}); 