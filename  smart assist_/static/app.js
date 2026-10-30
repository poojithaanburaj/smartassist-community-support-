const API = '/api';
let token = localStorage.getItem('smartassist_token') || '';
let currentUser = JSON.parse(localStorage.getItem('smartassist_user') || 'null');
let map, caseLayer, ngoLayer;
const $ = (id) => document.getElementById(id);
const escapeHtml = (value='') => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, options={}) {
  const headers = {'Content-Type':'application/json', ...(options.headers || {})};
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(API + path, {...options, headers});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Request failed');
  return data;
}
function setMessage(el, text, kind='success') { el.textContent=text; el.className=`message ${kind}`; }
function initMap(){
  if (!window.L) return;
  map = L.map('map').setView([11.0168,76.9558],12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
  caseLayer = L.layerGroup().addTo(map); ngoLayer = L.layerGroup().addTo(map);
}
function statusLabel(status){return ({pending_verification:'Pending verification',in_progress:'In progress'})[status] || status.replaceAll('_',' ')}
function categoryLabel(category){return category.charAt(0).toUpperCase()+category.slice(1)}
function renderCases(cases){
  const q = $('search').value.trim().toLowerCase();
  const status = $('status-filter').value, category = $('category-filter').value;
  const filtered = cases.filter(c => (!status || c.status===status) && (!category || c.category===category) && (!q || [c.case_code,c.description,c.location_text,c.category].join(' ').toLowerCase().includes(q)));
  $('case-count').textContent = `${filtered.length} case${filtered.length===1?'':'s'}`;
  if (!filtered.length) {$('case-rows').innerHTML='<tr><td colspan="7" class="empty">No matching cases found.</td></tr>';return;}
  $('case-rows').innerHTML = filtered.map(c=>{
    let actions = `<button class="action-btn" data-action="details" data-code="${escapeHtml(c.case_code)}">Details</button>`;
    if (currentUser && ['field_worker','admin'].includes(currentUser.role)) {
      if(c.status==='pending_verification') actions += `<button class="action-btn" data-action="verify" data-code="${escapeHtml(c.case_code)}">Verify</button>`;
      if(c.status==='verified') actions += `<button class="action-btn" data-action="assign" data-code="${escapeHtml(c.case_code)}">Assign</button>`;
    }
    if (currentUser && ['field_worker','ngo','admin'].includes(currentUser.role)) {
      if(c.status==='assigned') actions += `<button class="action-btn" data-action="progress" data-code="${escapeHtml(c.case_code)}">Start</button><button class="action-btn" data-action="resolve" data-code="${escapeHtml(c.case_code)}">Resolve</button>`;
      if(c.status==='in_progress') actions += `<button class="action-btn" data-action="resolve" data-code="${escapeHtml(c.case_code)}">Resolve</button>`;
    }
    const date = c.created_at ? new Date(c.created_at).toLocaleDateString() : '—';
    return `<tr><td><span class="case-id">${escapeHtml(c.case_code)}</span><div class="case-desc" title="${escapeHtml(c.ai_summary)}">${escapeHtml(c.ai_summary)}</div></td><td><span class="category-pill cat-${c.category}">${categoryLabel(c.category)}</span></td><td>${escapeHtml(c.location_text||'Not provided')}</td><td><span class="urgency-pill ${c.urgency==='urgent_review'?'urgency-urgent_review':''}">${c.urgency==='urgent_review'?'Urgent review':'Normal'}</span></td><td><span class="status-pill status-${c.status}">${escapeHtml(statusLabel(c.status))}</span></td><td>${date}</td><td><div class="action-stack">${actions}</div></td></tr>`;
  }).join('');
}
let allCases=[];
async function loadCases(){
  try { allCases=await api('/reports'); renderCases(allCases); updateMap(); }
  catch(e){$('case-rows').innerHTML=`<tr><td colspan="7" class="empty">Could not load cases: ${escapeHtml(e.message)}</td></tr>`;}
}
async function loadDashboard(){
  try {const d=await api('/dashboard'); $('stat-total').textContent=d.total; $('stat-pending').textContent=d.pending_verification; $('stat-assigned').textContent=d.assigned; $('stat-resolved').textContent=d.resolved; $('hero-total').textContent=d.total; $('hero-urgent').textContent=d.urgent_review;}
  catch(e){console.warn(e)}
}
async function updateMap(){
  if(!map)return;
  caseLayer.clearLayers();ngoLayer.clearLayers();
  for(const c of allCases){if(c.latitude==null||c.longitude==null)continue;const marker=L.circleMarker([c.latitude,c.longitude],{radius:7,color:'#b84f40',fillColor:'#d96a58',fillOpacity:.85,weight:2}).bindPopup(`<strong>${escapeHtml(c.case_code)}</strong><br>${escapeHtml(categoryLabel(c.category))} · ${escapeHtml(statusLabel(c.status))}<br>${escapeHtml(c.location_text||'Reported location')}`);caseLayer.addLayer(marker)}
  try{const ngos=await api('/ngos');for(const n of ngos){if(!n.verified)continue;const marker=L.circleMarker([n.latitude,n.longitude],{radius:8,color:'#176b50',fillColor:'#30966c',fillOpacity:.85,weight:2}).bindPopup(`<strong>${escapeHtml(n.name)}</strong><br>${escapeHtml(n.services)}<br>Available slots: ${Math.max(0,n.capacity-n.active_cases)}`);ngoLayer.addLayer(marker)}}catch(e){console.warn(e)}
}
async function refresh(){await Promise.all([loadCases(),loadDashboard()]);}
$('report-form').addEventListener('submit',async e=>{
  e.preventDefault();const form=new FormData(e.currentTarget);const payload=Object.fromEntries(form.entries());
  payload.latitude=payload.latitude?Number(payload.latitude):null;payload.longitude=payload.longitude?Number(payload.longitude):null;
  try{const result=await api('/reports',{method:'POST',body:JSON.stringify(payload)});const d=result.case;let msg=`Report submitted successfully. Your case ID is ${d.case_code}. Category suggested by AI: ${d.category}. Status: pending verification.`;if(result.possible_duplicates.length)msg+=` Possible similar cases flagged for human review: ${result.possible_duplicates.map(x=>x.case_code).join(', ')}.`;msg+=' Keep the case ID to follow progress.';setMessage($('report-message'),msg,'success');e.currentTarget.reset();$('latitude').value='';$('longitude').value='';$('location-status').textContent='Location is optional.';await refresh();}
  catch(err){setMessage($('report-message'),err.message,'error')}
});
$('use-location').addEventListener('click',()=>{if(!navigator.geolocation){$('location-status').textContent='Geolocation is not supported by this browser.';return;}$('location-status').textContent='Requesting location permission…';navigator.geolocation.getCurrentPosition(pos=>{$('latitude').value=pos.coords.latitude;$('longitude').value=pos.coords.longitude;$('location-status').textContent='Location added. You can still edit the landmark.';},err=>{$('location-status').textContent=err.code===1?'Permission denied. You can enter a landmark instead.':'Could not get location. Enter a landmark instead.';},{enableHighAccuracy:false,timeout:10000});});
$('search').addEventListener('input',()=>renderCases(allCases));$('status-filter').addEventListener('change',()=>renderCases(allCases));$('category-filter').addEventListener('change',()=>renderCases(allCases));$('refresh').addEventListener('click',refresh);
$('case-rows').addEventListener('click',async e=>{const b=e.target.closest('button[data-action]');if(!b)return;const code=b.dataset.code, action=b.dataset.action;try{
  if(action==='details'){const c=await api('/reports/'+encodeURIComponent(code));let extra=`\n\nDescription: ${c.description}\nAI summary: ${c.ai_summary}\nStatus: ${statusLabel(c.status)}\nLocation: ${c.location_text||'Not provided'}`;if(c.ngo_name)extra+=`\nNGO: ${c.ngo_name}`;const matches=await api(`/reports/${encodeURIComponent(code)}/matches`);if(matches.length)extra+='\n\nEligible NGOs:\n'+matches.slice(0,5).map(n=>`• ${n.name} — ${n.available_slots} slots${n.distance_km==null?'':`, ${n.distance_km} km`}`).join('\n');alert(`${c.case_code}${extra}`);return;}
  if(!token){$('auth-modal').hidden=false;setMessage($('login-message'),'Sign in with an authorized staff account to manage cases.','error');return;}
  if(action==='verify'){const approved=confirm(`Verify case ${code}? Choose Cancel to reject the report.`);await api(`/reports/${encodeURIComponent(code)}/verify`,{method:'POST',body:JSON.stringify({approved})});setMessage($('action-message'),`${code} updated: ${approved?'verified':'rejected'}.`,'success');}
  if(action==='assign'){const c=await api('/reports/'+encodeURIComponent(code));const matches=await api(`/reports/${encodeURIComponent(code)}/matches`);if(!matches.length){alert('No verified NGO with matching service and available capacity was found.');return;}const choices=matches.map(n=>`${n.id}: ${n.name} (${n.available_slots} slots${n.distance_km==null?'':`, ${n.distance_km} km`})`).join('\n');const selected=prompt(`Choose an NGO ID:\n${choices}`,String(matches[0].id));if(!selected)return;const worker=prompt('Assigned worker name (optional):','');await api(`/reports/${encodeURIComponent(code)}/assign`,{method:'POST',body:JSON.stringify({ngo_id:Number(selected),assigned_worker:worker||''})});setMessage($('action-message'),`${code} assigned successfully.`,'success');}
  if(action==='progress'){await api(`/reports/${encodeURIComponent(code)}/status`,{method:'POST',body:JSON.stringify({status:'in_progress',note:'Work started'})});setMessage($('action-message'),`${code} marked in progress.`,'success');}
  if(action==='resolve'){if(!confirm(`Mark ${code} as resolved?`))return;await api(`/reports/${encodeURIComponent(code)}/status`,{method:'POST',body:JSON.stringify({status:'resolved',note:'Assistance delivered'})});setMessage($('action-message'),`${code} marked resolved.`,'success');}
  await refresh();
}catch(err){setMessage($('action-message'),err.message,'error')}});
$('auth-open').addEventListener('click',()=>{$('auth-modal').hidden=false});$('auth-close').addEventListener('click',()=>$('auth-modal').hidden=true);$('auth-modal').addEventListener('click',e=>{if(e.target===$('auth-modal'))$('auth-modal').hidden=true});
$('login-form').addEventListener('submit',async e=>{e.preventDefault();const payload=Object.fromEntries(new FormData(e.currentTarget).entries());try{const result=await api('/auth/login',{method:'POST',body:JSON.stringify(payload)});token=result.access_token;currentUser=result.user;localStorage.setItem('smartassist_token',token);localStorage.setItem('smartassist_user',JSON.stringify(currentUser));$('auth-modal').hidden=true;$('auth-open').textContent=currentUser.name.split(' ')[0];setMessage($('action-message'),`Signed in as ${currentUser.role}.`,'success');renderCases(allCases);}catch(err){setMessage($('login-message'),err.message,'error')}});
initMap();refresh();
