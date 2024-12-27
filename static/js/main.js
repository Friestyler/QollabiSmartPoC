function saveSettings() {
    const settings = {
        degoudse: [],
        baloise: []
    };

    // Collect De Goudse settings
    for (let i = 1; i <= 5; i++) {
        settings.degoudse.push({
            title: document.getElementById(`degoudse-title-${i}`).value,
            link: document.getElementById(`degoudse-link-${i}`).value
        });
    }

    // Collect Baloise settings
    for (let i = 1; i <= 5; i++) {
        settings.baloise.push({
            title: document.getElementById(`baloise-title-${i}`).value,
            link: document.getElementById(`baloise-link-${i}`).value
        });
    }

    // Send to server
    fetch('/save_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Settings saved successfully!');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error saving settings');
    });
}

function loadDeGoudseContent() {
    fetch('/get_degoudse_settings')
        .then(response => response.json())
        .then(data => {
            data.forEach((item, index) => {
                if (index < 4) {
                    document.getElementById(`title-${index + 1}`).textContent = item.title;
                    document.getElementById(`frame-${index + 1}`).src = item.link;
                } else {
                    document.getElementById('text-content-5').textContent = item.content;
                }
            });
        })
        .catch(error => console.error('Error:', error));
}

function loadBaloiseContent() {
    fetch('/get_baloise_settings')
        .then(response => response.json())
        .then(data => {
            data.forEach((item, index) => {
                if (index < 4) {
                    document.getElementById(`baloise-title-${index + 1}`).textContent = item.title;
                    document.getElementById(`baloise-frame-${index + 1}`).src = item.link;
                } else {
                    document.getElementById('baloise-text-content-5').textContent = item.content;
                }
            });
        })
        .catch(error => console.error('Error:', error));
}

// Update the event listener to handle both pages
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('degoudse')) {
        loadDeGoudseContent();
    } else if (window.location.pathname.includes('baloise')) {
        loadBaloiseContent();
    }
}); 