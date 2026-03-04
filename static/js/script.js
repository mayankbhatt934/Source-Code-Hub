// =========================================
// INITIALIZATION & UI EFFECTS
// =========================================
AOS.init({ duration: 1000, once: false });

const glass = document.querySelector('.glass-bg');
document.addEventListener('mousemove', (e) => {
    glass.style.background = `radial-gradient(circle at ${e.clientX}px ${e.clientY}px, rgba(0, 210, 255, 0.1), transparent 20%)`;
});

function toggleMobileMenu() { 
    document.getElementById('nav-menu').classList.toggle('show'); 
}

// =========================================
// COPY FUNCTIONALITY
// =========================================
function copyMainCode(elementId, btn) {
    const code = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(code);
    const originalColor = btn.style.background;
    btn.innerText = 'Copied!'; 
    btn.style.background = '#00ff88'; 
    btn.style.color = '#000';
    setTimeout(() => { 
        btn.innerText = 'Copy Script'; 
        btn.style.background = originalColor || '#00d2ff'; 
    }, 2000);
}

function copyPrompt(btn, text) {
    navigator.clipboard.writeText(text);
    const original = btn.innerText;
    btn.innerText = 'Copied!'; 
    btn.classList.add('copied');
    setTimeout(() => { 
        btn.innerText = original; 
        btn.classList.remove('copied'); 
    }, 2000);
}

// =========================================
// NAVIGATION & AUTH UI
// =========================================
let isLoggedIn = false; 

function switchPage(pageId) {
    document.querySelectorAll('.page-section').forEach(page => page.classList.remove('active'));
    document.querySelectorAll('.nav-links li').forEach(link => link.classList.remove('active'));
    document.getElementById('page-' + pageId).classList.add('active');
    
    const navItem = document.getElementById('nav-' + pageId);
    if(navItem) navItem.classList.add('active');
    
    document.getElementById('nav-menu').classList.remove('show');
    setTimeout(() => AOS.refresh(), 100);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function switchAuthPage() {
    if (isLoggedIn) {
        loadProfile();
        switchPage('profile');
    } else {
        switchPage('login');
    }
}

let isFlipped = false;
function toggleFlipCard() {
    const innerBox = document.getElementById('flip-inner-box');
    const mainTitle = document.getElementById('auth-main-title');
    isFlipped = !isFlipped;
    innerBox.classList.toggle('flipped');
    mainTitle.innerHTML = isFlipped 
        ? `Create <span style="color:#00d2ff;">Account</span>` 
        : `Access <span style="color:#00d2ff;">Account</span>`;
}

function setAuthMode(mode) {
    const toggle = document.getElementById('auth-toggle');
    const btnN = document.getElementById('btn-normal');
    const btnP = document.getElementById('btn-premium');
    const span = document.getElementById('login-title-span');
    const flip = document.getElementById('flip-container');
    const lock = document.getElementById('premium-lock-overlay');
    
    if (mode === 'premium') {
        toggle.classList.add('premium-mode'); 
        btnP.classList.add('active'); 
        btnN.classList.remove('active'); 
        span.style.color = '#f5af19'; 
        flip.classList.add('blurred-locked'); 
        lock.classList.add('show');
    } else {
        toggle.classList.remove('premium-mode'); 
        btnN.classList.add('active'); 
        btnP.classList.remove('active'); 
        span.style.color = '#00d2ff'; 
        flip.classList.remove('blurred-locked'); 
        lock.classList.remove('show');
    }
}

// =========================================
// SESSION CHECKER & PREMIUM UNLOCKER
// =========================================

// Auto-login checker on page reload
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/profile');
        if (res.ok) {
            const data = await res.json();
            
            isLoggedIn = true;
            document.getElementById('nav-login').innerText = "Profile";
            
            if (data.is_premium) {
                unlockPremiumRoom();
            }
        }
    } catch (e) {
        console.log("No active session found.");
    }
});

// Helper function to safely unlock the room and fetch the real code
function unlockPremiumRoom() {
    const block = document.getElementById('premium-code-block');
    if (block) {
        // Securely fetch the real code from the Python backend
        fetch('/api/get-premium-code')
            .then(res => res.json())
            .then(codeData => {
                if (codeData.status === 'success') {
                    const codeElement = document.getElementById('premium-secret-code');
                    if (codeElement) codeElement.innerText = codeData.code;
                }
            })
            .catch(err => console.error("Error fetching premium code", err));

        // Remove the visual locks
        block.style.filter = 'none';
        block.style.pointerEvents = 'auto';
        block.style.opacity = '1';
        block.style.userSelect = 'auto';         
        block.style.webkitUserSelect = 'auto';   
        
        const unlockBtn = document.getElementById('premium-unlock-btn');
        if (unlockBtn) unlockBtn.style.display = 'none';
    }
}

// =========================================
// PROFILE LOGIC
// =========================================
async function loadProfile() {
    try {
        const res = await fetch('/api/profile');
        const data = await res.json();

        if (res.ok) {
            document.getElementById('prof-name').value = data.name;
            document.getElementById('prof-email').value = data.email;

            if (data.photo) {
                document.getElementById('profile-img').src = data.photo;
            } else {
                document.getElementById('profile-img').src = `https://ui-avatars.com/api/?name=${data.name}&background=00d2ff&color=fff`;
            }

            const badge = document.getElementById('profile-status-badge');
            const expiryText = document.getElementById('profile-expiry');

            if (data.is_premium) {
                badge.innerText = "Premium Account";
                badge.className = "status-badge premium";
                if (data.expiry) {
                    expiryText.style.display = 'block';
                    expiryText.innerHTML = `Expires: <span style="color:white;">${data.expiry}</span>`;
                }
                
                unlockPremiumRoom();
                
            } else {
                badge.innerText = "Basic Account";
                badge.className = "status-badge basic";
                expiryText.style.display = 'none';
            }
        }
    } catch (e) { console.error("Failed to load profile", e); }
}

async function updateProfileName(e) {
    e.preventDefault();
    const newName = document.getElementById('prof-name').value;
    await fetch('/api/update-profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName })
    });
    alert("Profile Updated Successfully!");
    loadProfile();
}

function uploadPhoto(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = async function(e) {
            const base64Image = e.target.result;
            document.getElementById('profile-img').src = base64Image;
            await fetch('/api/update-profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ photo: base64Image })
            });
            alert("Profile Photo Updated!");
        }
        reader.readAsDataURL(file);
    }
}

async function handleLogout() {
    await fetch('/logout', { method: 'POST' });
    isLoggedIn = false;
    document.getElementById('nav-login').innerText = "Account";
    
    // Lock premium room again visually
    const block = document.getElementById('premium-code-block');
    if (block) {
        block.style.filter = 'blur(5px)'; 
        block.style.pointerEvents = 'none'; 
        block.style.opacity = '0.6';
        block.style.userSelect = 'none';
        block.style.webkitUserSelect = 'none';
    }
    
    const unlockBtn = document.getElementById('premium-unlock-btn');
    if (unlockBtn) unlockBtn.style.display = 'block';

    // Wipe the real premium code out of the HTML so it can't be stolen after logout
    const codeElement = document.getElementById('premium-secret-code');
    if (codeElement) {
        codeElement.innerText = `# ----------------------------------------
# PREMIUM AI TRADING ALGORITHM [LOCKED]
# ----------------------------------------
# This code is safely hidden on the backend server.
# Purchase Premium to unlock and inject the real code here!
def execute_premium_trade():
    pass`;
    }
    
    switchPage('home');
    alert("You have been logged out.");
}

// =========================================
// GOOGLE PAY / UPI INTEGRATION
// =========================================
let currentPlan = "";
let currentPrice = 0;

function openUPIModal(plan, price) {
    if (!isLoggedIn) {
        alert("Please create an account or log in first!");
        switchAuthPage();
        return;
    }
    currentPlan = plan;
    currentPrice = price;
    
    const myUPI_ID = "mayankbhatt934@oksbi"; // <--- DO NOT FORGET TO CHANGE THIS!
    
    const name = "SourceHub Premium";
    const upiLink = `upi://pay?pa=${myUPI_ID}&pn=${name}&am=${price}&cu=INR`;
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(upiLink)}`;
    
    document.getElementById('modal-plan-desc').innerText = `Scan to pay ₹${price} for ${plan} Plan`;
    document.getElementById('upi-qr-code').src = qrUrl;
    document.getElementById('upi-mobile-link').href = upiLink;
    document.getElementById('upi-modal-overlay').style.display = 'flex';
}

function closeUPIModal() { 
    document.getElementById('upi-modal-overlay').style.display = 'none'; 
}

async function submitUPIPayment(event) {
    event.preventDefault();
    try {
        const response = await fetch('/submit-upi-payment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan: currentPlan, amount: currentPrice, utr_number: "Manual Verification" })
        });
        const data = await response.json();
        
        if(response.ok) {
            alert(data.message);
            closeUPIModal();
        } else {
            alert("Error: " + data.message);
            if(data.message.includes("login")) switchAuthPage();
        }
    } catch (err) { alert("Server error. Try again."); }
}

// =========================================
// AUTHENTICATION HOOKS
// =========================================
async function handleRegistration(e) {
    e.preventDefault(); 
    const name = document.getElementById('reg-name').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    
    try {
        const res = await fetch('/register', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ name, email, password }) 
        });
        const data = await res.json();
        
        if (data.status === 'success') { 
            alert("Success! You can now log in."); 
            document.getElementById('register-form').reset(); 
            toggleFlipCard(); 
        } else { 
            alert("Error: " + data.message); 
        }
    } catch (err) { alert("Error occurred."); }
}

async function handleLogin(e) {
    e.preventDefault(); 
    const email = document.getElementById('log-email').value;
    const password = document.getElementById('log-password').value;
    
    try {
        const res = await fetch('/login', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ email, password }) 
        });
        const data = await res.json();
        
        if (data.status === 'success') {
            document.getElementById('login-form').reset(); 
            isLoggedIn = true;
            document.getElementById('nav-login').innerText = "Profile"; 
            
            if(data.is_premium) {
                unlockPremiumRoom();
            }
            
            loadProfile();
            switchPage('profile'); 
        } else { 
            alert("Error: " + data.message); 
        }
    } catch (err) { alert("Error occurred."); }
}