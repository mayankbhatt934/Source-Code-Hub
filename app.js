const KEY_USERS = 'sch_users';
const KEY_SESSION = 'sch_session';

function seedUsers(){
  if(!localStorage.getItem(KEY_USERS)){
    const seed=[
      {name:'Admin',email:'admin@sourcehub.ai',password:'admin123',role:'admin',premium:true},
      {name:'Mayank',email:'mayank@sourcehub.ai',password:'mayank123',role:'user',premium:true}
    ];
    localStorage.setItem(KEY_USERS, JSON.stringify(seed));
  }
}
function users(){return JSON.parse(localStorage.getItem(KEY_USERS)||'[]')}
function setUsers(u){localStorage.setItem(KEY_USERS, JSON.stringify(u))}
function session(){return JSON.parse(localStorage.getItem(KEY_SESSION)||'null')}
function setSession(s){localStorage.setItem(KEY_SESSION, JSON.stringify(s))}
function logout(){localStorage.removeItem(KEY_SESSION); location.href='index.html'}
function currentUser(){
  const s=session(); if(!s) return null;
  return users().find(u=>u.email===s.email) || null;
}
function requireAuth(){ if(!currentUser()){ location.href='login.html'; return null;} return currentUser();}
function requireAdmin(){ const u=requireAuth(); if(!u||u.role!=='admin'){ location.href='dashboard.html'; return null;} return u;}
function nav(el){
  const u=currentUser();
  el.innerHTML = `
    <div class="logo">SOURCE<span>HUB</span></div>
    <ul class="nav">
      <li><a href="index.html">Home</a></li>
      <li><a href="free-code.html">Free Code</a></li>
      <li><a href="premium-code.html">Premium Code</a></li>
      <li><a href="ai-prompts.html">AI Prompts</a></li>
      ${u ? '<li><a href="dashboard.html">Dashboard</a></li>' : '<li><a href="login.html">Login</a></li><li><a href="signup.html">Sign up</a></li>'}
      ${u?.role==='admin' ? '<li><a href="admin.html">Admin</a></li>' : ''}
      ${u ? '<li><button class="btn" onclick="logout()">Logout</button></li>' : ''}
    </ul>`;
}
function copyText(text, btn){navigator.clipboard.writeText(text); if(btn){const x=btn.textContent; btn.textContent='Copied!'; setTimeout(()=>btn.textContent=x,1200)}}
seedUsers();
