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
    @import url('https://fonts.googleapis.com/css2?family=Bubblegum+Sans&family=Comic+Neue:wght@400;700&family=Patrick+Hand&display=swap');

    #ai-example-popup {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 480px;
      max-width: 90vw;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      background: #FFFEF9;
      background-image:
        repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,182,193,0.1) 2px, rgba(255,182,193,0.1) 4px),
        repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(173,216,230,0.1) 2px, rgba(173,216,230,0.1) 4px);
      border-radius: 15px 5px 15px 5px;
      box-shadow:
        6px 6px 0 rgba(255,193,7,0.4),
        -3px -3px 0 rgba(255,193,7,0.1),
        0 10px 40px rgba(0,0,0,0.3);
      z-index: 10000;
      font-family: 'Comic Neue', 'Comic Sans MS', cursive;
      font-size: 14px;
      line-height: 1.5;
      overflow: hidden;
      border: 4px solid #2D3436;
      position: relative;
    }

    #ai-example-popup::before {
      content: "✨";
      position: absolute;
      top: 8px;
      right: 12px;
      font-size: 18px;
      animation: sparkle 2s infinite;
      z-index: 1;
      pointer-events: none;
    }

    @keyframes sparkle {
      0%, 100% { opacity: 1; transform: scale(1) rotate(0deg); }
      50% { opacity: 0.6; transform: scale(1.2) rotate(15deg); }
    }

    .popup-header {
      background: linear-gradient(135deg, #FFD93D 0%, #FFA737 100%);
      color: #2D3436;
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
      border-bottom: 4px solid #2D3436;
      box-shadow:
        inset 0 -2px 0 rgba(0,0,0,0.1),
        0 3px 0 #333;
      position: relative;
      z-index: 2;
    }

    .popup-header::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: repeating-linear-gradient(
        90deg,
        #2D3436 0px,
        #2D3436 10px,
        transparent 10px,
        transparent 15px
      );
    }

    .popup-header h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      font-family: 'Bubblegum Sans', cursive;
      text-shadow: 2px 2px 0 rgba(255,255,255,0.5);
      animation: wiggle 3s infinite;
    }

    @keyframes wiggle {
      0%, 100% { transform: rotate(-1deg); }
      50% { transform: rotate(1deg); }
    }

    .close-btn {
      background: #FF6B6B;
      border: 3px solid #2D3436;
      color: #2D3436;
      font-size: 20px;
      font-weight: 700;
      cursor: pointer;
      padding: 0;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
      box-shadow: 3px 3px 0 rgba(0,0,0,0.2);
      font-family: 'Comic Neue', cursive;
    }

    .close-btn:hover {
      transform: scale(1.1) rotate(5deg);
      box-shadow: 4px 4px 0 rgba(0,0,0,0.2);
    }

    .close-btn:active {
      transform: scale(0.95);
      box-shadow: 1px 1px 0 rgba(0,0,0,0.2);
    }

    .popup-content {
      flex-grow: 1;
      padding: 20px;
      overflow-y: auto;
      min-height: 0;
      position: relative;
      z-index: 1;
    }

    .topic-section {
      margin-bottom: 15px;
      padding: 12px;
      background: linear-gradient(135deg, #E3F2FD 0%, #FFF9C4 100%);
      border-radius: 10px 3px 10px 3px;
      border: 3px solid #2D3436;
      flex-shrink: 0;
      box-shadow: 3px 3px 0 rgba(0,0,0,0.1);
      transform: rotate(-0.5deg);
      position: relative;
    }

    .topic-section::before {
      content: "";
      position: absolute;
      top: -3px;
      left: -3px;
      right: -3px;
      bottom: -3px;
      border: 2px dashed rgba(255,193,7,0.3);
      border-radius: 10px 3px 10px 3px;
      pointer-events: none;
    }

    .topic-section strong {
      font-weight: 700;
      color: #FF6B6B;
      font-family: 'Bubblegum Sans', cursive;
    }

    .topic {
      font-weight: 600;
      color: #2D3436;
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
      padding: 30px 0;
      color: #2D3436;
      justify-content: center;
      font-weight: 600;
    }

    .spinner {
      width: 20px;
      height: 20px;
      border: 3px solid #FFD93D;
      border-top: 3px solid #FF6B6B;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .example-content {
      background: white;
      padding: 15px;
      border-radius: 12px 4px 12px 4px;
      line-height: 1.7;
      border: 3px solid #2D3436;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-size: 14px;
      min-height: 80px;
      box-shadow:
        4px 4px 0 rgba(40,167,69,0.3),
        -2px -2px 0 rgba(40,167,69,0.1);
      transform: rotate(0.3deg);
      position: relative;
    }

    .example-content::before {
      content: "";
      position: absolute;
      top: -3px;
      left: -3px;
      right: -3px;
      bottom: -3px;
      border: 2px dashed rgba(40,167,69,0.3);
      border-radius: 12px 4px 12px 4px;
      pointer-events: none;
    }

    .example-content::-webkit-scrollbar {
      width: 8px;
    }

    .example-content::-webkit-scrollbar-track {
      background: #FFF9E6;
      border-radius: 4px;
      border: 2px solid #2D3436;
    }

    .example-content::-webkit-scrollbar-thumb {
      background: #FFD93D;
      border-radius: 4px;
      border: 2px solid #2D3436;
    }

    .example-content::-webkit-scrollbar-thumb:hover {
      background: #FFA737;
    }

    .popup-actions {
      display: flex;
      gap: 10px;
      justify-content: center;
      flex-shrink: 0;
      margin-top: 12px;
    }

    .action-btn {
      background: linear-gradient(135deg, #74B9FF 0%, #A29BFE 100%);
      color: #2D3436;
      border: 3px solid #2D3436;
      padding: 10px 18px;
      border-radius: 20px 5px 20px 5px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 700;
      font-family: 'Bubblegum Sans', cursive;
      transition: all 0.2s;
      box-shadow:
        4px 4px 0 rgba(0,0,0,0.2),
        inset 0 -2px 0 rgba(0,0,0,0.1);
      position: relative;
      overflow: hidden;
    }

    .action-btn::before {
      content: "";
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
      transition: left 0.5s;
    }

    .action-btn:hover {
      transform: translateY(-2px) rotate(-1deg);
      box-shadow:
        6px 6px 0 rgba(0,0,0,0.2),
        inset 0 -2px 0 rgba(0,0,0,0.1);
    }

    .action-btn:hover::before {
      left: 100%;
    }

    .action-btn:active {
      transform: translateY(2px);
      box-shadow:
        2px 2px 0 rgba(0,0,0,0.2),
        inset 0 -2px 0 rgba(0,0,0,0.1);
    }

    .error-content {
      background: linear-gradient(135deg, #FFB8B8 0%, #FFA8A8 100%);
      color: #D63031;
      padding: 15px;
      border-radius: 12px 4px 12px 4px;
      border: 3px solid #2D3436;
      white-space: pre-wrap;
      word-wrap: break-word;
      max-height: 300px;
      overflow-y: auto;
      font-weight: 600;
      box-shadow:
        4px 4px 0 rgba(214,48,49,0.3),
        -2px -2px 0 rgba(214,48,49,0.1);
      transform: rotate(-0.3deg);
      position: relative;
    }

    .error-content::before {
      content: "";
      position: absolute;
      top: -3px;
      left: -3px;
      right: -3px;
      bottom: -3px;
      border: 2px dashed rgba(214,48,49,0.3);
      border-radius: 12px 4px 12px 4px;
      pointer-events: none;
    }

    /* Responsive adjustments */
    @media (max-width: 480px) {
      #ai-example-popup {
        width: 95vw;
        max-height: 85vh;
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