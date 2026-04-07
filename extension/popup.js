// Popup JS for JobAgent QuickSave
const API_URL = 'https://agent-job-1.onrender.com';
let currentJob = null;

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  if (tab && tab.url) {
    try {
      chrome.tabs.sendMessage(tab.id, { action: "GET_JOB_INFO" }, (response) => {
        if (chrome.runtime.lastError || !response || !response.title) {
          document.getElementById('loading').innerText = "Aucune offre détectée. Ouvrez une offre sur LinkedIn ou WTTJ.";
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
      document.getElementById('loading').innerText = "Veuillez rafraîchir la page (F5) pour activer l'extraction.";
    }
  }

  // Handle Token
  const { token } = await chrome.storage.local.get('token');
  if (token) {
    document.getElementById('token-input').value = token;
  } else {
    // Attempt auto-detection if not set
    await attemptAutoTokenCapture();
  }
}

async function attemptAutoTokenCapture() {
  const status = document.getElementById('status');
  try {
    // Chercher l'onglet de l'app
    const tabs = await chrome.tabs.query({ url: "*://agent-candidature.vercel.app/*" });
    if (tabs.length > 0) {
      const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
        func: () => localStorage.getItem('token'),
      });

      if (result) {
        await chrome.storage.local.set({ token: result });
        document.getElementById('token-input').value = result;
        status.innerText = "✨ Connexion auto réussie !";
        status.style.color = '#2db87a';
        setTimeout(() => { if(status.innerText.includes('auto')) status.innerText = ''; }, 3000);
      }
    }
  } catch (e) {
    console.error("Auto-token check failed", e);
  }
}

// Navigation
document.getElementById('open-settings').addEventListener('click', () => {
  document.getElementById('main-view').style.display = 'none';
  document.getElementById('settings-view').style.display = 'block';
});

document.getElementById('back-btn').addEventListener('click', () => {
  document.getElementById('main-view').style.display = 'block';
  document.getElementById('settings-view').style.display = 'none';
});

// Settings Save
document.getElementById('save-settings').addEventListener('click', async () => {
  const token = document.getElementById('token-input').value.trim();
  if (!token) return alert('Veuillez saisir un token.');
  await chrome.storage.local.set({ token });
  alert('Configuration enregistrée !');
  document.getElementById('back-btn').click();
});

// Job Save Action
document.getElementById('save-btn').addEventListener('click', async () => {
  const btn = document.getElementById('save-btn');
  const status = document.getElementById('status');
  
  const { token } = await chrome.storage.local.get('token');
  if (!token) {
    status.innerText = "⚠️ Connectez-vous sur le site pour activer l'extension.";
    status.style.color = '#d4842a';
    return;
  }

  btn.disabled = true;
  btn.innerText = 'Enregistrement...';

  try {
    const params = new URLSearchParams({
      title: currentJob.title,
      company: currentJob.company,
      url: currentJob.url,
      platform: currentJob.platform
    });

    const res = await fetch(`${API_URL}/api/jobs/manual-create?${params}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (res.ok) {
      status.innerText = "✅ Offre ajoutée à votre tableau de bord !";
      status.style.color = '#2db87a';
      btn.style.display = 'none';
    } else {
      const err = await res.json();
      status.innerText = `❌ Erreur: ${err.detail || 'Session expirée'}`;
      status.style.color = '#c0392b';
      btn.disabled = false;
      btn.innerText = 'Réessayer';
      if (res.status === 401) await chrome.storage.local.remove('token');
    }
  } catch (e) {
    status.innerText = "❌ Serveur JobAgent injoignable.";
    status.style.color = '#c0392b';
    btn.disabled = false;
    btn.innerText = 'Réessayer';
  }
});

init();
