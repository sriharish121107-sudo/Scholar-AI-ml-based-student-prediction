// Scholar AI - Premium Frontend Application Script

document.addEventListener("DOMContentLoaded", function() {
    // 1. Initialize Theme Engine (Dark / Light Mode)
    initThemeEngine();

    // 2. Initialize HTML5 Canvas Neural Network Background (if canvas is present)
    initNeuralNetworkCanvas();

    // 3. Initialize Notification Alerts Bell polling
    initNotificationCenter();
});

/* 
   ==========================================================================
   1. Theme Engine (Dark / Light Theme Toggle)
   ==========================================================================
*/
function initThemeEngine() {
    const savedTheme = localStorage.getItem("scholar-ai-theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    
    // Bind toggle buttons (if present)
    const toggleBtns = document.querySelectorAll(".theme-toggle-btn");
    toggleBtns.forEach(btn => {
        updateThemeIcon(btn, savedTheme);
        
        btn.addEventListener("click", function() {
            const currentTheme = document.documentElement.getAttribute("data-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            
            document.documentElement.setAttribute("data-theme", newTheme);
            localStorage.setItem("scholar-ai-theme", newTheme);
            
            toggleBtns.forEach(b => updateThemeIcon(b, newTheme));
            showToast(`Theme switched to ${newTheme} mode.`, "bg-info");
        });
    });
}

function updateThemeIcon(btn, theme) {
    const icon = btn.querySelector("i");
    if (!icon) return;
    if (theme === "dark") {
        icon.className = "bi bi-sun-fill text-warning";
    } else {
        icon.className = "bi bi-moon-stars-fill text-primary";
    }
}

/* 
   ==========================================================================
   2. HTML5 Canvas Neural Network Particle Animation
   ==========================================================================
*/
function initNeuralNetworkCanvas() {
    const canvas = document.getElementById("neuralCanvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let particles = [];
    const particleCount = 65;
    const connectionDistance = 110;

    // Resize handler
    function resizeCanvas() {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
    }
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Particle constructor
    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.vx = (Math.random() - 0.5) * 0.6;
            this.vy = (Math.random() - 0.5) * 0.6;
            this.radius = Math.random() * 2.5 + 1;
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            // Bounce off walls
            if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
            if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(99, 102, 241, 0.4)"; // Indigo with opacity
            ctx.fill();
        }
    }

    // Initialize particles
    for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
    }

    // Animation loop
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw and update particles
        particles.forEach(p => {
            p.update();
            p.draw();
        });

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < connectionDistance) {
                    const alpha = (1 - dist / connectionDistance) * 0.15;
                    ctx.strokeStyle = `rgba(99, 102, 241, ${alpha})`;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(animate);
    }

    animate();
}

/* 
   ==========================================================================
   3. Notification Center Dropdown & Alert Polling
   ==========================================================================
*/
function initNotificationCenter() {
    // Run once on load
    fetchNotifications();

    // Poll every 30 seconds
    setInterval(fetchNotifications, 30000);
}

function fetchNotifications() {
    const listContainer = document.getElementById("notificationList");
    const badge = document.getElementById("notificationBadge");
    
    if (!listContainer) return;

    fetch("/api/notifications")
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const list = data.notifications;
            const unread = list.filter(n => !n.is_read).length;
            
            // Badge visibility
            if (unread > 0) {
                badge.classList.remove("d-none");
                badge.textContent = unread;
            } else {
                badge.classList.add("d-none");
            }
            
            // Populate list
            listContainer.innerHTML = "";
            if (list.length === 0) {
                listContainer.innerHTML = `<li class="px-3 py-2 text-center text-secondary small">No alerts currently</li>`;
                return;
            }
            
            list.forEach(n => {
                let badgeClass = "bg-primary";
                if (n.type === "danger") badgeClass = "bg-danger";
                else if (n.type === "success") badgeClass = "bg-success";
                else if (n.type === "warning") badgeClass = "bg-warning text-dark";
                
                const itemHtml = `
                    <li class="px-3 py-2 border-bottom d-flex align-items-start gap-2 ${n.is_read ? 'opacity-70' : 'fw-semibold bg-light-subtle'}">
                        <span class="badge ${badgeClass} fs-8 mt-1" style="width: 8px; height: 8px; border-radius: 50%; padding:0;"></span>
                        <div style="flex:1;">
                            <span class="d-block small text-dark-emphasis">${n.message}</span>
                            <span class="text-secondary" style="font-size: 0.725rem;">${n.created_at.substring(11, 16)}</span>
                        </div>
                        ${!n.is_read ? `<button class="btn btn-link p-0 text-primary small" onclick="markNotificationRead(${n.id}, event)"><i class="bi bi-check-circle"></i></button>` : ''}
                    </li>
                `;
                listContainer.innerHTML += itemHtml;
            });
            
            // Add clear all option
            listContainer.innerHTML += `
                <li class="p-2 text-center bg-light">
                    <button class="btn btn-sm btn-link text-primary text-decoration-none py-0 w-100 fw-bold" onclick="markAllNotificationsRead(event)">
                        Mark all as read
                    </button>
                </li>
            `;
        }
    })
    .catch(err => console.error("Error fetching notifications:", err));
}

function markNotificationRead(id, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    fetch(`/api/notifications/read`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            fetchNotifications();
        }
    })
    .catch(err => console.error("Error marking notification read:", err));
}

function markAllNotificationsRead(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    fetch(`/api/notifications/read`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ all: true })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            fetchNotifications();
            showToast("All notifications marked as read.", "bg-success");
        }
    })
    .catch(err => console.error("Error marking all read:", err));
}

/* 
   ==========================================================================
   4. Global Toast Alert helper
   ==========================================================================
*/
function showToast(message, bgClass = 'bg-primary') {
    const toastEl = document.getElementById('appToast');
    const msgEl = document.getElementById('toastMessage');
    
    if (!toastEl || !msgEl) return;
    
    toastEl.className = 'toast align-items-center text-white border-0 ' + bgClass;
    msgEl.textContent = message;
    
    const toast = new bootstrap.Toast(toastEl, {
        delay: 3500
    });
    toast.show();
}
