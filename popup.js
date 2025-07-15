// Popup script for AI Example Generator Extension

document.addEventListener('DOMContentLoaded', function() {
  loadUserProfile();
  
  // Save profile button
  document.getElementById('saveProfile').addEventListener('click', saveUserProfile);
  
  // Test API connection button
  document.getElementById('testConnection').addEventListener('click', testApiConnection);
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
      } else {
        statusDiv.textContent = '❌ Failed to save profile';
        statusDiv.className = 'status error';
      }
      
      // Hide status after 3 seconds
      setTimeout(() => {
        statusDiv.style.display = 'none';
      }, 3000);
    }
  );
}

function testApiConnection() {
  const button = document.getElementById('testConnection');
  const statusDiv = document.getElementById('apiStatus');
  
  button.disabled = true;
  button.textContent = '🔄 Testing...';
  statusDiv.style.display = 'block';
  statusDiv.textContent = 'Connecting to API...';
  statusDiv.className = 'status';
  
  // Test the API with a simple request
  fetch('http://localhost:8000/health', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  })
  .then(response => {
    if (response.ok) {
      statusDiv.textContent = '✅ API connection successful!';
      statusDiv.className = 'status success';
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  })
  .catch(error => {
    statusDiv.textContent = '❌ API connection failed. Make sure your Python server is running on localhost:8000';
    statusDiv.className = 'status error';
  })
  .finally(() => {
    button.disabled = false;
    button.textContent = '🔌 Test API Connection';
    
    // Hide status after 5 seconds
    setTimeout(() => {
      statusDiv.style.display = 'none';
    }, 5000);
  });
}