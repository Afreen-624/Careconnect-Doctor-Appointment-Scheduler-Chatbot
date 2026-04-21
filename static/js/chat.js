// =====================================================
// CareConnect — Chat Frontend Logic v2
// =====================================================

const messagesContainer = document.getElementById('chat-messages');
const chatInput          = document.getElementById('chat-input');
const sendBtn            = document.getElementById('send-btn');

let isTyping = false;

// ── Initialization ──────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await startConversation();
  chatInput.focus();
  updateStats();
  loadSidebar();
});

async function startConversation() {
  showTyping();
  try {
    const res  = await fetch('/api/start');
    const data = await res.json();
    hideTyping();
    renderResponses(data.responses);
  } catch (err) {
    hideTyping();
    renderBotMessage('👋 Hello! Welcome to CareConnect. How can I help you today?');
  }
}

// ── Send Message ─────────────────────────────────────
async function sendMessage(text) {
  const userText = (text || chatInput.value).trim();
  if (!userText || isTyping) return;

  // Display visible label for internal values
  const displayLabel = text ? null : userText;
  renderUserMessage(displayLabel || userText);
  if (!text) chatInput.value = '';
  chatInput.style.height = 'auto';

  showTyping();
  scrollToBottom();

  try {
    const res  = await fetch('/api/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: userText }),
    });
    const data = await res.json();
    hideTyping();
    await delay(150);
    renderResponses(data.responses);

    const redirect = data.responses.find(r => r.type === 'redirect');
    if (redirect) window.location.href = redirect.data.url;
  } catch (err) {
    hideTyping();
    renderBotMessage('❌ Connection error. Please try again.');
  }

  updateStats();
  scrollToBottom();
}

// helper: send a hidden value but show a friendly label in the bubble
async function sendWithLabel(value, label) {
  renderUserMessage(label);
  if (isTyping) return;
  showTyping();
  scrollToBottom();
  try {
    const res  = await fetch('/api/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: value }),
    });
    const data = await res.json();
    hideTyping();
    await delay(150);
    renderResponses(data.responses);
    const redirect = data.responses.find(r => r.type === 'redirect');
    if (redirect) window.location.href = redirect.data.url;
  } catch (err) {
    hideTyping();
    renderBotMessage('❌ Connection error.');
  }
  updateStats();
  scrollToBottom();
}

// ── Event Listeners ──────────────────────────────────
sendBtn.addEventListener('click', () => sendMessage());
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
});
document.querySelectorAll('.quick-action-btn').forEach(btn => {
  btn.addEventListener('click', () => sendMessage(btn.dataset.action));
});
document.querySelectorAll('.hint-chip').forEach(chip => {
  chip.addEventListener('click', () => { chatInput.value = chip.textContent; chatInput.focus(); });
});

// ── Render Dispatcher ─────────────────────────────────
function renderResponses(responses) {
  if (!responses?.length) return;
  responses.forEach((r, i) => setTimeout(() => { renderResponse(r); scrollToBottom(); }, i * 200));
}

function renderResponse(r) {
  switch (r.type) {
    case 'text':               if (r.text) renderBotMessage(r.text); break;
    case 'quick_reply':        if (r.text) renderBotMessage(r.text);
                               renderQuickReplies(r.data.options); break;
    case 'issue_options':      renderIssueOptions(r.data.options); break;
    case 'doctor_cards':       renderDoctorCards(r.data.doctors); break;
    case 'doctor_profile':     renderDoctorProfile(r.data.doctor); break;
    case 'date_picker':        if (r.text) renderBotMessage(r.text);
                               renderDatePicker(r.data.dates); break;
    case 'time_slots':         if (r.text) renderBotMessage(r.text);
                               renderTimeSlots(r.data.slots, r.data.pre_select); break;
    case 'branch_list':        if (r.text) renderBotMessage(r.text);
                               renderBranchList(r.data.branches); break;
    case 'confirm':            renderConfirmPanel(r.text, r.data.options); break;
    case 'appointment_report': renderAppointmentReport(r.data.report); break;
    case 'redirect':           if (r.text) renderBotMessage(r.text); break;
    default:                   if (r.text) renderBotMessage(r.text);
  }
}

// ── Message Bubbles ───────────────────────────────────
function renderUserMessage(text) {
  const g = document.createElement('div');
  g.className = 'message-group user';
  g.innerHTML = `
    <div class="message-content-wrap">
      <div class="message-bubble user-bubble">${escapeHtml(text)}</div>
      <span class="message-time">${getTime()}</span>
    </div>`;
  messagesContainer.appendChild(g);
}

function renderBotMessage(html) {
  if (!html || html.trim() === '') return;
  const g = document.createElement('div');
  g.className = 'message-group bot';
  g.innerHTML = `
    <div class="message-content-wrap">
      <div class="message-avatar bot-avatar">🏥</div>
      <div>
        <div class="message-bubble bot-bubble">${html}</div>
        <span class="message-time">${getTime()}</span>
      </div>
    </div>`;
  messagesContainer.appendChild(g);
}

// ── Quick Replies ─────────────────────────────────────
function renderQuickReplies(options) {
  const wrap = document.createElement('div');
  wrap.className = 'quick-replies';
  options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'quick-reply-btn';
    btn.textContent = opt.label;
    btn.addEventListener('click', () => {
      disableAll(wrap);
      sendWithLabel(opt.value, opt.label);
    });
    wrap.appendChild(btn);
  });
  messagesContainer.appendChild(wrap);
}

// ── Health Issue Options ──────────────────────────────
function renderIssueOptions(options) {
  const grid = document.createElement('div');
  grid.className = 'issue-grid';
  options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'issue-btn';
    btn.innerHTML = `<span class="issue-emoji">${opt.label.split(' ')[0]}</span>
                     <span class="issue-text">${opt.label.split(' ').slice(1).join(' ')}</span>`;
    btn.addEventListener('click', () => {
      disableAll(grid);
      btn.classList.add('selected');
      sendWithLabel(opt.value, opt.label);
    });
    grid.appendChild(btn);
  });
  messagesContainer.appendChild(grid);
}

// ── Doctor Cards ──────────────────────────────────────
function renderDoctorCards(doctors) {
  const wrap = document.createElement('div');
  wrap.className = 'doctor-cards-wrap';
  if (!doctors?.length) {
    wrap.innerHTML = '<p style="color:#aaa;padding:12px">No doctors available at this branch for your concern.</p>';
    messagesContainer.appendChild(wrap);
    return;
  }
  doctors.forEach(doc => {
    const card = document.createElement('div');
    card.className = 'doctor-card';
    const stars = '⭐'.repeat(Math.min(Math.round(doc.rating), 5));
    card.innerHTML = `
      <div class="doctor-avatar">👨‍⚕️</div>
      <div class="doctor-info">
        <div class="doctor-name">${doc.name}</div>
        <div class="doctor-spec">${doc.specialization}</div>
        ${doc.about ? `<div class="doctor-about">${doc.about}</div>` : ''}
        <div class="doctor-meta">
          <div class="doctor-rating">${stars} ${doc.rating}</div>
          <div class="doctor-exp">${doc.experience} yrs exp</div>
          <div class="doctor-fee">₹${doc.fee}</div>
        </div>
        ${doc.working_days?.length ? `<div class="doctor-days">📅 ${Array.isArray(doc.working_days) ? doc.working_days.join(', ') : doc.working_days}</div>` : ''}
      </div>`;
    card.addEventListener('click', () => {
      disableAll(wrap);
      card.classList.add('selected-card');
      sendWithLabel(`select_doctor_${doc.id}`, `Selected: ${doc.name}`);
    });
    wrap.appendChild(card);
  });
  messagesContainer.appendChild(wrap);
}

// ── Doctor Profile (shown after selection) ────────────
function renderDoctorProfile(doc) {
  if (!doc) return;
  const card = document.createElement('div');
  card.className = 'doctor-profile-card';
  const stars = '⭐'.repeat(Math.min(Math.round(doc.rating), 5));
  card.innerHTML = `
    <div class="profile-header">
      <div class="profile-avatar">👨‍⚕️</div>
      <div class="profile-main">
        <div class="profile-name">${doc.name}</div>
        <div class="profile-spec">${doc.specialization}</div>
        <div class="profile-rating">${stars} ${doc.rating} / 5</div>
      </div>
    </div>
    ${doc.about ? `<div class="profile-about">${doc.about}</div>` : ''}
    <div class="profile-meta-row">
      <div class="profile-meta-item"><span>🏥</span> ${doc.hospital || ''}</div>
      ${doc.address ? `<div class="profile-meta-item"><span>📍</span> ${doc.address}</div>` : ''}
      <div class="profile-meta-item"><span>💼</span> ${doc.experience} years exp</div>
      <div class="profile-meta-item"><span>💰</span> ₹${doc.fee} consultation</div>
      ${doc.working_days ? `<div class="profile-meta-item"><span>📅</span> ${doc.working_days}</div>` : ''}
    </div>`;
  messagesContainer.appendChild(card);
}

// ── Date Picker ───────────────────────────────────────
function renderDatePicker(dates) {
  const wrap = document.createElement('div');
  wrap.className = 'date-picker-wrap';
  (dates || []).forEach(date => {
    const chip = document.createElement('button');
    chip.className = 'date-chip';
    // Parse and format nicely
    const parts = date.split(' ');
    chip.innerHTML = `<span class="date-num">${parts[0]}</span><span class="date-mon">${parts[1]}</span>`;
    chip.title = date;
    chip.addEventListener('click', () => {
      wrap.querySelectorAll('.date-chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      setTimeout(() => { disableAll(wrap); sendWithLabel(date, date); }, 300);
    });
    wrap.appendChild(chip);
  });
  messagesContainer.appendChild(wrap);
}

// ── Time Slots ────────────────────────────────────────
function renderTimeSlots(slots, preSelect) {
  const wrap = document.createElement('div');
  wrap.className = 'time-slots-wrap';
  // Group by period
  const groupedHtml = '<div class="slots-label">Morning</div>';
  (slots || []).forEach(slot => {
    const chip = document.createElement('button');
    chip.className = 'time-chip' + (slot === preSelect ? ' selected' : '');
    const isAM = slot.includes('AM');
    const hour = parseInt(slot.split(':')[0]);
    let period = isAM ? '🌅' : (hour < 5 ? '☀️' : '🌆');
    chip.innerHTML = `${period} ${slot}`;
    chip.addEventListener('click', () => {
      wrap.querySelectorAll('.time-chip').forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      setTimeout(() => { disableAll(wrap); sendWithLabel(slot, slot); }, 300);
    });
    wrap.appendChild(chip);
  });
  messagesContainer.appendChild(wrap);
}

// ── Branch List ───────────────────────────────────────
function renderBranchList(branches) {
  const wrap = document.createElement('div');
  wrap.className = 'branch-list-wrap';
  (branches || []).forEach(branch => {
    const card = document.createElement('div');
    card.className = 'branch-card';
    card.innerHTML = `
      <div class="branch-icon">🏥</div>
      <div>
        <div class="branch-name">${branch.name}</div>
        <div class="branch-address">📍 ${branch.address}</div>
      </div>`;
    card.addEventListener('click', () => {
      disableAll(wrap);
      card.classList.add('selected-card');
      sendWithLabel(branch.name, branch.name);
    });
    wrap.appendChild(card);
  });
  messagesContainer.appendChild(wrap);
}

// ── Confirm Panel ─────────────────────────────────────
function renderConfirmPanel(text, options) {
  const panel = document.createElement('div');
  panel.className = 'confirm-panel';
  const lines = (text || '').split('<br>').filter(l => l.trim());
  const title = lines[0] || 'Booking Summary';
  const details = lines.slice(1).filter(l => l.includes(':') || l.includes('<strong>'));

  const detailsHtml = details.map(line => {
    const stripped = line.replace(/<\/?strong>/g, '');
    const colonIdx = stripped.indexOf(':');
    if (colonIdx < 0) return `<div class="confirm-row">${line}</div>`;
    const key = stripped.slice(0, colonIdx).trim();
    const val = stripped.slice(colonIdx + 1).trim();
    return `<div class="confirm-row"><span class="confirm-label">${key}</span><span class="confirm-value">${val}</span></div>`;
  }).join('');

  panel.innerHTML = `<div class="panel-title">📋 Booking Summary</div><div class="confirm-rows">${detailsHtml}</div>`;
  const actions = document.createElement('div');
  actions.className = 'confirm-actions';
  (options || []).forEach(opt => {
    const btn = document.createElement('button');
    btn.className = opt.value === 'yes' ? 'btn-confirm' : 'btn-decline';
    btn.textContent = opt.label;
    btn.addEventListener('click', () => { disableAll(panel); sendWithLabel(opt.value, opt.label); });
    actions.appendChild(btn);
  });
  panel.appendChild(actions);
  messagesContainer.appendChild(panel);
}

// ── Appointment Report ────────────────────────────────
function renderAppointmentReport(report) {
  const card = document.createElement('div');
  card.className = 'report-card';
  const statusClass = (report.status || 'confirmed').toLowerCase();
  card.innerHTML = `
    <div class="report-header">
      <div class="report-check">✅</div>
      <div>
        <div class="report-title">Appointment ${report.status || 'Confirmed'}!</div>
        <div class="report-apt-id">Appointment ID</div>
      </div>
    </div>
    <div class="report-id-badge">🎟️ ${report.appointment_id}</div>
    <div class="report-rows">
      <div class="report-row"><span class="report-icon">🎟️</span><span class="report-key">Apt ID</span><span class="report-val">${report.appointment_id}</span></div>
      ${report.patient_id ? `<div class="report-row"><span class="report-icon">🆔</span><span class="report-key">Patient ID</span><span class="report-val">${report.patient_id}</span></div>` : ''}
      <div class="report-row"><span class="report-icon">👤</span><span class="report-key">Patient</span><span class="report-val">${report.patient_name}</span></div>
      ${report.patient_age ? `<div class="report-row"><span class="report-icon">🎂</span><span class="report-key">Age</span><span class="report-val">${report.patient_age} years${report.patient_dob ? ' (DOB: ' + report.patient_dob + ')' : ''}</span></div>` : ''}
      ${report.health_issue ? `<div class="report-row"><span class="report-icon">🩺</span><span class="report-key">Concern</span><span class="report-val">${report.health_issue}</span></div>` : ''}
      <div class="report-row"><span class="report-icon">👨‍⚕️</span><span class="report-key">Doctor</span><span class="report-val">${report.doctor_name} (${report.specialization})</span></div>
      <div class="report-row"><span class="report-icon">⭐</span><span class="report-key">Rating</span><span class="report-val">${report.rating} / 5</span></div>
      <div class="report-row"><span class="report-icon">🏥</span><span class="report-key">Hospital</span><span class="report-val">${report.hospital_name}</span></div>
      <div class="report-row"><span class="report-icon">📍</span><span class="report-key">City</span><span class="report-val">${report.city}${report.state ? ', ' + report.state : ''}</span></div>
      <div class="report-row"><span class="report-icon">📅</span><span class="report-key">Date</span><span class="report-val">${report.date}</span></div>
      <div class="report-row"><span class="report-icon">⏰</span><span class="report-key">Time</span><span class="report-val">${report.time}</span></div>
      <div class="report-row"><span class="report-icon">💰</span><span class="report-key">Fee</span><span class="report-val">₹${report.fee}</span></div>
      <div class="report-row"><span class="report-icon">📌</span><span class="report-key">Status</span><span class="report-val"><span class="status-badge status-${statusClass}">● ${report.status}</span></span></div>
    </div>
    <div class="report-footer">🔔 Please arrive <strong>10 minutes</strong> before your scheduled time. Bring a valid ID.</div>
    <div class="report-qr">
      <div id="qr-${report.appointment_id}" class="qr-container"></div>
      <div class="report-qr-label">Scan to check in digitally</div>
    </div>`;
  messagesContainer.appendChild(card);

  setTimeout(() => {
    try {
      new QRCode(document.getElementById(`qr-${report.appointment_id}`), {
        text: `APT:${report.appointment_id}|PAT:${report.patient_name}|DOC:${report.doctor_name}|DATE:${report.date}|TIME:${report.time}`,
        width: 100, height: 100,
        colorDark: '#6366f1', colorLight: 'transparent',
        correctLevel: QRCode.CorrectLevel.M
      });
    } catch (e) {}

    const actions = document.createElement('div');
    actions.className = 'quick-replies';
    actions.style.marginTop = '12px';
    actions.innerHTML = `
      <button class="quick-reply-btn" onclick="sendMessage('book')">📅 Book Another</button>
      <button class="quick-reply-btn" onclick="window.location.href='/dashboard'">📋 View Dashboard</button>`;
    messagesContainer.appendChild(actions);
    scrollToBottom();
  }, 150);
}

// ── Typing Indicator ─────────────────────────────────
function showTyping() {
  isTyping = true;
  const el = document.createElement('div');
  el.className = 'typing-indicator'; el.id = 'typing-indicator';
  el.innerHTML = `
    <div class="message-avatar bot-avatar" style="font-size:14px">🏥</div>
    <div class="typing-dots">
      <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
    </div>`;
  messagesContainer.appendChild(el);
  scrollToBottom();
}
function hideTyping() {
  isTyping = false;
  document.getElementById('typing-indicator')?.remove();
}

// ── Sidebar ───────────────────────────────────────────
async function loadSidebar() {
  try {
    const res = await fetch('/api/sidebar');
    if (!res.ok) return;
    const data = await res.json();
    const statesEl = document.getElementById('sidebar-states');
    if (statesEl && data.states) {
      statesEl.innerHTML = data.states.map(s =>
        `<div class="sidebar-item">🗺️ ${s}</div>`
      ).join('');
    }
  } catch (e) {}
}

// ── Utility ──────────────────────────────────────────
function scrollToBottom() {
  setTimeout(() => messagesContainer.scrollTo({ top: messagesContainer.scrollHeight, behavior: 'smooth' }), 50);
}
function disableAll(container) {
  container.querySelectorAll('button, .doctor-card, .branch-card, .issue-btn').forEach(el => {
    el.style.opacity = '0.5'; el.style.pointerEvents = 'none';
  });
}
function getTime() {
  return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}
function escapeHtml(text) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(text));
  return d.innerHTML;
}
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

async function updateStats() {
  try {
    const res  = await fetch('/api/appointments');
    const apts = await res.json();
    const confirmed = apts.filter(a => a.status === 'Confirmed').length;
    const el1 = document.getElementById('stat-confirmed');
    const el2 = document.getElementById('stat-total');
    if (el1) el1.textContent = confirmed;
    if (el2) el2.textContent = apts.length;
  } catch (e) {}
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && confirm('Restart conversation?')) startConversation();
});
