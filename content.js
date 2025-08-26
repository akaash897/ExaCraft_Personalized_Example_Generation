// Content script for AI Example Generator Extension

let currentSelection = null;
let popupElement = null;

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("Content script received message:", request);
  if (request.action === "showExamplePopup") {
    console.log("Showing example popup for topic:", request.topic);
    showExamplePopup(request.topic);
    sendResponse({ success: true });
  }
});

// Store selection information for dynamic positioning
function storeSelectionInfo() {
  const selection = window.getSelection();
  if (selection.rangeCount > 0) {
    const range = selection.getRangeAt(0);
    currentSelection = {
      range: range.cloneRange(),
      text: selection.toString(),
      // Store initial rect for reference
      initialRect: range.getBoundingClientRect()
    };
  }
}

// Check if current selection is still visible on screen
function isSelectionVisible() {
  if (!currentSelection) return false;
  
  try {
    const currentRect = currentSelection.range.getBoundingClientRect();
    const viewport = {
      top: 0,
      left: 0,
      bottom: window.innerHeight,
      right: window.innerWidth
    };
    
    // Check if selection is still within viewport with some tolerance
    const tolerance = 50; // pixels
    return !(currentRect.bottom < viewport.top - tolerance || 
             currentRect.top > viewport.bottom + tolerance ||
             currentRect.right < viewport.left - tolerance || 
             currentRect.left > viewport.right + tolerance);
  } catch (e) {
    // If range is invalid, consider it not visible
    return false;
  }
}

// Create and show popup with example
function showExamplePopup(topic) {
  console.log("showExamplePopup called with topic:", topic);
  // Store current selection info
  storeSelectionInfo();
  
  // Remove existing popup if any
  removeExistingPopup();
  
  // Create popup container
  const popup = document.createElement('div');
  popup.id = 'ai-example-popup';
  console.log("Created popup element:", popup);
  popup.innerHTML = `
    <div class="popup-header">
      <h3>🤖 AI Example</h3>
      <button class="close-btn">×</button>
    </div>
    <div class="popup-content">
      <div class="topic-section">
        <strong>Topic:</strong> <span class="topic">${escapeHtml(topic)}</span>
      </div>
      <div class="example-section">
        <div class="loading">
          <div class="spinner"></div>
          <span>Generating example...</span>
        </div>
        <div class="example-content" style="display: none;"></div>
      </div>
      <div class="popup-actions">
        <button class="action-btn regenerate-btn">🔄 Regenerate</button>
      </div>
    </div>
  `;
  
  // Add CSS styles
  addPopupStyles();
  
  // Position popup near the selection
  positionPopup(popup);
  
  // Add to page
  console.log("Adding popup to document body");
  document.body.appendChild(popup);
  popupElement = popup;
  console.log("Popup added to page, element:", popupElement);
  
  // Attach event listeners (Fix for CSP restrictions)
  popup.querySelector('.close-btn').addEventListener('click', () => {
    removeExistingPopup();
  });
  
  popup.querySelector('.regenerate-btn').addEventListener('click', () => {
    regenerateExample(topic);
  });
  
  // Set up scroll and resize listeners
  setupDynamicPositioning();
  
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
      display: flex;
      flex-direction: column;
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
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
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
      font-size: 20px;
      cursor: pointer;
      padding: 0;
      width: 24px;
      height: 24px;
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
      flex-grow: 1;
      padding: 20px;
      overflow-y: auto;
      min-height: 0;
    }
    
    .topic-section {
      margin-bottom: 12px;
      padding: 10px;
      background: #f8f9fa;
      border-radius: 6px;
      border-left: 4px solid #667eea;
      flex-shrink: 0;
    }
    
    .topic {
      font-weight: 600;
      color: #333;
    }
    
    .example-section {
      margin-bottom: 12px;
      flex: 1;
      min-height: 0;
    }
    
    .loading {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 20px 0;
      color: #666;
      justify-content: center;
    }
    
    .spinner {
      width: 16px;
      height: 16px;
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
      padding: 12px;
      border-radius: 6px;
      line-height: 1.6;
      border-left: 4px solid #28a745;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-size: 13px;
      min-height: 60px;
    }
    
    .example-content::-webkit-scrollbar {
      width: 6px;
    }
    
    .example-content::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 3px;
    }
    
    .example-content::-webkit-scrollbar-thumb {
      background: #888;
      border-radius: 3px;
    }
    
    .example-content::-webkit-scrollbar-thumb:hover {
      background: #555;
    }
    
    .popup-actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      flex-shrink: 0;
      margin-top: 8px;
    }
    
    .action-btn {
      background: #667eea;
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 11px;
      transition: background-color 0.2s;
    }
    
    .action-btn:hover {
      background: #5a6fd8;
    }
    
    .error-content {
      background: #f8d7da;
      color: #721c24;
      padding: 12px;
      border-radius: 6px;
      border-left: 4px solid #dc3545;
      white-space: pre-wrap;
      word-wrap: break-word;
      max-height: 300px;
      overflow-y: auto;
    }
    
    /* Responsive adjustments */
    @media (max-width: 480px) {
      #ai-example-popup {
        width: 95vw;
        max-height: 80vh;
      }
    }
  `;
  
  document.head.appendChild(styles);
}

function positionPopup(popup) {
  // For now, use simple center positioning for reliability
  popup.style.position = 'fixed';
  popup.style.top = '50%';
  popup.style.left = '50%';
  popup.style.transform = 'translate(-50%, -50%)';
}

function updatePopupPosition() {
  if (!popupElement || !currentSelection) return;
  
  // Check if selection is still visible
  if (!isSelectionVisible()) {
    removeExistingPopup();
    return;
  }
  
  // Update position based on current scroll
  positionPopup(popupElement);
}

function setupDynamicPositioning() {
  // Remove existing listeners first
  removeDynamicPositioning();
  
  // Add scroll listener with throttling
  let scrollTimeout;
  window.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(updatePopupPosition, 50);
  }, { passive: true });
  
  // Add resize listener
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(updatePopupPosition, 100);
  });
  
  // Store references for cleanup
  popupElement._scrollHandler = updatePopupPosition;
  popupElement._resizeHandler = updatePopupPosition;
}

function removeDynamicPositioning() {
  if (popupElement && popupElement._scrollHandler) {
    window.removeEventListener('scroll', popupElement._scrollHandler);
    window.removeEventListener('resize', popupElement._resizeHandler);
  }
}

function removeExistingPopup() {
  const existing = document.getElementById('ai-example-popup');
  if (existing) {
    removeDynamicPositioning();
    existing.remove();
  }
  popupElement = null;
  currentSelection = null;
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
      
      // Update position after content is loaded
      setTimeout(() => updatePopupPosition(), 100);
    }
  );
}

// Updated regenerate function to work with event listeners and track struggle
function regenerateExample(topic) {
  const content = document.querySelector('.example-content');
  const loading = document.querySelector('.loading');
  
  if (content && loading) {
    content.style.display = 'none';
    loading.style.display = 'flex';
    
    // Notify background script about regeneration (indicates struggle)
    chrome.runtime.sendMessage({ 
      action: "recordStruggleSignal", 
      topic: topic,
      signal_type: "regeneration_requested"
    });
    
    generateExampleForPopup(topic);
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Clean up on page unload
window.addEventListener('beforeunload', removeExistingPopup);