let isFlipped = false; let isLoggedIn = false; let isPremiumUser = false; let isBannedUser = false; let isVerifiedUser = false;
let userBookmarks = [];

let currentEditorTarget = "";
function openEditor(targetId) { currentEditorTarget = targetId; document.getElementById('global-editor-textarea').value = document.getElementById(targetId).value; document.getElementById('editor-modal-overlay').style.display = 'flex'; }
function closeEditor() { document.getElementById('editor-modal-overlay').style.display = 'none'; currentEditorTarget = ""; }
function saveEditor() { if(currentEditorTarget) { document.getElementById(currentEditorTarget).value = document.getElementById('global-editor-textarea').value; } closeEditor(); }

function switchPage(pageId) {
    if (isBannedUser && ['home', 'free', 'premium', 'prompts', 'pricing'].includes(pageId)) { let banner = document.getElementById('ban-banner'); if(banner) banner.style.display = 'block'; return; }
    document.querySelectorAll('.page-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.nav-links li').forEach(link => link.classList.remove('active'));
    const targetPage = document.getElementById(`page-${pageId}`);
    if(targetPage) {
        targetPage.classList.add('active'); if(document.getElementById(`nav-${pageId}`)) document.getElementById(`nav-${pageId}`).classList.add('active'); window.scrollTo({ top: 0, behavior: 'smooth' });
        if(pageId === 'notifications') fetch('/api/notifications/read', {method: 'POST'}).then(() => {
            document.getElementById('notif-badge').style.display = 'none'; lastNotifHash = "";
        });
    }
    if(window.innerWidth <= 900) document.getElementById('nav-menu').classList.remove('show');
}
function toggleMobileMenu() { document.getElementById('nav-menu').classList.toggle('show'); }
function switchCategoryTab(section, category) { document.querySelectorAll(`.${section}-tab-content`).forEach(el => el.style.display = 'none'); document.querySelectorAll(`.${section}-tab-btn`).forEach(el => el.classList.remove('active')); document.getElementById(`${section}-${category}-content`).style.display = 'block'; document.getElementById(`btn-${section}-${category}`).classList.add('active'); }

function switchProfTab(tab) { 
    document.querySelectorAll('.prof-section').forEach(el => el.style.display = 'none'); 
    document.querySelectorAll('.prof-tab-btn').forEach(el => el.classList.remove('active')); 
    document.getElementById(`prof-sec-${tab}`).style.display = 'block'; 
    document.getElementById(`ptab-${tab}`).classList.add('active'); 
    if(tab === 'support') loadMyTickets(); 
    if(tab === 'saved') loadBookmarks(); 
    if(tab === 'creator') loadCreatorStats(); 
    if(tab === 'leaderboard') loadLeaderboard();
}

function copyMainCode(elementId, btnElement, type, codeId) { navigator.clipboard.writeText(document.getElementById(elementId).innerText); const originalText = btnElement.innerText; btnElement.innerText = "Copied!"; btnElement.style.background = "#00ff88"; btnElement.style.color = "#000"; setTimeout(() => { btnElement.innerText = originalText; btnElement.style.background = ""; btnElement.style.color = ""; }, 2000); toggleAction(codeId, type, 'view'); }
function copyPrompt(btn, text) { navigator.clipboard.writeText(text); const originalText = btn.innerText; btn.innerText = "Copied!"; btn.style.background = "#00ff88"; btn.style.color = "#000"; setTimeout(() => { btn.innerText = originalText; btn.style.background = ""; btn.style.color = ""; }, 2000); }

function filterCodes(type) { 
    const query = document.getElementById(`search-${type}`).value.toLowerCase(); 
    ['single', 'full'].forEach(tab => { 
        document.querySelectorAll(`#${type}-${tab}-content .code-wrapper`).forEach(el => { 
            const title = el.querySelector('.code-title span') ? el.querySelector('.code-title span').innerText.toLowerCase() : el.querySelector('h3').innerText.toLowerCase(); 
            const tagsText = el.getAttribute('data-tags') ? el.getAttribute('data-tags').toLowerCase() : "";
            el.style.display = (title.includes(query) || tagsText.includes(query)) ? 'block' : 'none'; 
        }); 
    }); 
}
function filterPrompts() { 
    const query = document.getElementById(`search-prompts`).value.toLowerCase(); 
    document.querySelectorAll('#dynamic-prompts .prompt-box').forEach(el => { 
        const title = el.querySelector('h3').innerText.toLowerCase(); 
        const tagsText = el.getAttribute('data-tags') ? el.getAttribute('data-tags').toLowerCase() : "";
        el.style.display = (title.includes(query) || tagsText.includes(query)) ? 'block' : 'none'; 
    }); 
}

function switchAuthPage() { isLoggedIn ? switchPage('profile') : switchPage('login'); }
function toggleFlipCard() { isFlipped = !isFlipped; document.getElementById('flip-inner-box').style.transform = isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)'; }
function setAuthMode(mode) { const btnNormal = document.getElementById('btn-normal'), btnPremium = document.getElementById('btn-premium'), toggleBg = document.querySelector('.toggle-bg'); if (mode === 'normal') { btnNormal.classList.add('active'); btnPremium.classList.remove('active'); toggleBg.style.left = '0'; if(isFlipped) toggleFlipCard(); } else { btnPremium.classList.add('active'); btnNormal.classList.remove('active'); toggleBg.style.left = '50%'; if(!isFlipped) toggleFlipCard(); } }

async function viewProfile(username) {
    try {
        const res = await fetch(`/api/public-profile/${username}`);
        if(res.ok) {
            const data = await res.json();
            document.getElementById('pub-prof-img').src = data.photo; document.getElementById('pub-prof-name').innerText = data.name;
            document.getElementById('pub-prof-badges').innerHTML = data.badges.map(b => `<span style="padding: 5px 10px; border-radius: 20px; font-size: 0.75rem; border: 1px solid ${b.class==='badge-premium'?'#f5af19':b.class==='badge-owner'?'#ff00ff':b.class==='badge-admin'?'#00d2ff':b.class==='badge-staff'?'#00ff88':b.class==='badge-friend'?'#ff5f56':'#333'}; color: ${b.class==='badge-premium'?'#f5af19':b.class==='badge-owner'?'#ff00ff':b.class==='badge-admin'?'#00d2ff':b.class==='badge-staff'?'#00ff88':b.class==='badge-friend'?'#ff5f56':'#888'}; background: rgba(255,255,255,0.05);">${b.name}</span>`).join('');
            document.getElementById('pub-prof-codes').innerHTML = data.codes.length > 0 ? data.codes.map(c => `<div style="background: rgba(0,0,0,0.5); padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 3px solid ${c.type==='Premium'?'#f5af19':'#00d2ff'};"><span style="color:#fff; font-size:0.9rem;">${c.title}</span> <span style="font-size:0.7rem; color:#888;">(${c.type})</span></div>`).join('') : '<p style="color:#666; font-size:0.8rem;">No codes published yet.</p>';
            document.getElementById('public-prof-modal').style.display = 'flex';
        }
    } catch(e) {}
}

async function handleRegistration(e) { 
    e.preventDefault(); const btn = document.getElementById('btn-send-otp'); btn.innerText = "Creating...";
    try { const res = await fetch('/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: document.getElementById('reg-name').value, username: document.getElementById('reg-username').value, email: document.getElementById('reg-email').value, password: document.getElementById('reg-password').value }) }); const data = await res.json(); if (res.ok) { alert(data.message); document.getElementById('register-form').reset(); setAuthMode('normal'); } else { alert("Error: " + data.message); } } catch (err) { alert("Network error!"); } btn.innerText = "Create Account";
}

async function handleLogin(e) { 
    e.preventDefault(); 
    try { const res = await fetch('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ login_id: document.getElementById('log-id').value, password: document.getElementById('log-password').value }) }); const data = await res.json(); if (res.ok) { isLoggedIn = true; isPremiumUser = data.is_premium; document.getElementById('nav-login').innerText = "Dashboard"; await loadUserProfile(); loadDynamicContent(); switchPage('profile'); } else { alert("Error: " + data.message); } } catch (err) {} 
}

async function handleLogout() { await fetch('/logout', { method: 'POST' }); isLoggedIn = false; isPremiumUser = false; isBannedUser = false; isVerifiedUser = false; document.getElementById('nav-login').innerText = "Account"; document.getElementById('login-form').reset(); document.getElementById('nav-notifications').style.display = 'none'; document.getElementById('btn-staff-panel').style.display = 'none'; const banner = document.getElementById('ban-banner'); if(banner) banner.remove(); ['nav-home', 'nav-free', 'nav-premium', 'nav-prompts', 'nav-pricing'].forEach(id => document.getElementById(id).style.display = 'block'); loadDynamicContent(); switchPage('home'); }

async function sendVerifyOTP() {
    const btn = document.getElementById('btn-send-verify'); btn.innerText = "Sending...";
    try { const res = await fetch('/api/send-verification-otp', { method: 'POST' }); const data = await res.json(); if(res.ok) { document.getElementById('btn-send-verify').style.display = 'none'; document.getElementById('verify-otp-input-box').style.display = 'block'; alert("OTP sent to your email!"); } else { alert("Error: " + data.error); btn.innerText = "Send Verification OTP"; if(data.error && data.error.includes("log in")) { handleLogout(); switchAuthPage(); } } } catch(e) {}
}

async function confirmVerifyOTP() {
    try { const res = await fetch('/api/verify-otp', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({otp: document.getElementById('prof-verify-otp').value}) }); const data = await res.json(); if(res.ok) { alert("Email Verified!"); document.getElementById('verify-email-box').style.display = 'none'; loadUserProfile(); } else { alert("Error: " + (data.error || data.message)); } } catch(e) {}
}

async function fetchMyBookmarks() { if(!isLoggedIn) return; try { const res = await fetch('/api/bookmarks'); if(res.ok) { const data = await res.json(); userBookmarks = data; } } catch(e) {} }
function isBookmarked(type, id) { return userBookmarks.some(b => b.type === type && b.id === id); }

async function toggleBookmark(type, id, btnElement) { 
    if(!isLoggedIn) { alert("Please login to save items!"); switchAuthPage(); return; } 
    try { const res = await fetch('/api/toggle-bookmark', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type, id}) }); const data = await res.json(); if(res.ok) { if(data.action === 'added') { btnElement.classList.add('bookmarked'); btnElement.innerHTML = `🔖 Saved`; userBookmarks.push({type, id}); } else { btnElement.classList.remove('bookmarked'); btnElement.innerHTML = `🔖 Save`; userBookmarks = userBookmarks.filter(b => !(b.type === type && b.id === id)); } if(document.getElementById('my-saved-list')) loadBookmarks(); } else if (data.error) { alert("Error: " + data.error); } } catch(e) {} 
}

async function loadBookmarks() {
    const list = document.getElementById('my-saved-list'); list.innerHTML = '<p style="color:#888;">Loading...</p>'; await fetchMyBookmarks();
    if(userBookmarks.length === 0) { list.innerHTML = '<p style="color:#888; font-size:0.9rem;">No items saved yet.</p>'; return; }
    list.innerHTML = userBookmarks.map(b => `<div style="background: rgba(0,0,0,0.5); border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;"><div><span style="color:#00d2ff; font-size:0.75rem; text-transform:uppercase; font-weight:bold;">${b.type}</span><h4 style="color:#fff; margin:5px 0 0 0;">${b.title}</h4></div><button onclick="switchPage('${b.type==='prem'?'premium':b.type}')" style="background:#333; color:#fff; border:none; padding:8px 15px; border-radius:5px; cursor:pointer;">View</button></div>`).join('');
}

async function loadCreatorStats() {
    const table = document.getElementById('creator-stats-table'); table.innerHTML = '<tbody><tr><td colspan="6" style="text-align:center; color:#888;">Loading stats...</td></tr></tbody>';
    try {
        const res = await fetch('/api/creator/stats'); if(res.ok) { const data = await res.json(); if(data.length === 0) { table.innerHTML = '<tbody><tr><td colspan="6" style="text-align:center; color:#888;">You haven\'t published any content yet.</td></tr></tbody>'; return; } let html = `<thead><tr><th>Title</th><th>Type</th><th>Views</th><th>Likes</th><th>Sales</th><th>Earnings</th></tr></thead><tbody>`; data.forEach(s => { html += `<tr><td>${s.title}</td><td><span class="badge" style="color:${s.type==='Free'?'#00d2ff':'#f5af19'}">${s.type}</span></td><td>${s.views}</td><td>🤍 ${s.likes}</td><td>${s.sales}</td><td style="color:#00ff88; font-weight:bold;">₹${s.earnings}</td></tr>`; }); html += `</tbody>`; table.innerHTML = html; }
    } catch(e) { table.innerHTML = '<tbody><tr><td colspan="6" style="text-align:center; color:#ff5f56;">Error loading stats</td></tr></tbody>'; }
}

async function loadUserProfile() {
    try {
        const res = await fetch('/api/profile'); const user = await res.json();
        if (res.ok) {
            isLoggedIn = true; document.getElementById('nav-login').innerText = "Dashboard"; document.getElementById('nav-notifications').style.display = 'block'; isPremiumUser = user.is_premium; isBannedUser = user.is_banned; isVerifiedUser = user.is_verified;
            document.getElementById('prof-name').value = user.name; document.getElementById('prof-email').value = user.email; document.getElementById('prof-username').value = user.username;
            if(!user.is_verified) { document.getElementById('verify-email-box').style.display = 'block'; } else { document.getElementById('verify-email-box').style.display = 'none'; }
            const defaultAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=00d2ff&color=fff`; let finalAvatar = defaultAvatar; if (user.photo && String(user.photo).trim() !== '' && String(user.photo) !== 'null') { finalAvatar = user.photo; }
            document.getElementById('profile-img').src = finalAvatar;
            if(user.has_staff_access) document.getElementById('btn-staff-panel').style.display = 'block'; else document.getElementById('btn-staff-panel').style.display = 'none';
            if(user.is_premium || user.has_staff_access) { document.getElementById('creator-lock').style.display = 'none'; document.getElementById('creator-unlocked').style.display = 'block'; }
            document.getElementById('cr-earnings').innerText = user.earnings;
            const badgeContainer = document.getElementById('profile-status-badge'); badgeContainer.innerHTML = ''; badgeContainer.style.cssText = 'display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin-bottom: 5px;';
            user.badges.forEach(b => { let color = '#888'; let bg = 'rgba(0,0,0,0.5)'; let border = '#333'; let fontStyle = 'font-weight: normal;'; if(b.class === 'badge-premium') { color = '#f5af19'; border = '#f5af19'; bg = 'rgba(245, 175, 25, 0.1)'; } if(b.class === 'badge-owner') { color = '#ff00ff'; border = '#ff00ff'; bg = 'rgba(255, 0, 255, 0.1)'; fontStyle = 'font-weight: bold; text-shadow: 0 0 10px rgba(255,0,255,0.5);'; } if(b.class === 'badge-admin') { color = '#00d2ff'; border = '#00d2ff'; bg = 'rgba(0, 210, 255, 0.1)'; } if(b.class === 'badge-staff') { color = '#00ff88'; border = '#00ff88'; bg = 'rgba(0, 255, 136, 0.1)'; } if(b.class === 'badge-friend') { color = '#ff5f56'; border = '#ff5f56'; bg = 'rgba(255, 95, 86, 0.1)'; } if(b.class === 'badge-banned') { color = '#fff'; border = '#ff0000'; bg = '#ff0000'; } badgeContainer.innerHTML += `<span style="padding: 5px 15px; border-radius: 20px; font-size: 0.8rem; border: 1px solid ${border}; background: ${bg}; color: ${color}; ${fontStyle}">${b.name}</span>`; });
            const expiryText = document.getElementById('profile-expiry'); if (user.expiry && !user.is_banned) { expiryText.style.display = 'block'; expiryText.innerHTML = `Access: <span>${user.expiry}</span>`; } else { expiryText.style.display = 'none'; }
            if (isBannedUser) { ['nav-home', 'nav-free', 'nav-premium', 'nav-prompts', 'nav-pricing'].forEach(id => document.getElementById(id).style.display = 'none'); let banner = document.getElementById('ban-banner'); if(!banner) { banner = document.createElement('div'); banner.id = 'ban-banner'; banner.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90%; max-width: 350px; background: rgba(20,20,20,0.95); border: 2px solid #ff5f56; color: #fff; text-align: center; padding: 25px; border-radius: 12px; z-index: 999999; box-shadow: 0 10px 50px rgba(0,0,0,0.9); backdrop-filter: blur(5px);'; banner.innerHTML = ' <div style="font-size: 2.5rem; margin-bottom: 10px;">🚫</div><h3 style="color: #ff5f56; margin-bottom: 10px;">Account Restricted</h3><p style="font-size: 0.9rem; color: #ccc; margin-bottom: 20px; line-height: 1.4;">Your access has been limited.</p><button onclick="this.parentElement.style.display=\'none\'" style="background: #ff5f56; color: #fff; border: none; padding: 8px 20px; border-radius: 5px; cursor: font-weight: bold;">I Understand</button>'; document.body.appendChild(banner); } else { banner.style.display = 'block'; } const activePage = document.querySelector('.page-section.active'); if(!activePage || !['page-profile', 'page-notifications'].includes(activePage.id)) switchPage('notifications'); } else { const banner = document.getElementById('ban-banner'); if(banner) banner.remove(); ['nav-home', 'nav-free', 'nav-premium', 'nav-prompts', 'nav-pricing'].forEach(id => document.getElementById(id).style.display = 'block'); }
            await fetchMyBookmarks(); loadMyPurchases(); loadNotifications();
        } else { isLoggedIn = false; }
    } catch (err) { isLoggedIn = false; }
}

async function changePassword(e) { e.preventDefault(); const btn = e.target.querySelector('button'); const origText = btn.innerText; btn.innerText = "Updating..."; try { const res = await fetch('/api/change-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ old_password: document.getElementById('cp-old').value, new_password: document.getElementById('cp-new').value }) }); const data = await res.json(); if(res.ok) { alert(data.message); e.target.reset(); } else { alert("Error: " + data.message); } } catch(err) {} btn.innerText = origText; }

function toggleCreatorFields() { const type = document.getElementById('cr-type').value; const cat = document.getElementById('cr-cat'); const price = document.getElementById('cr-price'); const code = document.getElementById('cr-code'); if(type === 'prompt') { cat.style.display = 'none'; cat.required = false; price.style.display = 'none'; price.required = false; code.placeholder = "Paste your AI Prompt here..."; } else if(type === 'free') { cat.style.display = 'block'; cat.required = true; price.style.display = 'none'; price.required = false; code.placeholder = "Paste your code or Drive link here..."; } else { cat.style.display = 'block'; cat.required = true; price.style.display = 'block'; price.required = true; code.placeholder = "Paste your code or Drive link here..."; } }
async function requestPayout() { const amount = prompt("Enter amount to withdraw (Min ₹100):"); if(!amount) return; const upi = prompt("Enter your UPI ID to receive payment:"); if(!upi) return; try { const res = await fetch('/api/creator/payout', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({amount: parseInt(amount), upi: upi}) }); const data = await res.json(); if(res.ok) { alert("Payout Requested! Admin will verify."); loadUserProfile(); } else { alert("Error: " + data.error); if(data.error && data.error.includes("log in")) { handleLogout(); switchAuthPage(); } } } catch(e) {} }
async function submitSupportTicket(e) { e.preventDefault(); const btn = e.target.querySelector('button'); btn.innerText = "Sending..."; try { const res = await fetch('/api/tickets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ subject: document.getElementById('tick-subject').value, message: document.getElementById('tick-msg').value }) }); const data = await res.json(); if(res.ok) { alert("Ticket opened!"); e.target.reset(); loadMyTickets(); } else { alert("Error: " + data.error); } } catch(e) {} btn.innerText = "Send to Support"; }
async function loadMyTickets() { try { const res = await fetch('/api/tickets'); if(res.ok) { const data = await res.json(); const container = document.getElementById('my-tickets-list'); if(data.length === 0) { container.innerHTML = '<p style="color: #888; font-size: 0.9rem;">No tickets found.</p>'; return; } container.innerHTML = data.map(t => `<div style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; border-left: 3px solid ${t.status==='Closed'?'#00ff88':'#ff5f56'}; margin-bottom: 10px;"><div style="display:flex; justify-content:space-between;"><strong style="color:#fff;">${t.subject}</strong><span style="color:${t.status==='Closed'?'#00ff88':'#ff5f56'}; font-size:0.8rem;">${t.status}</span></div><p style="color:#ccc; font-size:0.9rem; margin:5px 0;">${t.message}</p>${t.admin_reply ? `<div style="background: rgba(0, 210, 255, 0.1); padding: 10px; border-radius: 5px; margin-top: 10px; border-left: 2px solid #00d2ff;"><strong style="color: #00d2ff; font-size: 0.8rem;">Staff Reply:</strong><p style="color: #fff; font-size: 0.9rem; margin: 5px 0 0 0;">${t.admin_reply}</p></div>` : ''}</div>`).join(''); } } catch(e) {} }

async function submitCreatorCode(e) { e.preventDefault(); const btn = e.target.querySelector('button'); btn.innerText = "Submitting..."; try { const res = await fetch('/api/creator/upload', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sub_type: document.getElementById('cr-type').value, title: document.getElementById('cr-title').value, category: document.getElementById('cr-cat').value, tags: document.getElementById('cr-tags').value, price: document.getElementById('cr-price').value, code: document.getElementById('cr-code').value }) }); const data = await res.json(); if(res.ok) { alert("Code submitted for review!"); e.target.reset(); switchProfTab('locker'); } else { alert("Error: " + (data.error || "Upload failed.")); if (data.error && data.error.includes("log in")) { handleLogout(); switchAuthPage(); } } } catch(e) {} btn.innerText = "Submit for Review"; }

// SPRINT 2: ADVANCED REPORT SYSTEM WITH PROOF
function openReportModal(type, id) { 
    if(!isLoggedIn) { alert("Login to report content."); switchAuthPage(); return; } 
    document.getElementById('rep-item-type').value = type; 
    document.getElementById('rep-item-id').value = id; 
    document.getElementById('rep-reason-type').value = "";
    document.getElementById('rep-reason').value = ""; 
    document.getElementById('rep-proof').value = ""; 
    document.getElementById('report-modal-overlay').style.display = 'flex'; 
}

async function submitReport(e) { 
    e.preventDefault(); 
    const btn = e.target.querySelector('button'); btn.innerText = "Submitting..."; 
    const reasonType = document.getElementById('rep-reason-type').value;
    let reasonText = document.getElementById('rep-reason').value;
    let proofText = document.getElementById('rep-proof').value;
    
    if(!reasonType) { alert("Please select a reason."); btn.innerText = "Submit Report"; return; }
    
    const finalReason = reasonText ? `${reasonType} - ${reasonText}` : reasonType;
    
    try { 
        const res = await fetch('/api/report', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({ 
                type: document.getElementById('rep-item-type').value, 
                id: document.getElementById('rep-item-id').value, 
                reason: finalReason,
                proof: proofText
            }) 
        }); 
        if(res.ok) { alert("Report sent to Admins. Thank you for keeping the community safe."); document.getElementById('report-modal-overlay').style.display = 'none'; } 
    } catch(err) {} 
    btn.innerText = "Submit Report"; 
}

let lastNotifHash = "";
async function loadNotifications() { try { const res = await fetch('/api/notifications'); if (res.ok) { const rawText = await res.text(); if (rawText === lastNotifHash) return; lastNotifHash = rawText; const data = JSON.parse(rawText); const unread = data.filter(n => !n.is_read).length; const badge = document.getElementById('notif-badge'); if (unread > 0) { badge.innerText = unread; badge.style.display = 'inline-block'; } else { badge.style.display = 'none'; } const container = document.getElementById('notifications-list'); if (data.length === 0) { container.innerHTML = '<p style="text-align: center; color: #888;">No new alerts.</p>'; return; } container.innerHTML = data.map(n => `<div style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; border-left: 3px solid ${n.title.includes('Banned') || n.title.includes('Suspended') || n.title.includes('Removed') || n.title.includes('Restricted') ? '#ff5f56' : '#00d2ff'}; margin-bottom: 10px;"><div style="display: flex; justify-content: space-between; margin-bottom: 5px;"><strong style="color: #fff;">${n.title}</strong><span style="color: #666; font-size: 0.8rem;">${n.date}</span></div><p style="color: #ccc; font-size: 0.9rem; margin: 0;">${n.message}</p></div>`).join(''); } } catch(e) {} }
async function updateProfileName(e) { e.preventDefault(); try { const res = await fetch('/api/update-profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: document.getElementById('prof-name').value, username: document.getElementById('prof-username').value }) }); const data = await res.json(); if (res.ok) { alert("Profile updated!"); loadUserProfile(); } else { alert("Error: " + (data.error || data.message)); if(data.error && data.error.includes("log in")) { handleLogout(); switchAuthPage(); } } } catch(err) {} }
async function uploadPhoto(e) { const file = e.target.files[0]; if (!file) return; const reader = new FileReader(); reader.onloadend = async function() { const res = await fetch('/api/update-profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ photo: reader.result }) }); if (res.ok) { document.getElementById('profile-img').src = reader.result; alert("Photo updated!"); } }; reader.readAsDataURL(file); }

let selectedPlan = ""; let selectedAmount = 0; let baseAmount = 0; let selectedCodeId = null; let isGifting = false; let appliedPromo = null;

function openUPIModal(planName, price, codeId = null, giftMode = false) { 
    if (!isLoggedIn) { alert("Please login first!"); switchAuthPage(); return; } 
    if (!isVerifiedUser) { alert("⚠️ Please verify your email in the Account Dashboard before purchasing!"); switchPage('profile'); return; }
    selectedPlan = planName; selectedAmount = price; baseAmount = price; selectedCodeId = codeId; isGifting = giftMode; appliedPromo = null;
    document.getElementById('modal-promo').value = ""; document.getElementById('modal-promo').disabled = false;
    
    if(planName.includes("Creator Tip")) { document.getElementById('promo-container').style.display = 'none'; } else { document.getElementById('promo-container').style.display = 'block'; }
    
    updateQRAndDesc();
    const giftContainer = document.getElementById('gift-email-container'); const giftInput = document.getElementById('modal-gift-email'); 
    if(giftMode) { giftContainer.style.display = 'block'; giftInput.required = true; giftInput.value = ''; } else { giftContainer.style.display = 'none'; giftInput.required = false; } 
    document.getElementById('upi-modal-overlay').style.display = 'flex'; 
}

function updateQRAndDesc() {
    const desc = isGifting ? `GIFT - ${selectedPlan}` : `Source Code Hub - ${selectedPlan}`; 
    const upiURL = `upi://pay?pa=mayankbhatt934@oksbi&pn=SourceCodeHub&am=${selectedAmount}&cu=INR&tn=${encodeURIComponent(desc)}`; 
    document.getElementById('upi-qr-code').src = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(upiURL)}`; 
    document.getElementById('upi-mobile-link').href = upiURL; 
    let htmlDesc = isGifting ? `You are <strong style="color:#ff007f;">GIFTING</strong>: ${selectedPlan} (₹${baseAmount}).` : `You are purchasing: ${selectedPlan} (₹${baseAmount}).`;
    if(selectedPlan.includes("Creator Tip")) htmlDesc = `You are sending a <strong>☕ Tip</strong> to the creator: ₹${baseAmount}. (100% goes to them!).`;
    if (appliedPromo) { htmlDesc += `<br><span style="color:#00ff88; font-weight:bold; margin-top:5px; display:block;">🎟️ Promo Applied! New Total: ₹${selectedAmount}</span>`; }
    document.getElementById('modal-plan-desc').innerHTML = htmlDesc;
}

async function applyPromo() {
    const codeInput = document.getElementById('modal-promo'); const code = codeInput.value.trim();
    if(!code) return;
    try {
        const res = await fetch('/api/validate-promo', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ code: code, amount: baseAmount }) });
        const data = await res.json();
        if (res.ok) { selectedAmount = data.new_amount; appliedPromo = code; codeInput.disabled = true; updateQRAndDesc(); } 
        else { alert("Error: " + data.error); }
    } catch(e) {}
}

function closeUPIModal() { document.getElementById('upi-modal-overlay').style.display = 'none'; }

async function submitUPIPayment(e) { 
    e.preventDefault(); let giftEmail = null; 
    if(isGifting) { giftEmail = document.getElementById('modal-gift-email').value; if(!giftEmail) { alert("Enter recipient email!"); return; } } 
    const upiID = document.getElementById('modal-sender-upi').value; if (!upiID || !upiID.includes('@')) { alert("Enter a valid UPI ID"); return; } 
    const btn = e.target.querySelector('button[type="submit"]'); const originalText = btn.innerText; btn.innerText = "Verifying..."; 
    try { 
        const payload = { sender_upi: upiID, plan: selectedPlan, amount: selectedAmount, code_id: selectedCodeId, is_gift: isGifting, gift_email: giftEmail, promo_code: appliedPromo };
        const res = await fetch('/submit-upi-payment', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); 
        const data = await res.json(); 
        if (res.ok) { alert(data.message); closeUPIModal(); e.target.reset(); loadNotifications(); } 
        else { alert("Error: " + (data.error || data.message)); if(data.message && data.message.includes("verify")) { closeUPIModal(); switchPage('profile'); } } 
    } catch(err) {} 
    btn.innerText = originalText; 
}

async function loadMyPurchases() {
    try { const res = await fetch('/api/my-purchases'); if (res.ok) { const data = await res.json(); const container = document.getElementById('my-purchases-list'); if (isBannedUser) { container.innerHTML = '<div style="background: rgba(255, 95, 86, 0.1); border: 1px solid #ff5f56; padding: 15px; border-radius: 8px; text-align: center;"><p style="color: #ff5f56; font-size: 0.95rem; margin: 0; font-weight: bold;">🚫 Locked while restricted.</p></div>'; return; } if (data.is_premium) { container.innerHTML = `<div style="background: rgba(245, 175, 25, 0.1); border: 1px solid #f5af19; padding: 15px; border-radius: 8px; text-align: center;"><h4 style="color: #f5af19; margin-bottom: 5px;">⭐ Premium Active</h4><p style="color: #ccc; font-size: 0.9rem; margin-bottom: 10px;">You have full access to all files in the Premium Room.</p><button class="submit-btn premium-btn" style="width: auto; padding: 8px 20px;" onclick="switchPage('premium')">Go to Premium Room</button></div>`; return; } if (data.codes.length === 0) { container.innerHTML = '<p style="color: #666; font-size: 0.9rem;">No unlocked files.</p>'; return; } container.innerHTML = data.codes.map(item => { if (item.category.includes("Full Website")) { return `<div style="background: rgba(0,0,0,0.5); border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;"><div><h4 style="color: #fff; margin-bottom: 5px;">${item.title}</h4></div><a href="${item.code}" target="_blank" class="submit-btn" style="width: auto; padding: 8px 15px; text-decoration: none;">Download</a></div>`; } else { const safeCode = item.code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); return `<div style="background: rgba(0,0,0,0.5); border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 10px;"><h4 style="color: #fff; margin-bottom: 10px;">${item.title}</h4><div style="background: #111; padding: 10px; border-radius: 5px; position: relative;"><button onclick="copyPrompt(this, \`${item.code.replace(/`/g, '\\`')}\`)" style="position: absolute; top: 10px; right: 10px; background: #333; color: #fff; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; z-index: 10;">Copy</button><pre class="language-javascript" style="margin: 0; max-height: 200px; overflow: hidden;"><code class="language-javascript">${safeCode}</code></pre></div></div>`; } }).join(''); if(window.Prism) Prism.highlightAll(); } } catch (err) {}
}

async function loadLeaderboard() {
    try { 
        const res = await fetch('/api/leaderboard'); 
        if(res.ok) { 
            const data = await res.json(); const container = document.getElementById('leaderboard-list'); 
            if(data.length === 0) { container.innerHTML = '<p style="text-align: center; color: #888;">No creators ranked yet.</p>'; return; } 
            container.innerHTML = data.map((c, i) => `<div style="display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px solid #333; align-items: center;"><div><span style="color: ${i===0?'#f5af19':i===1?'#ccc':i===2?'#cd7f32':'#888'}; font-weight: bold; font-size: 1.2rem; margin-right: 15px;">#${i+1}</span><a class="creator-link" onclick="viewProfile('${c.username}')">${c.name}</a></div><span style="color: #ff5f56; font-weight: bold;">❤️ ${c.score} Score</span></div>`).join(''); 
        } 
    } catch(e) {}
}

// UPDATE: Added 'id' parameter to track views when prompt modal opens
function openPromptModal(title, text, id) { 
    document.getElementById('modal-prompt-title').innerText = title; 
    document.getElementById('modal-prompt-text').innerText = text; 
    currentModalPromptText = text; 
    document.getElementById('prompt-modal-overlay').style.display = 'flex'; 
    if(id) toggleAction(id, 'prompt', 'view'); // Trigger view count
}
function closePromptModal() { document.getElementById('prompt-modal-overlay').style.display = 'none'; }
function copyFromModal(btnElement) { navigator.clipboard.writeText(currentModalPromptText); const originalText = btnElement.innerText; btnElement.innerText = "Copied!"; btnElement.style.background = "#00ff88"; btnElement.style.color = "#000"; setTimeout(() => { btnElement.innerText = originalText; btnElement.style.background = ""; btnElement.style.color = ""; }, 2000); }

function openResetModal() { document.getElementById('reset-modal-overlay').style.display = 'flex'; document.getElementById('request-code-form').style.display = 'block'; document.getElementById('verify-code-form').style.display = 'none'; document.getElementById('reset-email').value = ''; }
function closeResetModal() { document.getElementById('reset-modal-overlay').style.display = 'none'; }
async function handleRequestCode(e) { e.preventDefault(); const email = document.getElementById('reset-email').value; const btn = e.target.querySelector('button'); btn.innerText = "Sending..."; try { const res = await fetch('/forgot-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) }); if (res.ok) { document.getElementById('request-code-form').style.display = 'none'; document.getElementById('verify-code-form').style.display = 'block'; } else { alert("Error."); } } catch (err) {} btn.innerText = "Send Code"; }
async function handleResetPassword(e) { e.preventDefault(); try { const res = await fetch('/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: document.getElementById('reset-email').value, code: document.getElementById('reset-code').value, new_password: document.getElementById('reset-new-password').value }) }); const data = await res.json(); if (res.ok) { alert("Password updated!"); closeResetModal(); } else { alert("Error: " + data.message); } } catch (err) {} }

window.onload = () => { loadUserProfile().then(() => { loadDynamicContent(); loadLeaderboard(); }); };

setInterval(() => { if (isLoggedIn) { loadNotifications(); } }, 5000);

function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (input.type === "password") { input.type = "text"; icon.classList.remove('bx-hide'); icon.classList.add('bx-show'); } 
    else { input.type = "password"; icon.classList.remove('bx-show'); icon.classList.add('bx-hide'); }
}

// ==========================================
// UNIFIED CONTENT RENDERING ENGINE
// ==========================================

let currentGlobalContent = { premium_codes: [] };
let lastContentHash = "";
window.siteContent = { free: [], premium: [], prompts: [] };

// NO MORE ACCORDION AUTO-HIDING
function revealContent(id, type) {
    const overlay = document.getElementById(`overlay-${type}-${id}`);
    const content = document.getElementById(`content-${type}-${id}`);
    const copyBtn = document.getElementById(`copy-${type}-${id}`);
    
    if(overlay) overlay.style.display = 'none';
    if(content) { content.style.filter = 'none'; content.style.userSelect = 'auto'; }
    if(copyBtn) copyBtn.style.display = 'inline-block';
    
    toggleAction(id, type, 'view');
}

async function loadDynamicContent() {
    try {
        let purchasedCodeIds = [];
        if (isLoggedIn && !isPremiumUser) {
            try {
                const pRes = await fetch('/api/my-purchases');
                if (pRes.ok) {
                    const pData = await pRes.json();
                    purchasedCodeIds = pData.codes.map(c => c.id);
                }
            } catch(e) {}
        }

        const res = await fetch('/api/content'); if (!res.ok) return; 
        const rawText = await res.text(); if (rawText === lastContentHash) return; lastContentHash = rawText;
        const data = JSON.parse(rawText); currentGlobalContent = data; 
        
        window.siteContent.free = data.codes;
        window.siteContent.premium = data.premium_codes;
        window.siteContent.prompts = data.prompts;

        const generateCodeHTML = (codes, isPremiumSection = false, typeName) => {
            if (codes.length === 0) return '<p style="text-align: center; color: #888;">No items yet.</p>';
            return codes.map((item, index) => {
                
                const isLocked = isPremiumSection && !isPremiumUser && !purchasedCodeIds.includes(item.id); 
                let mainColor = isPremiumSection ? '#f5af19' : '#00d2ff'; 
                
                const isFullWebsite = item.category && item.category.includes("Full Website");
                const safeCode = item.code ? item.code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") : '';
                
                let tagsHTML = ""; 
                if(item.tags) { 
                    const tagsArray = item.tags.split(',').map(t => t.trim()).filter(t => t); 
                    tagsHTML = tagsArray.map(t => `<span class="badge" style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; color: #aaa; margin-right: 5px;">#${t}</span>`).join(''); 
                }

                const num = (index + 1).toString().padStart(2, '0');

                // ACTION BAR WITH FIXED BOXICONS (bx-chat instead of bx-message-circle-detail)
                const actionBarHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 10px; color: #888; font-size: 1.1rem;">
                    <div style="display: flex; gap: 15px; align-items: center;">
                        <span title="Views" style="display: flex; align-items: center; gap: 5px; color: ${mainColor};"><i class="bx bx-show"></i> <span id="view-${typeName}-${item.id}" style="font-size:0.9rem">${item.views || 0}</span></span>
                        <span title="Like" onclick="toggleAction(${item.id}, '${typeName}', 'like')" style="cursor: pointer; display: flex; align-items: center; gap: 5px; transition: 0.3s;" onmouseover="this.style.color='#00ff88'" onmouseout="this.style.color=''"><i class="bx bx-like"></i> <span id="like-${typeName}-${item.id}" style="font-size:0.9rem">${item.likes || 0}</span></span>
                        <span title="Dislike" onclick="toggleAction(${item.id}, '${typeName}', 'dislike')" style="cursor: pointer; display: flex; align-items: center; gap: 5px; transition: 0.3s;" onmouseover="this.style.color='#ff5f56'" onmouseout="this.style.color=''"><i class="bx bx-dislike"></i> <span id="dislike-${typeName}-${item.id}" style="font-size:0.9rem">${item.dislikes || 0}</span></span>
                        <span title="Comments" onclick="openCommentModal('${typeName}', ${item.id})" style="cursor: pointer; display: flex; align-items: center; gap: 5px; transition: 0.3s;" onmouseover="this.style.color='#00d2ff'" onmouseout="this.style.color=''"><i class="bx bx-chat"></i></span>
                    </div>
                    <div style="display: flex; gap: 15px; align-items: center;">
                        <span title="Share Link" onclick="shareItem('${typeName}', ${item.id})" style="cursor: pointer; transition: 0.3s;" onmouseover="this.style.color='#f5af19'" onmouseout="this.style.color=''"><i class="bx bx-share-alt"></i></span>
                        <span title="Save for Later" onclick="toggleAction(${item.id}, '${typeName}', 'save')" style="cursor: pointer; transition: 0.3s;" onmouseover="this.style.color='#b06ab3'" onmouseout="this.style.color=''"><i class="bx bx-save"></i></span>
                        <span title="Report Content" onclick="openReportModal('${typeName}', ${item.id})" style="cursor: pointer; transition: 0.3s; color: #ff5f56;" onmouseover="this.style.color='#ff0000'" onmouseout="this.style.color='#ff5f56'"><i class="bx bx-flag"></i></span>
                    </div>
                </div>`;

                if (!isPremiumSection && !isFullWebsite) {
                    // FREE CODE MAC OS UI
                    return `
                    <div class="code-wrapper" data-tags="${item.tags}" style="margin-bottom: 30px;" data-aos="fade-up">
                        <h3 style="color: #00d2ff; margin-bottom: 5px;">${num}. ${item.title}</h3>
                        <div style="margin-bottom: 10px;">${tagsHTML}</div>
                        <div style="background: #1e1e2e; border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                            <div style="background: #2a2a3b; padding: 10px 15px; display: flex; justify-content: space-between; align-items: center;">
                                <div style="display: flex; gap: 8px;">
                                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #ff5f56;"></div>
                                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #ffbd2e;"></div>
                                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #27c93f;"></div>
                                </div>
                                <div style="display: flex; gap: 10px; align-items: center;">
                                    <span style="color: #aaa; font-size: 0.85rem; display: flex; align-items: center; margin-right: 10px;">By <b style="color: #fff; margin-left: 4px;">${item.creator}</b></span>
                                    <button id="copy-free-${item.id}" onclick="copyFreeCode(${item.id}, this, 'free');" style="display: none; background: #00d2ff; color: #000; border: none; padding: 5px 12px; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 0.85rem;">Copy Script</button>
                                </div>
                            </div>
                            <div style="position: relative; padding: 20px; background: #1a1a24; font-family: monospace; color: #ddd; min-height: 120px; max-height: 300px; overflow-y: auto;">
                                <div id="overlay-free-${item.id}" style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(26, 26, 36, 0.85); display: flex; justify-content: center; align-items: center; z-index: 5; backdrop-filter: blur(4px);">
                                    <button class="submit-btn" style="width: auto; padding: 10px 25px; font-size: 1.1rem; border-radius: 30px;" onclick="revealContent(${item.id}, 'free')"><i class="bx bx-show" style="margin-right: 5px;"></i> View Code</button>
                                </div>
                                <pre id="content-free-${item.id}" style="margin:0; white-space: pre-wrap; font-size: 0.9rem; filter: blur(5px); user-select: none; transition: 0.3s;">${safeCode}</pre>
                            </div>
                            <div style="background: #11111a; padding: 10px 15px; border-top: 1px solid rgba(255,255,255,0.05);">
                                ${actionBarHTML}
                            </div>
                        </div>
                    </div>`;
                } else if (isPremiumSection && !isFullWebsite) {
                    // PREMIUM CODE MAC OS UI
                    return `
                    <div class="code-wrapper" data-tags="${item.tags}" style="margin-bottom: 30px;" data-aos="fade-up">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 5px;">
                            <h3 style="color: ${mainColor}; margin: 0;">${num}. ${item.title}</h3>
                            <span class="badge" style="background: rgba(245,175,25,0.1); color: #f5af19; border: 1px solid #f5af19; padding: 5px 12px; border-radius: 20px; font-weight: bold;">₹${item.price}</span>
                        </div>
                        <div style="margin-bottom: 10px;">${tagsHTML}</div>
                        
                        <div style="background: #1e1e2e; border-radius: 10px; overflow: hidden; border: 1px solid rgba(245, 175, 25, 0.3); box-shadow: 0 10px 30px rgba(0,0,0,0.5); position: relative;">
                            
                            <div style="background: #2a2a3b; padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(245, 175, 25, 0.1);">
                                <div style="display: flex; gap: 8px;">
                                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #ff5f56;"></div>
                                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #ffbd2e;"></div>
                                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #27c93f;"></div>
                                </div>
                                <div style="display: flex; gap: 10px; align-items: center;">
                                    <span style="color: #aaa; font-size: 0.85rem; display: flex; align-items: center; margin-right: 10px;">By <b style="color: #fff; margin-left: 4px;">${item.creator}</b></span>
                                    <button id="copy-premium-${item.id}" onclick="copyFreeCode(${item.id}, this, 'premium');" style="display: none; background: #f5af19; color: #000; border: none; padding: 5px 12px; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 0.85rem;">Copy Script</button>
                                </div>
                            </div>
                            
                            <div style="position: relative; padding: 20px; background: #1a1a24; font-family: monospace; color: #ddd; min-height: 120px; max-height: 300px; overflow-y: auto;">
                                ${isLocked ? `
                                    <div style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(26, 26, 36, 0.85); display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 10; backdrop-filter: blur(4px);">
                                        <div style="font-size: 2.5rem; margin-bottom: 5px;">🔒</div>
                                        <h3 style="color: #f5af19; margin-bottom: 15px; margin-top: 0;">Premium Locked</h3>
                                        <div style="display: flex; gap: 10px;">
                                            <button class="submit-btn premium-btn" style="width: auto; padding: 8px 20px;" onclick="openUPIModal('Single File - ${item.title.replace(/'/g, "\\'")}', ${item.price}, ${item.id})">Buy ₹${item.price}</button>
                                            <button class="submit-btn" style="width: auto; padding: 8px 15px; background: #333; border: 1px solid #f5af19;" onclick="openUPIModal('Single File - ${item.title.replace(/'/g, "\\'")}', ${item.price}, ${item.id}, true)">🎁 Gift</button>
                                        </div>
                                    </div>
                                ` : `
                                    <div id="overlay-premium-${item.id}" style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(26, 26, 36, 0.85); display: flex; justify-content: center; align-items: center; z-index: 5; backdrop-filter: blur(4px);">
                                        <button class="submit-btn premium-btn" style="width: auto; padding: 10px 25px; font-size: 1.1rem; border-radius: 30px; color: #000;" onclick="revealContent(${item.id}, 'premium')"><i class="bx bx-show" style="margin-right: 5px;"></i> View Code</button>
                                    </div>
                                `}
                                <pre id="content-premium-${item.id}" style="margin:0; white-space: pre-wrap; font-size: 0.9rem; filter: ${isLocked ? 'blur(5px)' : 'blur(5px)'}; user-select: ${isLocked ? 'none' : 'none'}; transition: 0.3s;">${isLocked ? '// Premium Snippet\nfunction executeSuperCode() {\n  return "Hidden Magic";\n}\n...' : safeCode}</pre>
                            </div>
                            <div style="background: #11111a; padding: 10px 15px; border-top: 1px solid rgba(255,255,255,0.05);">
                                ${actionBarHTML}
                            </div>
                        </div>
                    </div>`;
                } else {
                    // FULL WEBSITE HTML (ZIP FOLDERS)
                    const blurStyleLocal = isLocked ? 'filter: blur(5px); pointer-events: none; opacity: 0.6; user-select: none;' : '';
                    return `
                    <div class="code-wrapper" data-tags="${item.tags}" data-aos="fade-up" style="margin-bottom: 20px;">
                        <div class="code-title" style="color: ${mainColor}; margin-bottom: 5px;"><span>${num}. ${item.title}</span></div>
                        <div style="margin-bottom: 15px;">${tagsHTML}</div>
                        <div class="code-container" style="position: relative; padding: 40px; text-align: center; background: rgba(0,0,0,0.4); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                            <div style="${blurStyleLocal}">
                                <div style="font-size: 3rem; margin-bottom: 15px;">📁</div>
                                <h3 style="color: #fff; margin-bottom: 20px;">Full Website Files</h3>
                                <p style="font-size: 0.85rem; color: #aaa; margin-bottom: 15px;">Published by: <span style="color: #fff;">${item.creator}</span></p>
                                <a href="${isLocked ? '#' : item.code}" target="${isLocked ? '' : '_blank'}" class="submit-btn" style="text-decoration: none; display: inline-block; width: auto; background: ${mainColor}; color: #000;" onclick="toggleAction(${item.id}, '${typeName}', 'view')">Download Files</a>
                                <div style="margin-top: 15px;">
                                    ${actionBarHTML}
                                </div>
                            </div>
                            ${isLocked ? `<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; z-index: 10; width: 90%;"><div style="font-size: 2.5rem; margin-bottom: 10px;">🔒</div><h3 style="color: #f5af19; margin-bottom: 15px;">Premium Locked</h3><button class="submit-btn premium-btn" style="width: auto; padding: 10px 20px;" onclick="openUPIModal('Full Site - ${item.title.replace(/'/g, "\\'")}', ${item.price}, ${item.id})">Buy ₹${item.price}</button></div>` : ''}
                        </div>
                    </div>`;
                }
            }).join('');
        };

        const freeSingle = data.codes.filter(c => c.category === 'Single Page' || c.category === 'Single Page Code'); const freeFull = data.codes.filter(c => c.category.includes('Full Website'));
        if(document.getElementById('free-single-content')) document.getElementById('free-single-content').innerHTML = generateCodeHTML(freeSingle, false, 'free');
        if(document.getElementById('free-full-content')) document.getElementById('free-full-content').innerHTML = generateCodeHTML(freeFull, false, 'free');
        
        const premSingle = data.premium_codes.filter(c => c.category === 'Single Page' || c.category === 'Single Page Code'); const premFull = data.premium_codes.filter(c => c.category.includes('Full Website'));
        if(document.getElementById('prem-single-content')) document.getElementById('prem-single-content').innerHTML = generateCodeHTML(premSingle, true, 'premium');
        if(document.getElementById('prem-full-content')) document.getElementById('prem-full-content').innerHTML = generateCodeHTML(premFull, true, 'premium');
        
        // REDESIGNED AI PROMPTS
        const promptContainer = document.getElementById('dynamic-prompts');
        if (promptContainer) { 
            promptContainer.innerHTML = data.prompts.length === 0 ? '<p style="text-align: center; color: #888;">No prompts published yet.</p>' : data.prompts.map((item) => {
                let tagsHTML = ""; 
                if(item.tags) { 
                    const tagsArray = item.tags.split(',').map(t => t.trim()).filter(t => t); 
                    tagsHTML = tagsArray.map(t => `<span class="badge" style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; color: #aaa; margin-right: 5px;">#${t}</span>`).join(''); 
                }
                
                const actionBarHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 10px; color: #888; font-size: 1.1rem;">
                    <div style="display: flex; gap: 15px; align-items: center;">
                        <span title="Views" style="display: flex; align-items: center; gap: 5px; color: #b06ab3;"><i class="bx bx-show"></i> <span id="view-prompt-${item.id}" style="font-size:0.9rem">${item.views || 0}</span></span>
                        <span title="Like" onclick="toggleAction(${item.id}, 'prompt', 'like')" style="cursor: pointer; display: flex; align-items: center; gap: 5px; transition: 0.3s;" onmouseover="this.style.color='#00ff88'" onmouseout="this.style.color=''"><i class="bx bx-like"></i> <span id="like-prompt-${item.id}" style="font-size:0.9rem">${item.likes || 0}</span></span>
                        <span title="Dislike" onclick="toggleAction(${item.id}, 'prompt', 'dislike')" style="cursor: pointer; display: flex; align-items: center; gap: 5px; transition: 0.3s;" onmouseover="this.style.color='#ff5f56'" onmouseout="this.style.color=''"><i class="bx bx-dislike"></i> <span id="dislike-prompt-${item.id}" style="font-size:0.9rem">${item.dislikes || 0}</span></span>
                        <span title="Comments" onclick="openCommentModal('prompt', ${item.id})" style="cursor: pointer; display: flex; align-items: center; gap: 5px; transition: 0.3s;" onmouseover="this.style.color='#00d2ff'" onmouseout="this.style.color=''"><i class="bx bx-chat"></i></span>
                    </div>
                    <div style="display: flex; gap: 15px; align-items: center;">
                        <span title="Share Link" onclick="shareItem('prompt', ${item.id})" style="cursor: pointer; transition: 0.3s;" onmouseover="this.style.color='#f5af19'" onmouseout="this.style.color=''"><i class="bx bx-share-alt"></i></span>
                        <span title="Save for Later" onclick="toggleAction(${item.id}, 'prompt', 'save')" style="cursor: pointer; transition: 0.3s;" onmouseover="this.style.color='#b06ab3'" onmouseout="this.style.color=''"><i class="bx bx-save"></i></span>
                        <span title="Report Content" onclick="openReportModal('prompt', ${item.id})" style="cursor: pointer; transition: 0.3s; color: #ff5f56;" onmouseover="this.style.color='#ff0000'" onmouseout="this.style.color='#ff5f56'"><i class="bx bx-flag"></i></span>
                    </div>
                </div>`;

                return `<div class="prompt-box" data-tags="${item.tags}" data-aos="fade-up" style="background: #1e1e2e; padding: 25px; border-radius: 12px; border: 1px solid rgba(176, 106, 179, 0.3); border-top: 3px solid #b06ab3; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); display: flex; flex-direction: column; gap: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <h3 style="margin: 0; color: #b06ab3; font-size: 1.4rem;">${item.title}</h3>
                        <button class="submit-btn" style="background: transparent; border: 1px solid #b06ab3; color: #b06ab3; padding: 8px 20px; border-radius: 30px; font-weight: bold; cursor: pointer; transition: 0.3s; width: auto;" onmouseover="this.style.background='#b06ab3'; this.style.color='#fff';" onmouseout="this.style.background='transparent'; this.style.color='#b06ab3';" onclick="openPromptModal(\`${item.title.replace(/`/g, '\\`')}\`, \`${item.prompt_text.replace(/`/g, '\\`')}\`, ${item.id})"><i class="bx bx-show" style="margin-right: 5px;"></i> View Prompt</button>
                    </div>
                    <div>${tagsHTML}</div>
                    <div style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 15px; margin-top: 10px;">
                        ${actionBarHTML}
                    </div>
                </div>`;
            }).join(''); 
        }
        if(window.Prism) Prism.highlightAll();
    } catch (err) { console.error("Error loading content:", err); }
}

async function toggleAction(id, type, action) {
    try {
        const res = await fetch('/api/interact', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id, type, action})
        });
        const data = await res.json();
        
        if (res.status === 401) { 
            alert(data.error || "Please log in to use this feature!"); 
            switchAuthPage();
            return; 
        }
        if (!res.ok) return;

        if (action === 'like' || action === 'dislike') {
            const likeEl = document.getElementById(`like-${type}-${id}`);
            const dislikeEl = document.getElementById(`dislike-${type}-${id}`);
            if(likeEl) likeEl.innerText = data.likes;
            if(dislikeEl) dislikeEl.innerText = data.dislikes;
        }
        if (action === 'view') {
            const viewEl = document.getElementById(`view-${type}-${id}`);
            if(viewEl) viewEl.innerText = data.count;
        }
        if (action === 'save') {
             alert(data.message);
             loadBookmarks();
        }
        
    } catch(e) { console.error("Action failed", e); }
}

async function openCommentModal(type, id) {
    document.getElementById('com-item-type').value = type; document.getElementById('com-item-id').value = id; document.getElementById('comment-modal-overlay').style.display = 'flex';
    const listContainer = document.getElementById('comment-list-container'); listContainer.innerHTML = '<p style="color:#888;">Loading...</p>';
    try {
        const res = await fetch(`/api/comments?type=${type}&id=${id}`);
        if(res.ok) { 
            const data = await res.json(); 
            if(data.length === 0) listContainer.innerHTML = '<p style="color:#888; font-size:0.9rem;">No comments yet. Start the discussion!</p>'; 
            else listContainer.innerHTML = data.map(c => `<div style="margin-bottom:10px; padding:10px; background:rgba(0,255,136,0.05); border-left: 2px solid #00ff88; border-radius:5px;"><strong style="color:#fff;">@${c.user}</strong> <span style="color:#888; font-size:0.75rem; float:right;">${c.date}</span><p style="margin:5px 0 0 0; color:#ccc; font-size:0.9rem;">${c.text}</p></div>`).join(''); 
        }
    } catch(e) {}
}

async function submitComment(e) {
    e.preventDefault(); 
    if (!isLoggedIn) { alert("Please log in to comment!"); switchAuthPage(); return; }
    if (!isVerifiedUser) { alert("⚠️ Please verify your email in the Account Dashboard before commenting!"); document.getElementById('comment-modal-overlay').style.display='none'; switchPage('profile'); return; }
    
    const type = document.getElementById('com-item-type').value; const id = document.getElementById('com-item-id').value; const text = document.getElementById('com-text').value;
    try { 
        const res = await fetch('/api/comments', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type, id, text}) }); 
        const data = await res.json();
        if(res.ok) { document.getElementById('com-text').value = ''; openCommentModal(type, id); } 
        else { alert("Error: " + (data.error || "Failed.")); if(data.error && data.error.includes("verify")) { document.getElementById('comment-modal-overlay').style.display='none'; switchPage('profile'); } }
    } catch(e) {}
}

function shareItem(type, id) {
    const url = `${window.location.origin}/code/${type}/${id}`; 
    navigator.clipboard.writeText(url).then(() => alert("🔗 Link copied to clipboard!"));
}