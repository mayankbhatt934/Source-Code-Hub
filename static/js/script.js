// =========================================
// NAVIGATION & UI LOGIC
// =========================================
function switchPage(pageId) {
    document.querySelectorAll('.page-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.nav-links li').forEach(link => link.classList.remove('active'));
    
    const targetPage = document.getElementById(`page-${pageId}`);
    if(targetPage) {
        targetPage.classList.add('active');
        if(document.getElementById(`nav-${pageId}`)) document.getElementById(`nav-${pageId}`).classList.add('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    if(window.innerWidth <= 768) document.getElementById('nav-menu').classList.remove('show');
}

function toggleMobileMenu() { document.getElementById('nav-menu').classList.toggle('show'); }

function switchCategoryTab(section, category) {
    document.querySelectorAll(`.${section}-tab-content`).forEach(el => el.style.display = 'none');
    document.querySelectorAll(`.${section}-tab-btn`).forEach(el => el.classList.remove('active'));
    document.getElementById(`${section}-${category}-content`).style.display = 'block';
    document.getElementById(`btn-${section}-${category}`).classList.add('active');
}

function copyMainCode(elementId, btnElement) {
    const code = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(code);
    const originalText = btnElement.innerText;
    btnElement.innerText = "Copied!";
    btnElement.style.background = "#00ff88"; btnElement.style.color = "#000";
    setTimeout(() => { btnElement.innerText = originalText; btnElement.style.background = ""; btnElement.style.color = ""; }, 2000);
}

function copyPrompt(btn, text) {
    navigator.clipboard.writeText(text);
    const originalText = btn.innerText;
    btn.innerText = "Copied!"; btn.style.background = "#00ff88"; btn.style.color = "#000";
    setTimeout(() => { btn.innerText = originalText; btn.style.background = ""; btn.style.color = ""; }, 2000);
}

function togglePromptView(id, btnElement) {
    const textBlock = document.getElementById(id);
    if (textBlock.style.display === 'none' || textBlock.style.display === '') {
        textBlock.style.display = 'block';
        btnElement.innerText = "Hide"; btnElement.style.color = "#fff"; btnElement.style.background = "#b06ab3";
    } else {
        textBlock.style.display = 'none';
        btnElement.innerText = "View"; btnElement.style.color = "#b06ab3"; btnElement.style.background = "transparent";
    }
}

// =========================================
// AUTHENTICATION & PROFILE
// =========================================
let isFlipped = false;
let isLoggedIn = false;
let isPremiumUser = false;

function switchAuthPage() { isLoggedIn ? switchPage('profile') : switchPage('login'); }

function toggleFlipCard() {
    isFlipped = !isFlipped;
    document.getElementById('flip-inner-box').style.transform = isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)';
}

function setAuthMode(mode) {
    const btnNormal = document.getElementById('btn-normal');
    const btnPremium = document.getElementById('btn-premium');
    const toggleBg = document.querySelector('.toggle-bg');
    if (mode === 'normal') {
        btnNormal.classList.add('active'); btnPremium.classList.remove('active');
        toggleBg.style.left = '0';
        if(isFlipped) toggleFlipCard();
    } else {
        btnPremium.classList.add('active'); btnNormal.classList.remove('active');
        toggleBg.style.left = '50%';
        if(!isFlipped) toggleFlipCard();
    }
}

async function handleRegistration(e) {
    e.preventDefault();
    try {
        const res = await fetch('/register', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: document.getElementById('reg-name').value, email: document.getElementById('reg-email').value, password: document.getElementById('reg-password').value })
        });
        const data = await res.json();
        if (res.ok) { alert(data.message); setAuthMode('normal'); } else { alert("Error: " + data.message); }
    } catch (err) { alert("Server error."); }
}

async function handleLogin(e) {
    e.preventDefault();
    try {
        const res = await fetch('/login', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: document.getElementById('log-email').value, password: document.getElementById('log-password').value })
        });
        const data = await res.json();
        if (res.ok) {
            isLoggedIn = true; isPremiumUser = data.is_premium;
            document.getElementById('nav-login').innerText = "Dashboard";
            await loadUserProfile();
            loadDynamicContent();
            switchPage('profile');
        } else { alert("Error: " + data.message); }
    } catch (err) { alert("Server error."); }
}

async function handleLogout() {
    await fetch('/logout', { method: 'POST' });
    isLoggedIn = false; isPremiumUser = false;
    document.getElementById('nav-login').innerText = "Account";
    document.getElementById('login-form').reset();
    loadDynamicContent();
    switchPage('home');
}

async function loadUserProfile() {
    try {
        const res = await fetch('/api/profile');
        if (res.ok) {
            isLoggedIn = true; document.getElementById('nav-login').innerText = "Dashboard";
            const user = await res.json();
            isPremiumUser = user.is_premium;
            document.getElementById('prof-name').value = user.name;
            document.getElementById('prof-email').value = user.email;
            document.getElementById('profile-img').src = user.photo ? user.photo : `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=00d2ff&color=fff`;

            const badge = document.getElementById('profile-status-badge');
            const expiryText = document.getElementById('profile-expiry');
            
            if (user.is_premium) {
                badge.className = 'status-badge premium'; badge.innerText = 'Premium Member ⭐';
                if (user.expiry) { expiryText.style.display = 'block'; expiryText.innerHTML = `Expires/Status: <span>${user.expiry}</span>`; }
            } else {
                badge.className = 'status-badge basic'; badge.innerText = 'Basic Account';
                expiryText.style.display = 'none';
            }
        }
    } catch (err) { console.log("Not logged in"); }
}

async function updateProfileName(e) {
    e.preventDefault();
    const res = await fetch('/api/update-profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: document.getElementById('prof-name').value }) });
    if (res.ok) { alert("Profile updated!"); loadUserProfile(); }
}

async function uploadPhoto(e) {
    const file = e.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onloadend = async function() {
        const res = await fetch('/api/update-profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ photo: reader.result }) });
        if (res.ok) { document.getElementById('profile-img').src = reader.result; alert("Photo updated!"); }
    }
    reader.readAsDataURL(file);
}

// =========================================
// UPI & MARKETPLACE LOGIC
// =========================================
let selectedPlan = "";
let selectedAmount = 0;

function openUPIModal(planName, price) {
    if (!isLoggedIn) { alert("Please login or create an account first to make a purchase!"); switchAuthPage(); return; }
    
    selectedPlan = planName;
    selectedAmount = price;
    const upiID = "mayank.code.ai@okaxis"; 
    const desc = `Source Code Hub - ${planName}`;
    const upiURL = `upi://pay?pa=${upiID}&pn=SourceCodeHub&am=${price}&cu=INR&tn=${encodeURIComponent(desc)}`;
    
    document.getElementById('upi-qr-code').src = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(upiURL)}`;
    document.getElementById('upi-mobile-link').href = upiURL;
    document.getElementById('modal-plan-desc').innerText = `You are purchasing: ${planName} (₹${price}). Scan the QR code or click below to pay.`;
    document.getElementById('upi-modal-overlay').style.display = 'flex';
}

function closeUPIModal() { document.getElementById('upi-modal-overlay').style.display = 'none'; }

async function submitUPIPayment(e) {
    e.preventDefault();
    const utr = prompt("Please enter the 12-digit UPI Reference Number (UTR) from your payment app:");
    if (!utr || utr.length < 10) { alert("Valid UTR number is required."); return; }
    const res = await fetch('/submit-upi-payment', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ utr_number: utr, plan: selectedPlan, amount: selectedAmount })
    });
    const data = await res.json();
    if (res.ok) { alert(data.message); closeUPIModal(); } else { alert("Error: " + data.message); }
}

// =========================================
// DYNAMIC HYBRID CONTENT LOADER
// =========================================
async function loadDynamicContent() {
    try {
        const res = await fetch('/api/content');
        if (!res.ok) return;
        const data = await res.json();

        const generateCodeHTML = (codes, isPremiumSection = false) => {
            if (codes.length === 0) return '<p style="text-align: center; color: #888;">No codes available in this category yet.</p>';
            return codes.map((item, index) => {
                const isLocked = isPremiumSection && !isPremiumUser; 
                const blurStyle = isLocked ? 'filter: blur(5px); pointer-events: none; opacity: 0.6; user-select: none;' : '';
                const mainColor = isPremiumSection ? '#f5af19' : '#00d2ff';
                
                let html = `
                    <div class="code-wrapper" data-aos="fade-up" style="margin-bottom: 40px; position: relative;">
                        <div class="code-title" style="color: ${mainColor};"><span>0${index + 1}. ${item.title}</span></div>
                        <div class="code-container" style="${blurStyle}">
                            <div class="code-header">
                                <div class="dots"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div>
                                <button class="copy-main-btn" style="background: ${isPremiumSection ? '#f5af19' : ''}; color: ${isPremiumSection ? '#000' : ''};" onclick="copyMainCode('code-${item.id}', this)">Copy Script</button>
                            </div>
                            <pre id="code-${item.id}">${item.code}</pre>
                        </div>`;

                if (isLocked) {
                    html += `
                        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; z-index: 10; width: 90%;">
                            <div style="font-size: 2.5rem; margin-bottom: 10px;">🔒</div>
                            <h3 style="color: #f5af19; margin-bottom: 15px;">Premium Locked</h3>
                            <button class="submit-btn premium-btn" style="width: auto; padding: 10px 20px; margin-right: 10px;" onclick="openUPIModal('Single Code - ${item.title}', ${item.price})">Buy for ₹${item.price}</button>
                            <button class="submit-btn" style="width: auto; padding: 10px 20px;" onclick="switchPage('pricing')">View Memberships</button>
                        </div>`;
                }
                html += `</div>`;
                return html;
            }).join('');
        };

        const freeSingle = data.codes.filter(c => c.category === 'Single Page' || c.category === 'Single Page Code');
        const freeFull = data.codes.filter(c => c.category === 'Full Website' || c.category === 'Full Website Code');
        if(document.getElementById('free-single-content')) document.getElementById('free-single-content').innerHTML = generateCodeHTML(freeSingle);
        if(document.getElementById('free-full-content')) document.getElementById('free-full-content').innerHTML = generateCodeHTML(freeFull);

        const premSingle = data.premium_codes.filter(c => c.category === 'Single Page' || c.category === 'Single Page Code');
        const premFull = data.premium_codes.filter(c => c.category === 'Full Website' || c.category === 'Full Website Code');
        if(document.getElementById('premium-single-content')) document.getElementById('premium-single-content').innerHTML = generateCodeHTML(premSingle, true);
        if(document.getElementById('premium-full-content')) document.getElementById('premium-full-content').innerHTML = generateCodeHTML(premFull, true);

        const promptContainer = document.getElementById('dynamic-prompts');
        if (promptContainer) {
            promptContainer.innerHTML = data.prompts.length === 0 ? '<p style="text-align: center; color: #888;">No prompts published yet.</p>' : data.prompts.map((item) => `
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
    } catch (err) { console.error("Error loading dynamic content:", err); }
}

function openResetModal() { document.getElementById('reset-modal-overlay').style.display = 'flex'; document.getElementById('request-code-form').style.display = 'block'; document.getElementById('verify-code-form').style.display = 'none'; document.getElementById('reset-email').value = ''; }
function closeResetModal() { document.getElementById('reset-modal-overlay').style.display = 'none'; }
async function handleRequestCode(e) { e.preventDefault(); const email = document.getElementById('reset-email').value; const btn = e.target.querySelector('button'); btn.innerText = "Sending..."; try { const res = await fetch('/forgot-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) }); if (res.ok) { document.getElementById('request-code-form').style.display = 'none'; document.getElementById('verify-code-form').style.display = 'block'; } else { alert("Error."); } } catch (err) { alert("Server error."); } btn.innerText = "Send Code"; }
async function handleResetPassword(e) { e.preventDefault(); try { const res = await fetch('/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: document.getElementById('reset-email').value, code: document.getElementById('reset-code').value, new_password: document.getElementById('reset-new-password').value }) }); const data = await res.json(); if (res.ok) { alert("Password updated!"); closeResetModal(); } else { alert("Error: " + data.message); } } catch (err) { alert("Server error."); } }

document.addEventListener("DOMContentLoaded", () => {
    loadUserProfile().then(() => {
        loadDynamicContent(); 
    });
});