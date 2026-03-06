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
    if(window.innerWidth <= 768) document.getElementById('nav-menu').classList.remove('show');
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

function copyMainCode(elementId, btnElement, type, codeId) { navigator.clipboard.writeText(document.getElementById(elementId).innerText); const originalText = btnElement.innerText; btnElement.innerText = "Copied!"; btnElement.style.background = "#00ff88"; btnElement.style.color = "#000"; setTimeout(() => { btnElement.innerText = originalText; btnElement.style.background = ""; btnElement.style.color = ""; }, 2000); interactCode(type, codeId, 'view', null); }
function copyPrompt(btn, text) { navigator.clipboard.writeText(text); const originalText = btn.innerText; btn.innerText = "Copied!"; btn.style.background = "#00ff88"; btn.style.color = "#000"; setTimeout(() => { btn.innerText = originalText; btn.style.background = ""; btn.style.color = ""; }, 2000); }

function filterCodes(type) { 
    const query = document.getElementById(`search-${type}`).value.toLowerCase(); 
    ['single', 'full'].forEach(tab => { 
        document.querySelectorAll(`#${type}-${tab}-content .code-wrapper`).forEach(el => { 
            const title = el.querySelector('.code-title span').innerText.toLowerCase(); 
            const tagsText = el.getAttribute('data-tags') ? el.getAttribute('data-tags').toLowerCase() : "";
            el.style.display = (title.includes(query) || tagsText.includes(query)) ? 'block' : 'none'; 
        }); 
    }); 
}
function filterPrompts() { 
    const query = document.getElementById(`search-prompts`).value.toLowerCase(); 
    document.querySelectorAll('#dynamic-prompts .prompt-box').forEach(el => { 
        const title = el.querySelector('.prompt-text').innerText.toLowerCase(); 
        const tagsText = el.getAttribute('data-tags') ? el.getAttribute('data-tags').toLowerCase() : "";
        el.style.display = (title.includes(query) || tagsText.includes(query)) ? 'flex' : 'none'; 
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

async function interactCode(type, id, action, btnElement) { if(action === 'like' && !isLoggedIn) { alert("Please login to like codes!"); switchAuthPage(); return; } try { const res = await fetch('/api/interact-code', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type, id, action }) }); const data = await res.json(); if(res.ok && action === 'like') { btnElement.classList.add('liked'); btnElement.innerHTML = `🤍 ${data.likes}`; } } catch(e) {} }

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

// SPRINT 2: ADVANCED REPORT SYSTEM
function openReportModal(type, id) { 
    if(!isLoggedIn) { alert("Login to report content."); switchAuthPage(); return; } 
    document.getElementById('rep-item-type').value = type; 
    document.getElementById('rep-item-id').value = id; 
    document.getElementById('rep-reason-type').value = "";
    document.getElementById('rep-reason').value = ""; 
    document.getElementById('report-modal-overlay').style.display = 'flex'; 
}

async function submitReport(e) { 
    e.preventDefault(); 
    const btn = e.target.querySelector('button'); btn.innerText = "Submitting..."; 
    const reasonType = document.getElementById('rep-reason-type').value;
    let reasonText = document.getElementById('rep-reason').value;
    if(!reasonType) { alert("Please select a reason."); btn.innerText = "Submit Report"; return; }
    
    const finalReason = reasonText ? `${reasonType} - ${reasonText}` : reasonType;
    
    try { 
        const res = await fetch('/api/report', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ type: document.getElementById('rep-item-type').value, id: document.getElementById('rep-item-id').value, reason: finalReason }) }); 
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

let currentGlobalContent = { premium_codes: [] };
let lastContentHash = "";

async function loadDynamicContent() {
    try {
        const res = await fetch('/api/content'); if (!res.ok) return; 
        const rawText = await res.text(); if (rawText === lastContentHash) return; lastContentHash = rawText;
        const data = JSON.parse(rawText); currentGlobalContent = data; 
        
        const generateCodeHTML = (codes, isPremiumSection = false, typeName) => {
            if (codes.length === 0) return '<p style="text-align: center; color: #888;">No items yet.</p>';
            return codes.map((item, index) => {
                const isLocked = isPremiumSection && !isPremiumUser; const blurStyle = isLocked ? 'filter: blur(5px); pointer-events: none; opacity: 0.6; user-select: none;' : '';
                const mainColor = isPremiumSection ? '#f5af19' : '#00d2ff'; const isFullWebsite = item.category.includes("Full Website");
                const bMarked = isBookmarked(typeName, item.id) ? 'bookmarked' : ''; const bMarkText = isBookmarked(typeName, item.id) ? 'Saved' : 'Save';
                
                let reviewBtnHTML = ''; if (isPremiumSection) { const stars = item.avg_rating > 0 ? `⭐ ${item.avg_rating}` : '⭐ New'; reviewBtnHTML = `<button onclick="openReviewModal(${item.id})" style="background: transparent; border: 1px solid #f5af19; color: #f5af19; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 0.8rem; margin-right: 10px;">${stars} (${item.reviews.length})</button>`; }
                let commentBtnHTML = ''; if (!isPremiumSection) { commentBtnHTML = `<button class="comment-btn" onclick="openCommentModal('${typeName}', ${item.id})">💬 Discuss</button>`; }
                const safeCode = item.code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                
                let tagsHTML = ""; 
                if(item.tags) { const tagsArray = item.tags.split(',').map(t => t.trim()).filter(t => t); tagsHTML = tagsArray.map(t => `<span class="tag-badge">#${t}</span>`).join(''); }

                let tipBtnHTML = "";
                if(!isPremiumSection && item.creator_email && item.creator_email !== 'admin') { tipBtnHTML = `<button class="submit-btn" style="width:auto; padding: 5px 10px; font-size:0.75rem; background:transparent; border:1px solid #f5af19; color:#f5af19; margin-left: 10px;" onclick="openUPIModal('Creator Tip - ${item.creator_email}', 50)">☕ Tip ₹50</button>`; }

                let html = `<div class="code-wrapper" data-tags="${item.tags}" style="margin-bottom: 40px; position: relative;"><div class="code-title" style="color: ${mainColor}; margin-bottom: 5px;"><span>0${index + 1}. ${item.title}</span></div><div style="margin-bottom: 15px;">${tagsHTML}</div>`;
                
                if (isFullWebsite) { html += `<div class="code-container" style="${blurStyle} padding: 40px; text-align: center; background: rgba(0,0,0,0.4);"><div style="font-size: 3rem; margin-bottom: 15px;">📁</div><h3 style="color: #fff; margin-bottom: 20px;">Full Website Files</h3><a href="${isLocked ? '#' : item.code}" target="${isLocked ? '' : '_blank'}" class="submit-btn" style="text-decoration: none; display: inline-block; width: auto; background: ${mainColor}; color: #000;" onclick="interactCode('${typeName}', ${item.id}, 'view', null)">Download</a></div>`; } 
                else { html += `<div class="code-container" style="${blurStyle}"><div class="code-header"><div class="dots"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div></div><div>${reviewBtnHTML}<a href="/code/${typeName}/${item.id}" target="_blank" style="color: #00d2ff; text-decoration: none; font-size: 0.8rem; margin-right: 15px; border-bottom: 1px dashed #00d2ff;">🔗 Share Page</a><button class="copy-main-btn" style="background: ${isPremiumSection ? '#f5af19' : ''}; color: ${isPremiumSection ? '#000' : ''};" onclick="copyMainCode('code-${item.id}', this, '${typeName}', ${item.id})">Copy Script</button></div></div><pre class="language-javascript"><code class="language-javascript" id="code-${item.id}">${safeCode}</code></pre></div>`; }
                
                html += `<div class="social-proof" style="${isLocked ? 'filter: blur(5px); pointer-events: none;' : ''}"><div style="display:flex; gap:15px; align-items:center;"><span>👁️ ${item.views} | By <a class="creator-link" onclick="viewProfile('${item.creator_username}')">${item.creator}</a></span>${commentBtnHTML}${tipBtnHTML}</div><div style="display:flex; gap:15px; align-items:center;"><button class="bookmark-btn ${bMarked}" onclick="toggleBookmark('${typeName}', ${item.id}, this)">🔖 ${bMarkText}</button><button class="like-btn" onclick="interactCode('${typeName}', ${item.id}, 'like', this)">🤍 ${item.likes}</button><button class="report-btn" onclick="openReportModal('${typeName}', ${item.id})">🚩</button></div></div>`;
                
                if (isLocked) { html += `<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; z-index: 10; width: 90%;"><div style="font-size: 2.5rem; margin-bottom: 10px;">🔒</div><h3 style="color: #f5af19; margin-bottom: 15px;">Premium Locked</h3><div style="display: flex; justify-content: center; gap: 10px;"><button class="submit-btn premium-btn" style="width: auto; padding: 10px 20px;" onclick="openUPIModal('Single File - ${item.title}', ${item.price}, ${item.id})">Buy ₹${item.price}</button><button class="submit-btn" style="width: auto; padding: 10px 15px; background: #333; border: 1px solid #f5af19;" onclick="openUPIModal('Single File - ${item.title}', ${item.price}, ${item.id}, true)">🎁</button><button class="submit-btn" style="width: auto; padding: 10px 20px;" onclick="switchPage('pricing')">Memberships</button></div></div>`; }
                html += `</div>`; return html;
            }).join('');
        };
        const freeSingle = data.codes.filter(c => c.category === 'Single Page' || c.category === 'Single Page Code'); const freeFull = data.codes.filter(c => c.category.includes('Full Website'));
        if(document.getElementById('free-single-content')) document.getElementById('free-single-content').innerHTML = generateCodeHTML(freeSingle, false, 'free');
        if(document.getElementById('free-full-content')) document.getElementById('free-full-content').innerHTML = generateCodeHTML(freeFull, false, 'free');
        const premSingle = data.premium_codes.filter(c => c.category === 'Single Page' || c.category === 'Single Page Code'); const premFull = data.premium_codes.filter(c => c.category.includes('Full Website'));
        if(document.getElementById('prem-single-content')) document.getElementById('prem-single-content').innerHTML = generateCodeHTML(premSingle, true, 'prem');
        if(document.getElementById('prem-full-content')) document.getElementById('prem-full-content').innerHTML = generateCodeHTML(premFull, true, 'prem');
        
        const promptContainer = document.getElementById('dynamic-prompts');
        if (promptContainer) { 
            promptContainer.innerHTML = data.prompts.length === 0 ? '<p style="text-align: center; color: #888;">No prompts published yet.</p>' : data.prompts.map((item) => {
                const bMarked = isBookmarked('prompt', item.id) ? 'bookmarked' : ''; const bMarkText = isBookmarked('prompt', item.id) ? 'Saved' : 'Save';
                let tagsHTML = ""; if(item.tags) { const tagsArray = item.tags.split(',').map(t => t.trim()).filter(t => t); tagsHTML = tagsArray.map(t => `<span class="tag-badge" style="font-size:0.65rem;">#${t}</span>`).join(''); }
                
                return `<div class="prompt-box" data-tags="${item.tags}"><div style="flex:1;"><span class="prompt-text" style="font-weight: bold; color: #00d2ff; display:block; margin-bottom:5px;">${item.title}</span><div style="margin-bottom:10px;">${tagsHTML}</div><div style="display:flex; gap:15px;"><button class="bookmark-btn ${bMarked}" onclick="toggleBookmark('prompt', ${item.id}, this)">🔖 ${bMarkText}</button><button class="comment-btn" onclick="openCommentModal('prompt', ${item.id})">💬 Discuss</button><button class="report-btn" onclick="openReportModal('prompt', ${item.id})">🚩</button></div></div><div style="display: flex; gap: 10px;"><a href="/code/prompt/${item.id}" target="_blank" class="submit-btn" style="padding: 5px 15px; font-size: 0.8rem; background: transparent; border: 1px dashed #00d2ff; color: #00d2ff; text-decoration:none; line-height: 1.5;">🔗 Share</a><button class="submit-btn" style="padding: 5px 15px; font-size: 0.8rem; background: transparent; border: 1px solid #b06ab3; color: #b06ab3;" onclick="openPromptModal(\`${item.title.replace(/`/g, '\\`')}\`, \`${item.prompt_text.replace(/`/g, '\\`')}\`)">View</button><button class="copy-btn" style="padding: 5px 15px; font-size: 0.8rem;" onclick="copyPrompt(this, \`${item.prompt_text.replace(/`/g, '\\`')}\`)">Copy</button></div></div>`;
            }).join(''); 
        }
        if(window.Prism) Prism.highlightAll();
    } catch (err) {}
}

function openReviewModal(codeId) { document.getElementById('rev-code-id').value = codeId; const code = currentGlobalContent.premium_codes.find(c => c.id === codeId); const listContainer = document.getElementById('review-list-container'); if (code && code.reviews.length > 0) { listContainer.innerHTML = code.reviews.map(r => `<div style="margin-bottom:10px; padding:10px; background:rgba(255,255,255,0.05); border-radius:5px;"><strong style="color:#f5af19;">${'⭐'.repeat(r.rating)}</strong> <span style="color:#aaa; font-size:0.8rem;">- ${r.user}</span><p style="margin:5px 0 0 0; color:#fff; font-size:0.9rem;">${r.comment}</p></div>`).join(''); } else { listContainer.innerHTML = '<p style="color:#888; font-size:0.9rem;">No reviews yet. Be the first!</p>'; } document.getElementById('review-modal-overlay').style.display = 'flex'; }
async function submitReview(e) { e.preventDefault(); if (!isLoggedIn) { alert("Please login first!"); return; } const btn = e.target.querySelector('button'); btn.innerText = "Submitting..."; try { const res = await fetch('/api/submit-review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code_id: document.getElementById('rev-code-id').value, rating: document.getElementById('rev-rating').value, comment: document.getElementById('rev-comment').value }) }); const data = await res.json(); if (res.ok) { alert(data.message); document.getElementById('review-modal-overlay').style.display = 'none'; e.target.reset(); loadDynamicContent(); } else { alert("Error: " + (data.error || data.message)); } } catch (err) {} btn.innerText = "Submit Review"; }

async function openCommentModal(type, id) {
    if (!isVerifiedUser) { alert("⚠️ Please verify your email in the Account Dashboard before commenting!"); switchPage('profile'); return; }
    document.getElementById('com-item-type').value = type; document.getElementById('com-item-id').value = id; document.getElementById('comment-modal-overlay').style.display = 'flex';
    const listContainer = document.getElementById('comment-list-container'); listContainer.innerHTML = '<p style="color:#888;">Loading...</p>';
    try {
        const res = await fetch(`/api/comments/${type}/${id}`);
        if(res.ok) { const data = await res.json(); if(data.length === 0) listContainer.innerHTML = '<p style="color:#888; font-size:0.9rem;">No comments yet. Start the discussion!</p>'; else listContainer.innerHTML = data.map(c => `<div style="margin-bottom:10px; padding:10px; background:rgba(0,255,136,0.05); border-left: 2px solid #00ff88; border-radius:5px;"><strong style="color:#fff;">${c.user}</strong> <span style="color:#888; font-size:0.75rem;">${c.date}</span><p style="margin:5px 0 0 0; color:#ccc; font-size:0.9rem;">${c.text}</p></div>`).join(''); }
    } catch(e) {}
}
async function submitComment(e) {
    e.preventDefault(); if (!isLoggedIn) { alert("Please login to comment!"); return; }
    const type = document.getElementById('com-item-type').value; const id = document.getElementById('com-item-id').value; const text = document.getElementById('com-text').value;
    try { 
        const res = await fetch('/api/add-comment', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({type, id, text}) }); 
        const data = await res.json();
        if(res.ok) { document.getElementById('com-text').value = ''; openCommentModal(type, id); } 
        else { alert("Error: " + (data.error || "Failed.")); if(data.error && data.error.includes("verify")) { document.getElementById('comment-modal-overlay').style.display='none'; switchPage('profile'); } }
    } catch(e) {}
}

let currentModalPromptText = ""; 
function openPromptModal(title, text) { document.getElementById('modal-prompt-title').innerText = title; document.getElementById('modal-prompt-text').innerText = text; currentModalPromptText = text; document.getElementById('prompt-modal-overlay').style.display = 'flex'; }
function closePromptModal() { document.getElementById('prompt-modal-overlay').style.display = 'none'; }
function copyFromModal(btnElement) { navigator.clipboard.writeText(currentModalPromptText); const originalText = btnElement.innerText; btnElement.innerText = "Copied!"; btnElement.style.background = "#00ff88"; btnElement.style.color = "#000"; setTimeout(() => { btnElement.innerText = originalText; btnElement.style.background = ""; btnElement.style.color = ""; }, 2000); }
function openResetModal() { document.getElementById('reset-modal-overlay').style.display = 'flex'; document.getElementById('request-code-form').style.display = 'block'; document.getElementById('verify-code-form').style.display = 'none'; document.getElementById('reset-email').value = ''; }
function closeResetModal() { document.getElementById('reset-modal-overlay').style.display = 'none'; }
async function handleRequestCode(e) { e.preventDefault(); const email = document.getElementById('reset-email').value; const btn = e.target.querySelector('button'); btn.innerText = "Sending..."; try { const res = await fetch('/forgot-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) }); if (res.ok) { document.getElementById('request-code-form').style.display = 'none'; document.getElementById('verify-code-form').style.display = 'block'; } else { alert("Error."); } } catch (err) {} btn.innerText = "Send Code"; }
async function handleResetPassword(e) { e.preventDefault(); try { const res = await fetch('/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: document.getElementById('reset-email').value, code: document.getElementById('reset-code').value, new_password: document.getElementById('reset-new-password').value }) }); const data = await res.json(); if (res.ok) { alert("Password updated!"); closeResetModal(); } else { alert("Error: " + data.message); } } catch (err) {} }

window.onload = () => { loadUserProfile().then(() => { loadDynamicContent(); loadLeaderboard(); }); };

setInterval(() => { if (isLoggedIn) { loadNotifications(); } }, 5000);
setInterval(() => { if (isLoggedIn && !isBannedUser) { loadDynamicContent(); } }, 10000);