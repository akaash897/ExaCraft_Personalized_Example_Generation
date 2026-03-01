// Content script for AI Example Generator Extension

let currentSelection = null;
let popupElement = null;
let currentThreadId = null;
let currentTopic = null;
let workflowMode = false;
let feedbackInfluence = null;

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
        <div class="example-header" style="display: none; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="font-size: 12px; font-weight: 700; color: #2D3436;">Generated Example</span>
          <button class="info-icon-btn" title="How did feedback affect this example?" style="background: none; border: none; font-size: 18px; cursor: pointer; padding: 4px 8px; border-radius: 50%; transition: all 0.2s;">ℹ️</button>
        </div>
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

    /* Feedback Section Styles */
    .feedback-section {
      background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
      padding: 15px;
      border-radius: 12px 4px 12px 4px;
      border: 3px solid #2D3436;
      box-shadow: 3px 3px 0 rgba(0,0,0,0.1);
    }

    .feedback-header {
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 2px dashed rgba(45,52,54,0.2);
    }

    .rating-group {
      margin-bottom: 10px;
    }

    .rating-group label {
      display: block;
      font-size: 12px;
      margin-bottom: 4px;
      color: #636E72;
      font-weight: 600;
    }

    .rating-group input[type="range"] {
      -webkit-appearance: none;
      width: 100%;
      height: 8px;
      border-radius: 5px;
      background: linear-gradient(to right, #FF6B6B 0%, #FFD93D 50%, #55EFC4 100%);
      outline: none;
      border: 2px solid #2D3436;
    }

    .rating-group input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: #2D3436;
      cursor: pointer;
      border: 3px solid white;
      box-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .rating-group input[type="range"]::-moz-range-thumb {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: #2D3436;
      cursor: pointer;
      border: 3px solid white;
      box-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .submit-feedback-btn {
      background: linear-gradient(135deg, #55EFC4 0%, #81ECEC 100%) !important;
    }

    .skip-feedback-btn {
      background: linear-gradient(135deg, #DFE6E9 0%, #B2BEC3 100%) !important;
    }

    /* Info Icon Styles */
    .info-icon-btn {
      background: none;
      border: none;
      font-size: 18px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 50%;
      transition: all 0.2s;
    }

    .info-icon-btn:hover {
      background: rgba(45, 52, 54, 0.1);
      transform: scale(1.1);
    }

    /* Feedback Influence Modal */
    .influence-modal {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      z-index: 10001;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      animation: fadeIn 0.2s;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .influence-modal-content {
      background: #FFFEF9;
      border: 4px solid #2D3436;
      border-radius: 15px 5px 15px 5px;
      max-width: 600px;
      max-height: 80vh;
      overflow-y: auto;
      box-shadow: 0 10px 40px rgba(0,0,0,0.4);
      animation: slideUp 0.3s;
    }

    @keyframes slideUp {
      from {
        transform: translateY(20px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }

    .influence-header {
      background: linear-gradient(135deg, #A29BFE 0%, #74B9FF 100%);
      padding: 20px;
      border-bottom: 4px solid #2D3436;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .influence-header h2 {
      margin: 0;
      font-size: 20px;
      color: #2D3436;
      font-family: 'Bubblegum Sans', cursive;
    }

    .influence-body {
      padding: 20px;
      font-family: 'Comic Neue', cursive;
      color: #2D3436;
    }

    .influence-section {
      margin-bottom: 20px;
      padding: 15px;
      background: white;
      border: 3px solid #2D3436;
      border-radius: 10px;
      box-shadow: 3px 3px 0 rgba(0,0,0,0.1);
    }

    .influence-section h3 {
      margin: 0 0 12px 0;
      font-size: 16px;
      color: #FF6B6B;
      font-family: 'Bubblegum Sans', cursive;
    }

    .influence-item {
      margin-bottom: 10px;
      padding: 10px;
      background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
      border-radius: 8px;
      border: 2px solid #2D3436;
    }

    .influence-label {
      font-weight: 700;
      color: #636E72;
      font-size: 12px;
      text-transform: uppercase;
      margin-bottom: 4px;
    }

    .influence-value {
      color: #2D3436;
      font-size: 14px;
    }

    .adaptation-badge {
      display: inline-block;
      padding: 4px 10px;
      margin: 4px 4px 4px 0;
      background: linear-gradient(135deg, #55EFC4 0%, #81ECEC 100%);
      border: 2px solid #2D3436;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 700;
    }

    .no-feedback-message {
      text-align: center;
      padding: 30px;
      color: #636E72;
      font-style: italic;
    }

    /* Responsive adjustments */
    @media (max-width: 480px) {
      #ai-example-popup {
        width: 95vw;
        max-height: 85vh;
      }

      .influence-modal-content {
        max-width: 95vw;
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
  currentThreadId = null;
  currentTopic = null;
  workflowMode = false;
  feedbackInfluence = null;
}

function generateExampleForPopup(topic) {
  currentTopic = topic;

  chrome.runtime.sendMessage(
    { action: "generateExample", topic: topic },
    (response) => {
      console.log('[Content] Received response:', response);

      const popup = document.getElementById('ai-example-popup');
      if (!popup) return;

      const loading = popup.querySelector('.loading');
      const content = popup.querySelector('.example-content');
      const actionsDiv = popup.querySelector('.popup-actions');

      loading.style.display = 'none';
      content.style.display = 'block';

      if (response.success) {
        // Debugging: Check what we got
        if (!response.example) {
          console.error('[Content] No example in response!', response);
          content.textContent = 'Error: No example generated. Check console logs.';
          content.className = 'error-content';
          showLegacyActions(actionsDiv);
          return;
        }

        content.textContent = response.example;
        content.className = 'example-content';

        // Store workflow information
        workflowMode = response.workflowMode || false;
        currentThreadId = response.threadId || null;
        feedbackInfluence = response.feedbackInfluence || null;

        // Show info icon if feedback influence is available
        const exampleHeader = popup.querySelector('.example-header');
        if (feedbackInfluence && feedbackInfluence.has_previous_feedback) {
          console.log('[Content] Feedback influence available:', feedbackInfluence);
          exampleHeader.style.display = 'flex';

          // Attach click listener to info icon
          const infoBtn = exampleHeader.querySelector('.info-icon-btn');
          infoBtn.addEventListener('click', () => {
            showFeedbackInfluenceModal(feedbackInfluence);
          });
        } else {
          exampleHeader.style.display = 'none';
        }

        // Show feedback UI if in workflow mode
        if (workflowMode && currentThreadId) {
          console.log('[Content] Workflow mode active, showing feedback UI');
          showFeedbackUI(actionsDiv);
        } else {
          console.log('[Content] Legacy mode, showing regenerate only');
          showLegacyActions(actionsDiv);
        }

      } else {
        content.textContent = response.example || `Error: ${response.error}`;
        content.className = 'error-content';
        showLegacyActions(actionsDiv);
      }

      // Update position after content is loaded
      setTimeout(() => updatePopupPosition(), 100);
    }
  );
}

function showFeedbackUI(actionsDiv) {
  actionsDiv.innerHTML = `
    <div class="feedback-section" style="width: 100%; margin-top: 10px;">
      <div class="feedback-header" style="text-align: center; margin-bottom: 12px;">
        <strong style="color: #2D3436; font-size: 14px;">📊 Rate this example:</strong>
      </div>

      <div class="rating-group" style="margin-bottom: 10px;">
        <label style="display: block; font-size: 12px; margin-bottom: 4px; color: #636E72;">
          Difficulty (1=Too Easy, 5=Too Hard):
        </label>
        <div style="display: flex; gap: 8px; align-items: center;">
          <input type="range" id="difficulty-rating" min="1" max="5" value="3"
                 style="flex: 1; cursor: pointer;">
          <span id="difficulty-value" style="min-width: 30px; font-weight: 700; color: #FF6B6B;">3</span>
        </div>
      </div>

      <div class="rating-group" style="margin-bottom: 10px;">
        <label style="display: block; font-size: 12px; margin-bottom: 4px; color: #636E72;">
          Clarity (1=Confusing, 5=Very Clear):
        </label>
        <div style="display: flex; gap: 8px; align-items: center;">
          <input type="range" id="clarity-rating" min="1" max="5" value="3"
                 style="flex: 1; cursor: pointer;">
          <span id="clarity-value" style="min-width: 30px; font-weight: 700; color: #74B9FF;">3</span>
        </div>
      </div>

      <div class="rating-group" style="margin-bottom: 15px;">
        <label style="display: block; font-size: 12px; margin-bottom: 4px; color: #636E72;">
          Usefulness (1=Not Helpful, 5=Very Helpful):
        </label>
        <div style="display: flex; gap: 8px; align-items: center;">
          <input type="range" id="usefulness-rating" min="1" max="5" value="3"
                 style="flex: 1; cursor: pointer;">
          <span id="usefulness-value" style="min-width: 30px; font-weight: 700; color: #55EFC4;">3</span>
        </div>
      </div>

      <div style="display: flex; gap: 8px; justify-content: center;">
        <button class="action-btn submit-feedback-btn" style="flex: 1;">
          ✅ Submit Feedback
        </button>
        <button class="action-btn skip-feedback-btn" style="flex: 1; background: linear-gradient(135deg, #DFE6E9 0%, #B2BEC3 100%);">
          ⏭️ Skip
        </button>
      </div>
    </div>
  `;

  // Attach slider event listeners
  ['difficulty', 'clarity', 'usefulness'].forEach(type => {
    const slider = document.getElementById(`${type}-rating`);
    const valueSpan = document.getElementById(`${type}-value`);
    slider.addEventListener('input', (e) => {
      valueSpan.textContent = e.target.value;
    });
  });

  // Attach button listeners
  document.querySelector('.submit-feedback-btn').addEventListener('click', submitFeedback);
  document.querySelector('.skip-feedback-btn').addEventListener('click', skipFeedback);
}

function showLegacyActions(actionsDiv) {
  actionsDiv.innerHTML = `
    <button class="action-btn regenerate-btn">🔄 Regenerate</button>
  `;
  document.querySelector('.regenerate-btn').addEventListener('click', () => {
    regenerateExample(currentTopic);
  });
}

function submitFeedback() {
  const difficulty = parseInt(document.getElementById('difficulty-rating').value);
  const clarity = parseInt(document.getElementById('clarity-rating').value);
  const usefulness = parseInt(document.getElementById('usefulness-rating').value);

  console.log('[Content] Submitting feedback:', { difficulty, clarity, usefulness });

  // Show loading state
  const actionsDiv = document.querySelector('.popup-actions');
  actionsDiv.innerHTML = `
    <div style="text-align: center; padding: 15px; color: #2D3436;">
      <div class="spinner" style="margin: 0 auto 10px;"></div>
      <span>Submitting feedback...</span>
    </div>
  `;

  // Submit to background script
  chrome.runtime.sendMessage({
    action: 'submitFeedback',
    threadId: currentThreadId,
    feedback: {
      difficulty_rating: difficulty,
      clarity_rating: clarity,
      usefulness_rating: usefulness
    }
  }, (response) => {
    if (response.success) {
      actionsDiv.innerHTML = `
        <div style="text-align: center; padding: 15px; color: #00B894; font-weight: 700;">
          ✅ ${response.message || 'Feedback submitted successfully!'}
        </div>
      `;

      // Close popup after 2 seconds
      setTimeout(() => {
        removeExistingPopup();
      }, 2000);
    } else {
      actionsDiv.innerHTML = `
        <div style="text-align: center; padding: 15px; color: #D63031; font-weight: 700;">
          ❌ Error: ${response.error || 'Failed to submit feedback'}
        </div>
      `;

      // Show retry option
      setTimeout(() => {
        showFeedbackUI(actionsDiv);
      }, 2000);
    }
  });
}

function skipFeedback() {
  console.log('[Content] User skipped feedback');
  removeExistingPopup();
}

// Updated regenerate function to work with event listeners and track struggle
function regenerateExample(topic) {
  const content = document.querySelector('.example-content');
  const loading = document.querySelector('.loading');

  if (content && loading) {
    content.style.display = 'none';
    loading.style.display = 'flex';

    // Notify background script about regeneration (indicates struggle)
    // Only in legacy mode - workflow mode handles this via feedback
    if (!workflowMode) {
      chrome.runtime.sendMessage({
        action: "recordStruggleSignal",
        topic: topic,
        signal_type: "regeneration_requested"
      });
    }

    // Clear current workflow state and regenerate
    currentThreadId = null;
    workflowMode = false;

    generateExampleForPopup(topic);
  }
}

function showFeedbackInfluenceModal(influence) {
  console.log('[Content] Showing feedback influence modal:', influence);

  // Create modal overlay
  const modal = document.createElement('div');
  modal.className = 'influence-modal';
  modal.innerHTML = `
    <div class="influence-modal-content">
      <div class="influence-header">
        <h2>📊 How Feedback Shaped This Example</h2>
        <button class="close-btn" style="margin: 0;">×</button>
      </div>
      <div class="influence-body">
        ${buildInfluenceContent(influence)}
      </div>
    </div>
  `;

  // Add to page
  document.body.appendChild(modal);

  // Close modal on background click or close button
  const closeModal = () => {
    modal.remove();
  };

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      closeModal();
    }
  });

  modal.querySelector('.close-btn').addEventListener('click', closeModal);

  // Close on escape key
  const escapeHandler = (e) => {
    if (e.key === 'Escape') {
      closeModal();
      document.removeEventListener('keydown', escapeHandler);
    }
  };
  document.addEventListener('keydown', escapeHandler);
}

function buildInfluenceContent(influence) {
  if (!influence || !influence.has_previous_feedback) {
    return `
      <div class="no-feedback-message">
        <p>📝 No previous feedback available yet.</p>
        <p>Your feedback will help personalize future examples!</p>
      </div>
    `;
  }

  let html = '';

  // Adaptations Applied
  if (influence.adaptations_applied && influence.adaptations_applied.length > 0) {
    html += `
      <div class="influence-section">
        <h3>🎯 Adaptations Applied</h3>
    `;
    influence.adaptations_applied.forEach(adaptation => {
      html += `
        <div class="influence-item">
          <div class="influence-label">${adaptation.type}</div>
          <div class="influence-value">
            <strong>Why:</strong> ${adaptation.reason}<br>
            <strong>Action:</strong> ${adaptation.action}
          </div>
        </div>
      `;
    });
    html += `</div>`;
  }

  // Recent Ratings Summary
  if (influence.recent_ratings_summary && influence.recent_ratings_summary.sample_size > 0) {
    const ratings = influence.recent_ratings_summary;
    html += `
      <div class="influence-section">
        <h3>📈 Your Recent Feedback</h3>
        <div class="influence-item">
          <div class="influence-value">
            Based on your last ${ratings.sample_size} feedback ${ratings.sample_size === 1 ? 'entry' : 'entries'}:
            <div style="margin-top: 8px;">
              <span class="adaptation-badge">Difficulty: ${ratings.average_difficulty}/5</span>
              <span class="adaptation-badge">Clarity: ${ratings.average_clarity}/5</span>
              <span class="adaptation-badge">Usefulness: ${ratings.average_usefulness}/5</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // Struggle Indicators
  if (influence.struggle_indicators && influence.struggle_indicators.is_struggling) {
    const struggle = influence.struggle_indicators;
    html += `
      <div class="influence-section">
        <h3>🆘 Struggle Detected</h3>
        <div class="influence-item">
          <div class="influence-value">
            We noticed you're working through this topic:<br>
            <strong>Repetitions:</strong> ${struggle.repeat_count} times<br>
            <strong>Regenerations:</strong> ${struggle.regeneration_count} times<br>
            <em>We've simplified the explanation to help!</em>
          </div>
        </div>
      </div>
    `;
  }

  // Mastery Indicators
  if (influence.mastery_indicators && influence.mastery_indicators.showing_mastery) {
    const mastery = influence.mastery_indicators;
    html += `
      <div class="influence-section">
        <h3>🚀 Mastery Detected</h3>
        <div class="influence-item">
          <div class="influence-value">
            Great progress! You've explored ${mastery.unique_topic_count} different topics recently:
            <div style="margin-top: 8px;">
              ${mastery.recent_topics.map(t => `<span class="adaptation-badge">${t}</span>`).join(' ')}
            </div>
            <em>We've increased complexity to match your growing skills!</em>
          </div>
        </div>
      </div>
    `;
  }

  // Topic-Specific Feedback History
  if (influence.topic_feedback_history && influence.topic_feedback_history.length > 0) {
    html += `
      <div class="influence-section">
        <h3>📚 Previous Feedback on This Topic</h3>
    `;
    influence.topic_feedback_history.forEach((item, index) => {
      html += `
        <div class="influence-item">
          <div class="influence-label">Attempt #${index + 1}</div>
          <div class="influence-value">
            <span class="adaptation-badge">Difficulty: ${item.difficulty}/5</span>
            <span class="adaptation-badge">Clarity: ${item.clarity}/5</span>
            <span class="adaptation-badge">Usefulness: ${item.usefulness}/5</span>
          </div>
        </div>
      `;
    });
    html += `</div>`;
  }

  // Threshold Information
  if (influence.threshold_info) {
    const thresholds = influence.threshold_info;
    html += `
      <div class="influence-section">
        <h3>⚙️ Current Settings</h3>
        <div class="influence-item">
          <div class="influence-value">
            <strong>Struggle Threshold:</strong> ${thresholds.struggle_threshold} repetitions<br>
            <strong>Mastery Threshold:</strong> ${thresholds.mastery_threshold} unique topics<br>
            <small style="color: #636E72;">These thresholds adjust automatically based on your feedback!</small>
          </div>
        </div>
      </div>
    `;
  }

  return html;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Clean up on page unload
window.addEventListener('beforeunload', removeExistingPopup);