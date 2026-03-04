// =========================================
// NAVIGATION & UI LOGIC
// =========================================
function togglePromptView(id, btnElement) {
    const textBlock = document.getElementById(id);
    if (textBlock.style.display === 'none' || textBlock.style.display === '') {
        textBlock.style.display = 'block';
        btnElement.innerText = "Hide";
        btnElement.style.color = "#fff";
        btnElement.style.background = "#b06ab3";
    } else {
        textBlock.style.display = 'none';
        btnElement.innerText = "View";
        btnElement.style.color = "#b06ab3";
        btnElement.style.background = "transparent";
    }
}
function switchPage(pageId) {
    document.querySelectorAll('.page-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.nav-links li').forEach(link => link.classList.remove('active'));
    
    const targetPage = document.getElementById(`page-${pageId}`);
    if(targetPage) {
        targetPage.classList.add('active');
        if(document.getElementById(`nav-${pageId}`)) {
            document.getElementById(`nav-${pageId}`).classList.add('active');
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    if(window.innerWidth <= 768) {
        document.getElementById('nav-menu').classList.remove('show');
    }

    if(pageId === 'premium') {
        loadPremiumCode();
    }
}

function toggleMobileMenu() {
    document.getElementById('nav-menu').classList.toggle('show');
}

function copyMainCode(elementId, btnElement) {
    const code = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(code);
    const originalText = btnElement.innerText;
    btnElement.innerText = "Copied!";
    btnElement.style.background = "#00ff88";
    btnElement.style.color = "#000";
    setTimeout(() => {
        btnElement.innerText = originalText;
        btnElement.style.background = "";
        btnElement.style.color = "";
    }, 2000);
}

function copyPrompt(btn, text) {
    navigator.clipboard.writeText(text);
    const originalText = btn.innerText;
    btn.innerText = "Copied!";
    btn.style.background = "#00ff88";
    btn.style.color = "#000";
    setTimeout(() => {
        btn.innerText = originalText;
        btn.style.background = "";
        btn.style.color = "";
    }, 2000);
}

// =========================================
// AUTHENTICATION & PROFILE LOGIC
// =========================================
let isFlipped = false;
let authMode = 'normal'; 
let isLoggedIn = false;
let isPremiumUser = false;

function switchAuthPage() {
    if (isLoggedIn) {
        switchPage('profile');
    } else {
        switchPage('login');
    }
}

function toggleFlipCard() {
    const inner = document.getElementById('flip-inner-box');
    isFlipped = !isFlipped;
    inner.style.transform = isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)';
}

function setAuthMode(mode) {
    authMode = mode;
    const btnNormal = document.getElementById('btn-normal');
    const btnPremium = document.getElementById('btn-premium');
    const toggleBg = document.querySelector('.toggle-bg');
    const lockOverlay = document.getElementById('premium-lock-overlay');
    const flipContainer = document.getElementById('flip-container');
    const titleSpan = document.getElementById('login-title-span');

    if (mode === 'normal') {
        btnNormal.classList.add('active');
        btnPremium.classList.remove('active');
        toggleBg.style.left = '0';
        lockOverlay.style.display = 'none';
        flipContainer.style.display = 'block';
        titleSpan.innerText = "Account";
        titleSpan.style.color = "#00d2ff";
    } else {
        btnPremium.classList.add('active');
        btnNormal.classList.remove('active');
        toggleBg.style.left = '50%';
        lockOverlay.style.display = 'flex';
        flipContainer.style.display = 'none';
        titleSpan.innerText = "Premium";
        titleSpan.style.color = "#f5af19";
    }
}

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
        
        if (res.ok) {
            alert(data.message);
            toggleFlipCard(); 
        } else {
            alert("Error: " + data.message);
        }
    } catch (err) {
        alert("Server error. Please try again.");
    }
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
        
        if (res.ok) {
            isLoggedIn = true;
            isPremiumUser = data.is_premium;
            document.getElementById('nav-login').innerText = "Dashboard";
            
            await loadUserProfile();
            switchPage('profile');
        } else {
            alert("Error: " + data.message);
        }
    } catch (err) {
        alert("Server error. Please try again.");
    }
}

async function handleLogout() {
    try {
        await fetch('/logout', { method: 'POST' });
        isLoggedIn = false;
        isPremiumUser = false;
        document.getElementById('nav-login').innerText = "Account";
        document.getElementById('login-form').reset();
        switchPage('home');
    } catch (err) {
        alert("Error logging out.");
    }
}

async function loadUserProfile() {
    try {
        const res = await fetch('/api/profile');
        if (res.ok) {
            isLoggedIn = true;
            document.getElementById('nav-login').innerText = "Dashboard";
            
            const user = await res.json();
            document.getElementById('prof-name').value = user.name;
            document.getElementById('prof-email').value = user.email;
            
            if (user.photo) {
                document.getElementById('profile-img').src = user.photo;
            } else {
                document.getElementById('profile-img').src = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=00d2ff&color=fff`;
            }

            const badge = document.getElementById('profile-status-badge');
            const expiryText = document.getElementById('profile-expiry');
            
            if (user.is_premium) {
                badge.className = 'status-badge premium';
                badge.innerText = 'Premium Member ⭐';
                if (user.expiry) {
                    expiryText.style.display = 'block';
                    expiryText.querySelector('span').innerText = user.expiry;
                }
            } else {
                badge.className = 'status-badge basic';
                badge.innerText = 'Basic Account';
                expiryText.style.display = 'none';
            }
        }
    } catch (err) {
        console.log("Not logged in");
    }
}

async function updateProfileName(e) {
    e.preventDefault();
    const newName = document.getElementById('prof-name').value;
    try {
        const res = await fetch('/api/update-profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });
        if (res.ok) {
            alert("Profile updated successfully!");
            loadUserProfile(); 
        }
    } catch (err) { alert("Error updating profile."); }
}

async function uploadPhoto(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onloadend = async function() {
        const base64String = reader.result;
        try {
            const res = await fetch('/api/update-profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ photo: base64String })
            });
            if (res.ok) {
                document.getElementById('profile-img').src = base64String;
                alert("Photo updated!");
            }
        } catch (err) { alert("Failed to upload photo."); }
    }
    reader.readAsDataURL(file);
}

// =========================================
// FORGOT PASSWORD LOGIC
// =========================================
function openResetModal() {
    document.getElementById('reset-modal-overlay').style.display = 'flex';
    document.getElementById('request-code-form').style.display = 'block';
    document.getElementById('verify-code-form').style.display = 'none';
    document.getElementById('reset-email').value = '';
}

function closeResetModal() {
    document.getElementById('reset-modal-overlay').style.display = 'none';
}

async function handleRequestCode(e) {
    e.preventDefault();
    const email = document.getElementById('reset-email').value;
    const btn = e.target.querySelector('button');
    btn.innerText = "Sending...";
    
    try {
        const res = await fetch('/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (res.ok) {
            document.getElementById('request-code-form').style.display = 'none';
            document.getElementById('verify-code-form').style.display = 'block';
        } else {
            alert("Error: " + data.message);
        }
    } catch (err) { alert("Server error."); }
    btn.innerText = "Send Code";
}

async function handleResetPassword(e) {
    e.preventDefault();
    const email = document.getElementById('reset-email').value;
    const code = document.getElementById('reset-code').value;
    const newPassword = document.getElementById('reset-new-password').value;
    
    try {
        const res = await fetch('/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, code, new_password: newPassword })
        });
        const data = await res.json();
        if (res.ok) {
            alert("Password updated successfully! You can now log in.");
            closeResetModal();
        } else {
            alert("Error: " + data.message);
        }
    } catch (err) { alert("Server error."); }
}

// =========================================
// UPI & PREMIUM LOGIC
// =========================================
let selectedPlan = "";

function openUPIModal(planName, price) {
    if (!isLoggedIn) {
        alert("Please create an account or login first to buy Premium!");
        switchAuthPage();
        return;
    }
    
    selectedPlan = planName;
    const upiID = "mayank.code.ai@okaxis"; 
    const name = "Source Code Hub Premium";
    const amount = price;
    const desc = `${planName} Premium Plan`;

    const upiURL = `upi://pay?pa=${upiID}&pn=${encodeURIComponent(name)}&am=${amount}&cu=INR&tn=${encodeURIComponent(desc)}`;
    
    const qrURL = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(upiURL)}`;
    document.getElementById('upi-qr-code').src = qrURL;
    document.getElementById('upi-mobile-link').href = upiURL;
    
    document.getElementById('modal-plan-desc').innerText = `You selected the ${planName} Plan (₹${amount}). Scan the QR code or click the button below to pay.`;
    document.getElementById('upi-modal-overlay').style.display = 'flex';
}

function closeUPIModal() {
    document.getElementById('upi-modal-overlay').style.display = 'none';
}

async function submitUPIPayment(e) {
    e.preventDefault();
    
    const utr = prompt("Please enter the 12-digit UPI Reference Number (UTR) from your payment app:");
    if (!utr || utr.length < 10) {
        alert("Valid UTR number is required to verify your payment.");
        return;
    }

    let amount = 0;
    if (selectedPlan === 'Weekly') amount = 199;
    if (selectedPlan === 'Monthly') amount = 499;
    if (selectedPlan === 'Yearly') amount = 3999;

    try {
        const res = await fetch('/submit-upi-payment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ utr_number: utr, plan: selectedPlan, amount: amount })
        });
        const data = await res.json();
        
        if (res.ok) {
            alert(data.message);
            closeUPIModal();
        } else {
            alert("Error: " + data.message);
        }
    } catch (err) {
        alert("Server error submitting payment.");
    }
}

async function loadPremiumCode() {
    try {
        const res = await fetch('/api/get-premium-code');
        if (res.ok) {
            const data = await res.json();
            const codeBlock = document.getElementById('premium-code-block');
            const unlockBtn = document.getElementById('premium-unlock-btn');
            
            codeBlock.style.filter = 'none';
            codeBlock.style.pointerEvents = 'auto';
            codeBlock.style.opacity = '1';
            codeBlock.style.userSelect = 'auto';
            
            document.getElementById('premium-secret-code').innerText = data.code;
            unlockBtn.style.display = 'none'; 
        }
    } catch (err) {
        console.log("Premium check failed");
    }
}

// =========================================
// DYNAMIC CONTENT LOADER (ADMIN DATA)
// =========================================
async function loadDynamicContent() {
    try {
        const res = await fetch('/api/content');
        if (!res.ok) return;
        const data = await res.json();

        // Inject Free Codes
        const codeContainer = document.getElementById('dynamic-free-codes');
        if (codeContainer) {
            if (data.codes.length === 0) {
                codeContainer.innerHTML = '<p style="color: #888; text-align: center;">No free codes published yet. Check back soon!</p>';
            } else {
                codeContainer.innerHTML = data.codes.map((item, index) => `
                    <div class="code-wrapper" data-aos="fade-up" style="margin-bottom: 30px;">
                        <div class="code-title"><span>0${index + 1}. ${item.title}</span></div>
                        <div class="code-container">
                            <div class="code-header">
                                <div class="dots"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div>
                                <button class="copy-main-btn" onclick="copyMainCode('dynamic-code-${item.id}', this)">Copy Script</button>
                            </div>
                            <pre id="dynamic-code-${item.id}">${item.code}</pre>
                        </div>
                    </div>
                `).join('');
            }
        }

        // Inject AI Prompts
        const promptContainer = document.getElementById('dynamic-prompts');
        if (promptContainer) {
            if (data.prompts.length === 0) {
                promptContainer.innerHTML = '<p style="color: #888; text-align: center;">No AI prompts published yet. Check back soon!</p>';
            } else {
                promptContainer.innerHTML = data.prompts.map((item) => `
                    <div class="prompt-box" style="margin-bottom: 15px; padding: 15px; background: rgba(0,0,0,0.4); border-radius: 8px; border: 1px solid #333;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="prompt-text" style="font-weight: bold; color: #00d2ff;">${item.title}</span>
                            <div>
                                <button class="submit-btn" style="padding: 5px 15px; font-size: 0.8rem; margin-right: 5px; background: transparent; border: 1px solid #b06ab3; color: #b06ab3;" onclick="togglePromptView('prompt-text-${item.id}', this)">View</button>
                                <button class="copy-btn" style="padding: 5px 15px; font-size: 0.8rem;" onclick="copyPrompt(this, \`${item.prompt_text.replace(/`/g, '\\`')}\`)">Copy</button>
                            </div>
                        </div>
                        <div id="prompt-text-${item.id}" style="display: none; margin-top: 15px; padding: 15px; background: rgba(0,0,0,0.6); border-radius: 5px; color: #ccc; font-size: 0.9rem; line-height: 1.5; border-left: 3px solid #b06ab3;">
                            ${item.prompt_text}
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (err) {
        console.error("Error loading dynamic content:", err);
    }
}

// Run startup checks
document.addEventListener("DOMContentLoaded", () => {
    loadUserProfile();
    loadDynamicContent();
});