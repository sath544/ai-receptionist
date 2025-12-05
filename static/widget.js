// static/widget.js - embeddable widget
(function(){
  const client = (function(){
    const el = document.currentScript || document.scripts[document.scripts.length-1];
    return el && el.getAttribute('data-client') ? el.getAttribute('data-client') : 'demo';
  })();

  const css = document.createElement('link');
  css.rel = "stylesheet";
  css.href = "/static/widget.css";
  document.head.appendChild(css);

  const wrapper = document.createElement('div');
  wrapper.id = "ai-widget";
  wrapper.innerHTML = `
    <div id="ai-widget-bubble">Chat</div>
    <div id="ai-widget-panel" style="display:none">
      <div id="ai-widget-header">AI Receptionist<button id="ai-widget-close">×</button></div>
      <div id="ai-widget-body"></div>
      <div id="ai-widget-input">
        <input id="ai-widget-message" placeholder="Type a message..." />
        <button id="ai-widget-send">Send</button>
      </div>
    </div>
  `;
  document.body.appendChild(wrapper);

  const bubble = document.getElementById('ai-widget-bubble');
  const panel = document.getElementById('ai-widget-panel');
  const closeBtn = document.getElementById('ai-widget-close');
  const body = document.getElementById('ai-widget-body');
  const input = document.getElementById('ai-widget-message');
  const send = document.getElementById('ai-widget-send');

  bubble.addEventListener('click', ()=> { panel.style.display = 'block'; bubble.style.display='none'; addMessage("Hello! How can I help you today?"); });
  closeBtn.addEventListener('click', ()=> { panel.style.display='none'; bubble.style.display='block'; });

  function addMessage(text, who='bot'){
    const el = document.createElement('div');
    el.className = 'ai-msg ' + who;
    el.innerText = text;
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
  }

  send.addEventListener('click', sendMsg);
  input.addEventListener('keydown', function(e){ if (e.key==='Enter') sendMsg(); });

  function sendMsg(){
    const txt = input.value.trim();
    if (!txt) return;
    addMessage(txt, 'user');
    input.value = '';
    fetch('/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:txt, client:client})
    }).then(r=>r.json()).then(d=>{
      addMessage(d.reply || 'No reply');
    }).catch(e=>{
      addMessage('Network error');
    });
  }
})();
