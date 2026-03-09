// Popup script for ExaCraft AI Example Generator Extension

document.addEventListener('DOMContentLoaded', function() {
  loadUserProfile();
  loadProviderSettings();

  document.getElementById('saveProfile').addEventListener('click', saveUserProfile);
  document.getElementById('testConnection').addEventListener('click', testApiConnection);
  document.getElementById('llmProvider').addEventListener('change', saveProviderSelection);
});

function loadUserProfile() {
  chrome.runtime.sendMessage({ action: "getUserProfile" }, (response) => {
    if (response.profile) {
      const profile = response.profile;
      document.getElementById('name').value = profile.name || '';
      document.getElementById('location').value = profile.location || '';
      document.getElementById('education').value = profile.education || '';
      document.getElementById('profession').value = profile.profession || '';
      document.getElementById('complexity').value = profile.complexity || 'medium';
    }
  });
}

function saveUserProfile() {
  const profile = {
    name: document.getElementById('name').value,
    location: document.getElementById('location').value,
    education: document.getElementById('education').value,
    profession: document.getElementById('profession').value,
    complexity: document.getElementById('complexity').value,
    updated_at: new Date().toISOString()
  };

  chrome.runtime.sendMessage(
    { action: "saveUserProfile", profile: profile },
    (response) => {
      const statusDiv = document.getElementById('status');
      statusDiv.style.display = 'block';

      if (response.success) {
        statusDiv.textContent = '✅ Profile saved successfully!';
        statusDiv.className = 'status success';
        syncProfileToFileSystem(profile, statusDiv);
      } else {
        statusDiv.textContent = '❌ Failed to save profile';
        statusDiv.className = 'status error';
      }

      setTimeout(() => { statusDiv.style.display = 'none'; }, 3000);
    }
  );
}

function syncProfileToFileSystem(profile, statusDiv) {
  fetch('http://localhost:8000/sync-profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile: profile })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      statusDiv.textContent = '✅ Profile saved & synced!';
      statusDiv.className = 'status success';
    } else {
      console.warn('Sync failed:', data.error);
      statusDiv.textContent = '⚠️ Profile saved, sync failed';
      statusDiv.className = 'status error';
    }
  })
  .catch(error => {
    console.warn('Sync API unavailable:', error);
  });
}

function loadProviderSettings() {
  chrome.storage.local.get("llmProvider", (result) => {
    const provider = result.llmProvider || 'gemini';
    document.getElementById('llmProvider').value = provider;
  });
}

function saveProviderSelection() {
  const provider = document.getElementById('llmProvider').value;
  const statusDiv = document.getElementById('providerStatus');

  chrome.storage.local.set({ llmProvider: provider }, () => {
    statusDiv.style.display = 'block';
    statusDiv.textContent = provider === 'openai'
      ? '✅ Using OpenAI (GPT-4o Mini)'
      : '✅ Using Google Gemini (Default)';
    statusDiv.className = 'status success';
    setTimeout(() => { statusDiv.style.display = 'none'; }, 3000);
  });
}

function testApiConnection() {
  const button = document.getElementById('testConnection');
  const statusDiv = document.getElementById('apiStatus');

  button.disabled = true;
  button.textContent = '🔄 Testing...';
  statusDiv.style.display = 'block';
  statusDiv.textContent = 'Connecting to API...';
  statusDiv.className = 'status';

  fetch('http://localhost:8000/health', {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  })
  .then(response => {
    if (response.ok) {
      statusDiv.textContent = '✅ API connection successful!';
      statusDiv.className = 'status success';
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  })
  .catch(() => {
    statusDiv.textContent = '❌ API connection failed. Make sure your Python server is running on localhost:8000';
    statusDiv.className = 'status error';
  })
  .finally(() => {
    button.disabled = false;
    button.textContent = '🔌 Test API Connection';
    setTimeout(() => { statusDiv.style.display = 'none'; }, 5000);
  });
}
