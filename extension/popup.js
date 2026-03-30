// Popup JS for JobAgent QuickSave

const API_URL = 'https://agent-job-1.onrender.com';
let currentJob = null;

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  
  if (tab && tab.url) {
    try {
      chrome.tabs.sendMessage(tab.id, { action: "GET_JOB_INFO" }, (response) => {
        if (chrome.runtime.lastError || !response || !response.title) {
          document.getElementById('loading').innerText = "Aucune offre détectée sur cette page.";
          return;
        }

        currentJob = response;
        document.getElementById('loading').style.display = 'none';
        document.getElementById('job-card').style.display = 'block';
        document.getElementById('job-title').innerText = response.title;
        document.getElementById('job-company').innerText = response.company || 'Entreprise inconnue';
        document.getElementById('save-btn').style.display = 'block';
      });
    } catch(e) {
      document.getElementById('loading').innerText = "Veuillez rafraîchir la page ou vérifier l'URL.";
    }
  }

  // Load existing token
  const { token } = await chrome.storage.local.get('token');
  if (token) document.getElementById('token-input').value = token;
}

// Navigation
document.getElementById('open-settings').addEventListener('click', () => {
  document.getElementById('main-view').style.display = 'none';
  document.getElementById('settings-view').style.display = 'block';
  document.getElementById('open-settings').style.display = 'none';
});

document.getElementById('back-btn').addEventListener('click', () => {
  document.getElementById('main-view').style.display = 'block';
  document.getElementById('settings-view').style.display = 'none';
  document.getElementById('open-settings').style.display = 'block';
});

// Settings Save
document.getElementById('save-settings').addEventListener('click', async () => {
  const token = document.getElementById('token-input').value.trim();
  await chrome.storage.local.set({ token });
  alert('Réglages enregistrés !');
  document.getElementById('back-btn').click();
});

// Job Save Action
document.getElementById('save-btn').addEventListener('click', async () => {
  const btn = document.getElementById('save-btn');
  const status = document.getElementById('status');
  btn.disabled = true;
  btn.innerText = 'Sauvegarde...';

  const { token } = await chrome.storage.local.get('token');
  if (!token) {
    status.innerText = "⚠️ Token manquant. Allez dans les réglages.";
    status.style.color = '#d4842a';
    btn.disabled = false;
    btn.innerText = 'Sauvegarder';
    return;
  }

  try {
    const url = `${API_URL}/api/jobs/manual-create?title=${encodeURIComponent(currentJob.title)}&company=${encodeURIComponent(currentJob.company)}&url=${encodeURIComponent(currentJob.url)}&platform=${encodeURIComponent(currentJob.platform)}`;
    
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (res.ok) {
      status.innerText = "✅ Offre sauvegardée sur JobAgent !";
      status.style.color = '#2db87a';
      btn.style.display = 'none';
    } else {
      const err = await res.json();
      status.innerText = `❌ Erreur: ${err.detail || 'Inconnue'}`;
      status.style.color = '#c0392b';
      btn.disabled = false;
      btn.innerText = 'Réessayer';
    }
  } catch (e) {
    status.innerText = "❌ Connexion au serveur impossible.";
    status.style.color = '#c0392b';
    btn.disabled = false;
    btn.innerText = 'Réessayer';
  }
});

init();
