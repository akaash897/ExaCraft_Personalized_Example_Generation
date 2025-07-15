// Content script for AI Example Generator Extension

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "showExamplePopup") {
    showExamplePopup(request.topic);
    sendResponse({ success: true });
  }
});

// Create and show popup with example
function showExamplePopup(topic) {
  // Remove existing popup if any
  removeExistingPopup();
  
  // Create popup container
  const popup = document.createElement('div');
  popup.id = 'ai-example-popup';
  popup.innerHTML = `
    <div class="popup-header">
      <h3>🤖 AI Example Generator</h3>
      <button class="close-btn" onclick="this.parentElement.parentElement.remove()">×</button>
    </div>
    <div class="popup-content">
      <div class="topic-section">
        <strong>Topic:</strong> <span class="topic">${escapeHtml(topic)}</span>
      </div>
      <div class="example-section">
        <div class="loading">
          <div class="spinner"></div>
          <span>Generating personalized example...</span>
        </div>
        <div class="example-content" style="display: none;"></div>
      </div>
      <div class="popup-actions">
        <button class="action-btn" onclick="regenerateExample('${escapeHtml(topic)}')">🔄 Regenerate</button>
        <button class="action-btn" onclick="openSettings()">⚙️ Settings</button>
      </div>
    </div>
  `;
  
  // Add CSS styles
  addPopupStyles();
  
  // Position popup near the selection
  positionPopup(popup);
  
  // Add to page
  document.body.appendChild(popup);
  
  // Generate example
  generateExampleForPopup(topic);
}

function addPopupStyles() {
  if (document.getElementById('ai-example-styles')) return;
  
  const styles = document.createElement('style');
  styles.id = 'ai-example-styles';
  styles.textContent = `
    #ai-example-popup {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 450px;
      max-width: 90vw;
      max-height: 80vh;
      background: white;
      border-radius: 12px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.3);
      z-index: 10000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      line-height: 1.4;
      overflow: hidden;
      border: 1px solid #e1e5e9;
    }
    
    .popup-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .popup-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }
    
    .close-btn {
      background: none;
      border: none;
      color: white;
      font-size: 24px;
      cursor: pointer;
      padding: 0;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background-color 0.2s;
    }
    
    .close-btn:hover {
      background-color: rgba(255,255,255,0.2);
    }
    
    .popup-content {
      padding: 20px;
      max-height: 60vh;
      overflow-y: auto;
    }
    
    .topic-section {
      margin-bottom: 16px;
      padding: 12px;
      background: #f8f9fa;
      border-radius: 6px;
      border-left: 4px solid #667eea;
    }
    
    .topic {
      font-weight: 600;
      color: #333;
    }
    
    .example-section {
      margin-bottom: 16px;
    }
    
    .loading {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 20px 0;
      color: #666;
    }
    
    .spinner {
      width: 20px;
      height: 20px;
      border: 2px solid #f3f3f3;
      border-top: 2px solid #667eea;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    
    .example-content {
      background: #f8f9fa;
      padding: 16px;
      border-radius: 8px;
      white-space: pre-wrap;
      line-height: 1.6;
      border-left: 4px solid #28a745;
    }
    
    .popup-actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }
    
    .action-btn {
      background: #667eea;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      transition: background-color 0.2s;
    }
    
    .action-btn:hover {
      background: #5a6fd8;
    }
    
    .error-content {
      background: #f8d7da;
      color: #721c24;
      padding: 16px;
      border-radius: 8px;
      border-left: 4px solid #dc3545;
    }
  `;
  
  document.head.appendChild(styles);
}

function positionPopup(popup) {
  // Get current selection position
  const selection = window.getSelection();
  if (selection.rangeCount > 0) {
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    
    // Position popup near selection
    let top = rect.bottom + window.scrollY + 10;
    let left = rect.left + window.scrollX;
    
    // Keep popup within viewport
    const popupRect = popup.getBoundingClientRect();
    if (left + 450 > window.innerWidth) {
      left = window.innerWidth - 450 - 20;
    }
    if (top + 300 > window.innerHeight + window.scrollY) {
      top = rect.top + window.scrollY - 310;
    }
    
    popup.style.top = Math.max(10, top) + 'px';
    popup.style.left = Math.max(10, left) + 'px';
    popup.style.transform = 'none';
  }
}

function removeExistingPopup() {
  const existing = document.getElementById('ai-example-popup');
  if (existing) {
    existing.remove();
  }
}

function generateExampleForPopup(topic) {
  chrome.runtime.sendMessage(
    { action: "generateExample", topic: topic },
    (response) => {
      const popup = document.getElementById('ai-example-popup');
      if (!popup) return;
      
      const loading = popup.querySelector('.loading');
      const content = popup.querySelector('.example-content');
      
      loading.style.display = 'none';
      content.style.display = 'block';
      
      if (response.success) {
        content.textContent = response.example;
        content.className = 'example-content';
      } else {
        content.textContent = `Error: ${response.error}`;
        content.className = 'error-content';
      }
    }
  );
}

// Global functions for popup buttons
window.regenerateExample = function(topic) {
  const content = document.querySelector('.example-content');
  const loading = document.querySelector('.loading');
  
  if (content && loading) {
    content.style.display = 'none';
    loading.style.display = 'flex';
    generateExampleForPopup(topic);
  }
};

window.openSettings = function() {
  chrome.runtime.openOptionsPage();
};

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}