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
    navigator.clipboard.writeText(document.getElementById(elementId).innerText);
    const originalText = btnElement.innerText;
    btnElement.innerText = "Copied!"; btnElement.style.background = "#00ff88"; btnElement.style.color = "#000";
    setTimeout(() => { btnElement.innerText = originalText; btnElement.style.background = ""; btnElement.style.color = ""; }, 2000);
}
function copyPrompt(btn, text) {
    navigator.clipboard.writeText(text); const originalText = btn.innerText;
    btn.innerText = "Copied!"; btn.style.background = "#00ff88"; btn.style.color = "#000";
    setTimeout(() => { btn.innerText = originalText; btn.style.background = ""; btn.style.color = ""; }, 2000);
}

let isFlipped = false; let isLoggedIn = false; let isPremiumUser = false;
function switchAuthPage() { isLoggedIn ? switchPage('profile') : switchPage('login'); }
function toggleFlipCard() { isFlipped = !isFlipped; document.getElementById('flip-inner-box').style.transform = isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)'; }
function setAuthMode(mode) {
    const btnNormal = document.getElementById('btn-normal'), btnPremium = document.getElementById('btn-premium'), toggleBg = document.querySelector('.toggle-bg');
    if (mode === 'normal') { btnNormal.classList.add('active'); btnPremium.classList.remove('active'); toggleBg.style.left = '0'; if(isFlipped) toggleFlipCard(); } 
    else { btnPremium.classList.add('active'); btnNormal.classList.remove('active'); toggleBg.style.left = '50%'; if(!isFlipped) toggleFlipCard(); }
}

async function handleRegistration(e) { e.preventDefault(); try { const res = await fetch('/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: document.getElementById('reg-name').value, email: document.getElementById('reg-email').value, password: document.getElementById('reg-password').value }) }); const data = await res.json(); if (res.ok) { alert(data.message); setAuthMode('normal'); } else { alert("Error: " + data.message); } } catch (err) { alert("Server error."); } }

async function handleLogin(e) { 
    e.preventDefault(); 
    try { 
        const res = await fetch('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: document.getElementById('log-email').value, password: document.getElementById('log-password').value }) }); 
        const data = await res.json(); 
        
        if (res.ok) { 
            isLoggedIn = true; isPremiumUser = data.is_premium; document.getElementById('nav-login').innerText = "Dashboard"; await loadUserProfile(); loadDynamicContent(); switchPage('profile'); 
        } else { 
            // NEW: Trigger the giant lockdown screen if the server says 403 (Banned)
            if (res.status === 403) {
                document.getElementById('banned-screen-overlay').style.display = 'flex';
            } else {
                alert("Error: " + data.message); 
            }
        } 
    } catch (err) { alert("Server error."); } 
}

async function handleLogout() { await fetch('/logout', { method: 'POST' }); isLoggedIn = false; isPremiumUser = false; document.getElementById('nav-login').innerText = "Account"; document.getElementById('login-form').reset(); loadDynamicContent(); switchPage('home'); }

async function loadUserProfile() {
    try {
        const res = await fetch('/api/profile');
        
        // NEW: If they refresh the page while banned, instantly lock them out!
        if (res.status === 403) {
            document.getElementById('banned-screen-overlay').style.display = 'flex';
            await fetch('/logout', { method: 'POST' }); // Silently wipe their session
            return;
        }

        if (res.ok) {
            isLoggedIn = true; document.getElementById('nav-login').innerText = "Dashboard";
            const user = await res.json(); isPremiumUser = user.is_premium;
            document.getElementById('prof-name').value = user.name; document.getElementById('prof-email').value = user.email;
            document.getElementById('profile-img').src = user.photo ? user.photo : `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=00d2ff&color=fff`;
            const badge = document.getElementById('profile-status-badge'), expiryText = document.getElementById('profile-expiry');
            if (user.is_premium) { badge.className = 'status-badge premium'; badge.innerText = 'Premium Member ⭐'; if (user.expiry) { expiryText.style.display = 'block'; expiryText.innerHTML = `Expires/Status: <span>${user.expiry}</span>`; } } 
            else { badge.className = 'status-badge basic'; badge.innerText = 'Basic Account'; expiryText.style.display = 'none'; }
            loadMyPurchases();
        }
    } catch (err) { console.log("Not logged in"); }
}

async function updateProfileName(e) { e.preventDefault(); const res = await fetch('/api/update-profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: document.getElementById('prof-name').value }) }); if (res.ok) { alert("Profile updated!"); loadUserProfile(); } }
async function uploadPhoto(e) { const file = e.target.files[0]; if (!file) return; const reader = new FileReader(); reader.onloadend = async function() { const res = await fetch('/api/update-profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ photo: reader.result }) }); if (res.ok) { document.getElementById('profile-img').src = reader.result; alert("Photo updated!"); } }; reader.readAsDataURL(file); }

let selectedPlan = ""; let selectedAmount = 0; let selectedCodeId = null; let isGifting = false;
function openUPIModal(planName, price, codeId = null, giftMode = false) {
    if (!isLoggedIn) { alert("Please login or create an account first!"); switchAuthPage(); return; }
    selectedPlan = planName; selectedAmount = price; selectedCodeId = codeId; isGifting = giftMode;
    const desc = giftMode ? `GIFT - ${planName}` : `Source Code Hub - ${planName}`;
    const upiURL = `upi://pay?pa=mayank.code.ai@okaxis&pn=SourceCodeHub&am=${price}&cu=INR&tn=${encodeURIComponent(desc)}`;
    document.getElementById('upi-qr-code').src = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(upiURL)}`;
    document.getElementById('upi-mobile-link').href = upiURL;
    document.getElementById('modal-plan-desc').innerHTML = giftMode ? `You are <strong style="color:#ff007f;">GIFTING</strong>: ${planName} (₹${price}).` : `You are purchasing: ${planName} (₹${price}).`;
    document.getElementById('modal-sender-upi').value = '';
    const giftContainer = document.getElementById('gift-email-container');
    const giftInput = document.getElementById('modal-gift-email');
    if(giftMode) { giftContainer.style.display = 'block'; giftInput.required = true; giftInput.value = ''; } 
    else { giftContainer.style.display = 'none'; giftInput.required = false; }
    document.getElementById('upi-modal-overlay').style.display = 'flex';
}
function closeUPIModal() { document.getElementById('upi-modal-overlay').style.display = 'none'; }

async function submitUPIPayment(e) {
    e.preventDefault();
    let giftEmail = null;
    if(isGifting) { giftEmail = document.getElementById('modal-gift-email').value; if(!giftEmail) { alert("Please enter the recipient's email address!"); return; } }
    const upiID = document.getElementById('modal-sender-upi').value;
    if (!upiID || !upiID.includes('@')) { alert("Please enter a valid UPI ID containing an '@' symbol."); return; }
    const btn = e.target.querySelector('button[type="submit"]'); const originalText = btn.innerText; btn.innerText = "Verifying...";
    try {
        const res = await fetch('/submit-upi-payment', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender_upi: upiID, plan: selectedPlan, amount: selectedAmount, code_id: selectedCodeId, is_gift: isGifting, gift_email: giftEmail })
        });
        const data = await res.json();
        if (res.ok) { alert(data.message); closeUPIModal(); e.target.reset(); } else { alert("Error: " + data.message); }
    } catch(err) { alert("Server error processing payment."); } btn.innerText = originalText;
}

async function loadMyPurchases() {
    try {
        const res = await fetch('/api/my-purchases');
        if (res.ok) {
            const data = await res.json();
            const container = document.getElementById('my-purchases-list');
            if (data.is_premium) { container.innerHTML = `<div style="background: rgba(245, 175, 25, 0.1); border: 1px solid #f5af19; padding: 15px; border-radius: 8px; text-align: center;"><h4 style="color: #f5af19; margin-bottom: 5px;">⭐ Premium Active</h4><p style="color: #ccc; font-size: 0.9rem; margin-bottom: 10px;">You have full access to all files in the Premium Room.</p><button class="submit-btn premium-btn" style="width: auto; padding: 8px 20px;" onclick="switchPage('premium')">Go to Premium Room</button></div>`; return; }
            if (data.codes.length === 0) { container.innerHTML = '<p style="color: #666; font-size: 0.9rem;">You haven\'t unlocked any individual files yet.</p>'; return; }
            container.innerHTML = data.codes.map(item => {
                if (item.category.includes("Full Website")) { return `<div style="background: rgba(0,0,0,0.5); border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;"><div><h4 style="color: #fff; margin-bottom: 5px;">${item.title}</h4><span style="font-size: 0.8rem; color: #888;">Full Website Source Files</span></div><a href="${item.code}" target="_blank" class="submit-btn" style="width: auto; padding: 8px 15px; text-decoration: none;">Download</a></div>`; } 
                else { return `<div style="background: rgba(0,0,0,0.5); border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 10px;"><h4 style="color: #fff; margin-bottom: 10px;">${item.title}</h4><div style="background: #111; padding: 10px; border-radius: 5px; position: relative;"><button onclick="copyPrompt(this, \`${item.code.replace(/`/g, '\\`')}\`)" style="position: absolute; top: 10px; right: 10px; background: #333; color: #fff; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">Copy</button><pre style="color: #00ff88; font-size: 0.85rem; margin: 0; max-height: 100px; overflow: hidden; font-family: monospace;">${item.code}</pre></div></div>`; }
            }).join('');
        }
    } catch (err) { console.log("Failed to load purchases"); }
}

async function loadDynamicContent() {
    try {
        const res = await fetch('/api/content'); if (!res.ok) return; const data = await res.json();
        const generateCodeHTML = (codes, isPremiumSection = false) => {
            if (codes.length === 0) return '<p style="text-align: center; color: #888;">No items available in this category yet.</p>';
            return codes.map((item, index) => {
                const isLocked = isPremiumSection && !isPremiumUser; 
                const blurStyle = isLocked ? 'filter: blur(5px); pointer-events: none; opacity: 0.6; user-select: none;' : '';
                const mainColor = isPremiumSection ? '#f5af19' : '#00d2ff';
                const isFullWebsite = item.category.includes("Full Website");
                
                let html = `<div class="code-wrapper" style="margin-bottom: 40px; position: relative;"><div class="code-title" style="color: ${mainColor};"><span>0${index + 1}. ${item.title}</span></div>`;
                if (isFullWebsite) { html += `<div class="code-container" style="${blurStyle} padding: 40px; text-align: center; background: rgba(0,0,0,0.4);"><div style="font-size: 3rem; margin-bottom: 15px;">📁</div><h3 style="color: #fff; margin-bottom: 20px;">Full Website Source Files</h3><a href="${isLocked ? '#' : item.code}" target="${isLocked ? '' : '_blank'}" class="submit-btn" style="text-decoration: none; display: inline-block; width: auto; background: ${mainColor}; color: #000;">Download Files</a></div>`; } 
                else { html += `<div class="code-container" style="${blurStyle}"><div class="code-header"><div class="dots"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div><button class="copy-main-btn" style="background: ${isPremiumSection ? '#f5af19' : ''}; color: ${isPremiumSection ? '#000' : ''};" onclick="copyMainCode('code-${item.id}', this)">Copy Script</button></div><pre id="code-${item.id}">${item.code}</pre></div>`; }

                if (isLocked) {
                    html += `<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; z-index: 10; width: 90%;">
                                <div style="font-size: 2.5rem; margin-bottom: 10px;">🔒</div><h3 style="color: #f5af19; margin-bottom: 15px;">Premium Locked</h3>
                                <div style="display: flex; justify-content: center; gap: 10px;">
                                    <button class="submit-btn premium-btn" style="width: auto; padding: 10px 20px;" onclick="openUPIModal('Single File - ${item.title}', ${item.price}, ${item.id})">Buy for ₹${item.price}</button>
                                    <button class="submit-btn" style="width: auto; padding: 10px 15px; background: #333; border: 1px solid #f5af19;" onclick="openUPIModal('Single File - ${item.title}', ${item.price}, ${item.id}, true)" title="Gift this code">🎁</button>
                                    <button class="submit-btn" style="width: auto; padding: 10px 20px;" onclick="switchPage('pricing')">View Memberships</button>
                                </div>
                            </div>`;
                }
                html += `</div>`; return html;
            }).join('');
        };
        const freeSingle = data.codes.filter(c => c.category === 'Single Page' || c.category === 'Single Page Code'); const freeFull = data.codes.filter(c => c.category.includes('Full Website'));
        if(document.getElementById('free-single-content')) document.getElementById('free-single-content').innerHTML = generateCodeHTML(freeSingle);
        if(document.getElementById('free-full-content')) document.getElementById('free-full-content').innerHTML = generateCodeHTML(freeFull);
        const premSingle = data.premium_codes.filter(c => c.category === 'Single Page' || c.category === 'Single Page Code'); const premFull = data.premium_codes.filter(c => c.category.includes('Full Website'));
        if(document.getElementById('prem-single-content')) document.getElementById('prem-single-content').innerHTML = generateCodeHTML(premSingle, true);
        if(document.getElementById('prem-full-content')) document.getElementById('prem-full-content').innerHTML = generateCodeHTML(premFull, true);
        
        const promptContainer = document.getElementById('dynamic-prompts');
        if (promptContainer) {
            promptContainer.innerHTML = data.prompts.length === 0 ? '<p style="text-align: center; color: #888;">No prompts published yet.</p>' : data.prompts.map((item) => `
                <div class="prompt-box" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 15px; background: rgba(0,0,0,0.4); border-radius: 8px; border: 1px solid #333;"><span class="prompt-text" style="font-weight: bold; color: #00d2ff;">${item.title}</span><div style="display: flex; gap: 10px;"><button class="submit-btn" style="padding: 5px 15px; font-size: 0.8rem; background: transparent; border: 1px solid #b06ab3; color: #b06ab3;" onclick="openPromptModal(\`${item.title.replace(/`/g, '\\`')}\`, \`${item.prompt_text.replace(/`/g, '\\`')}\`)">View</button><button class="copy-btn" style="padding: 5px 15px; font-size: 0.8rem;" onclick="copyPrompt(this, \`${item.prompt_text.replace(/`/g, '\\`')}\`)">Copy</button></div></div>
            `).join('');
        }
    } catch (err) { console.error("Error loading dynamic content:", err); }
}

let currentModalPromptText = ""; 
function openPromptModal(title, text) { document.getElementById('modal-prompt-title').innerText = title; document.getElementById('modal-prompt-text').innerText = text; currentModalPromptText = text; document.getElementById('prompt-modal-overlay').style.display = 'flex'; }
function closePromptModal() { document.getElementById('prompt-modal-overlay').style.display = 'none'; }
function copyFromModal(btnElement) { navigator.clipboard.writeText(currentModalPromptText); const originalText = btnElement.innerText; btnElement.innerText = "Copied!"; btnElement.style.background = "#00ff88"; btnElement.style.color = "#000"; setTimeout(() => { btnElement.innerText = originalText; btnElement.style.background = ""; btnElement.style.color = ""; }, 2000); }
function openResetModal() { document.getElementById('reset-modal-overlay').style.display = 'flex'; document.getElementById('request-code-form').style.display = 'block'; document.getElementById('verify-code-form').style.display = 'none'; document.getElementById('reset-email').value = ''; }
function closeResetModal() { document.getElementById('reset-modal-overlay').style.display = 'none'; }
async function handleRequestCode(e) { e.preventDefault(); const email = document.getElementById('reset-email').value; const btn = e.target.querySelector('button'); btn.innerText = "Sending..."; try { const res = await fetch('/forgot-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) }); if (res.ok) { document.getElementById('request-code-form').style.display = 'none'; document.getElementById('verify-code-form').style.display = 'block'; } else { alert("Error."); } } catch (err) { alert("Server error."); } btn.innerText = "Send Code"; }
async function handleResetPassword(e) { e.preventDefault(); try { const res = await fetch('/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: document.getElementById('reset-email').value, code: document.getElementById('reset-code').value, new_password: document.getElementById('reset-new-password').value }) }); const data = await res.json(); if (res.ok) { alert("Password updated!"); closeResetModal(); } else { alert("Error: " + data.message); } } catch (err) { alert("Server error."); } }

document.addEventListener("DOMContentLoaded", () => { loadUserProfile().then(() => { loadDynamicContent(); }); });