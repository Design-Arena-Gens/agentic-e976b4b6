const transcriptEl = document.getElementById('transcript');
const responsesEl = document.getElementById('responses');
const micBtn = document.getElementById('micBtn');
const hiddenTel = document.getElementById('hiddenTel');

let recognition;
let listening = false;
let speechSynthesisSupported = 'speechSynthesis' in window;

function addBubble(container, text, role) {
  const div = document.createElement('div');
  div.className = `bubble ${role}`;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function speak(text) {
  if (!speechSynthesisSupported) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'en-US';
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

async function sendToAgent(text) {
  addBubble(transcriptEl, text, 'user');
  try {
    const res = await fetch('/api/agent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error('Agent error');
    const data = await res.json();

    if (data.response_text) {
      addBubble(responsesEl, data.response_text, 'agent');
      speak(data.response_text);
    }

    if (Array.isArray(data.actions)) {
      for (const action of data.actions) {
        await handleAction(action);
      }
    }
  } catch (err) {
    addBubble(responsesEl, `Error: ${err.message}`, 'agent');
  }
}

async function handleAction(action) {
  switch (action.type) {
    case 'open_url': {
      if (action.url) {
        window.open(action.url, '_blank');
      }
      break;
    }
    case 'call': {
      if (action.phone) {
        hiddenTel.href = `tel:${encodeURIComponent(action.phone)}`;
        hiddenTel.click();
      }
      break;
    }
    case 'create_calendar': {
      if (action.url) {
        window.open(action.url, '_blank');
      }
      break;
    }
    case 'message': {
      // Placeholder UI notification
      console.log(action.text || '');
      break;
    }
    default:
      console.log('Unknown action', action);
  }
}

function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    micBtn.disabled = true;
    addBubble(responsesEl, 'Speech recognition not supported in this browser.', 'agent');
    return;
  }
  recognition = new SR();
  recognition.lang = 'en-US';
  recognition.interimResults = true;
  recognition.continuous = true;

  let buffer = '';

  recognition.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i];
      if (res.isFinal) {
        buffer += res[0].transcript + ' ';
      } else {
        interim += res[0].transcript;
      }
    }
    // Update live interim transcript (optional)
  };

  recognition.onend = () => {
    micBtn.classList.remove('listening');
    micBtn.textContent = 'Start Listening';
    listening = false;
  };

  recognition.onerror = (e) => {
    addBubble(responsesEl, `Recognition error: ${e.error}`, 'agent');
  };

  // On stop, send the last sentence
  function flushAndSend() {
    if (!buffer.trim()) return;
    const text = buffer.trim();
    buffer = '';
    sendToAgent(text);
  }

  // Expose
  return { flushAndSend, getBuffer: () => buffer, setBuffer: (t) => (buffer = t) };
}

const control = initRecognition();

micBtn.addEventListener('click', () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;

  if (!listening) {
    recognition.start();
    listening = true;
    micBtn.classList.add('listening');
    micBtn.textContent = 'Stop Listening';
  } else {
    recognition.stop();
    control.flushAndSend();
  }
});

// Allow text input fallback via keyboard (press Enter with prompt())
window.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
    const t = prompt('Type your command for Jarvis:');
    if (t) sendToAgent(t);
  }
});
