// Content script for ExaCraft AI Example Generator Extension

let currentSelection = null;
let popupElement = null;
let currentThreadId = null;
let currentTopic = null;

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "showExamplePopup") {
    showExamplePopup(request.topic);
    sendResponse({ success: true });
  }
});

// ─── Selection Tracking ────────────────────────────────────────────────────────

function storeSelectionInfo() {
  const selection = window.getSelection();
  if (selection.rangeCount > 0) {
    const range = selection.getRangeAt(0);
    currentSelection = {
      range: range.cloneRange(),
      text: selection.toString(),
      initialRect: range.getBoundingClientRect()
    };
  }
}

function isSelectionVisible() {
  if (!currentSelection) return false;
  try {
    const rect = currentSelection.range.getBoundingClientRect();
    const tolerance = 50;
    return !(rect.bottom < -tolerance || rect.top > window.innerHeight + tolerance ||
             rect.right < -tolerance || rect.left > window.innerWidth + tolerance);
  } catch (e) {
    return false;
  }
}

// ─── Popup Lifecycle ───────────────────────────────────────────────────────────

function showExamplePopup(topic) {
  storeSelectionInfo();
  removeExistingPopup();

  const popup = document.createElement('div');
  popup.id = 'ai-example-popup';
  popup.innerHTML = `
    <div class="popup-header">
      <h3>🤖 ExaCraft</h3>
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
      <div class="popup-actions"></div>
    </div>
  `;

  addPopupStyles();
  positionPopup(popup);
  document.body.appendChild(popup);
  popupElement = popup;

  popup.querySelector('.close-btn').addEventListener('click', removeExistingPopup);
  setupDynamicPositioning();
  generateExampleForPopup(topic);
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
}

// ─── Generate & Display ────────────────────────────────────────────────────────

function generateExampleForPopup(topic) {
  currentTopic = topic;

  chrome.runtime.sendMessage({ action: "generateExample", topic: topic }, (response) => {
    const popup = document.getElementById('ai-example-popup');
    if (!popup) return;

    const loading = popup.querySelector('.loading');
    const content = popup.querySelector('.example-content');
    const actionsDiv = popup.querySelector('.popup-actions');

    loading.style.display = 'none';
    content.style.display = 'block';

    if (response.success && response.example) {
      content.textContent = response.example;
      content.className = 'example-content';
      currentThreadId = response.threadId || null;

      if (currentThreadId) {
        showFeedbackUI(actionsDiv);
      } else {
        showRegenerateAction(actionsDiv);
      }
    } else {
      content.textContent = response.example || `Error: ${response.error || 'Unknown error'}`;
      content.className = 'error-content';
      showRegenerateAction(actionsDiv);
    }

    setTimeout(() => updatePopupPosition(), 100);
  });
}

// ─── Feedback UI ───────────────────────────────────────────────────────────────

function showFeedbackUI(actionsDiv) {
  actionsDiv.innerHTML = `
    <div class="feedback-section">
      <div style="text-align: center; margin-bottom: 10px;">
        <strong style="color: #2D3436; font-size: 14px;">💬 What did you think?</strong>
      </div>
      <textarea id="user-feedback-text"
        placeholder="e.g. 'Too abstract' · 'Perfect!' · 'Use a medical example' · 'Too easy'"
        style="width: 100%; padding: 10px; border: 2px solid #2D3436; border-radius: 8px;
               font-size: 13px; font-family: inherit; resize: vertical; min-height: 65px;
               box-sizing: border-box; background: #FFFEF9; margin-bottom: 10px;"></textarea>
      <div style="display: flex; gap: 8px;">
        <button class="action-btn submit-feedback-btn" style="flex: 1;">✅ Submit</button>
        <button class="action-btn skip-feedback-btn"
                style="flex: 1; background: linear-gradient(135deg, #DFE6E9 0%, #B2BEC3 100%);">
          ⏭️ Skip
        </button>
      </div>
    </div>
  `;
  actionsDiv.querySelector('.submit-feedback-btn').addEventListener('click', submitFeedback);
  actionsDiv.querySelector('.skip-feedback-btn').addEventListener('click', skipFeedback);
}

function showRegenerateAction(actionsDiv) {
  actionsDiv.innerHTML = `<button class="action-btn regenerate-btn">🔄 Regenerate</button>`;
  actionsDiv.querySelector('.regenerate-btn').addEventListener('click', () => {
    regenerateExample(currentTopic);
  });
}

// ─── Feedback Submission ───────────────────────────────────────────────────────

function submitFeedback() {
  const feedbackText = document.getElementById('user-feedback-text').value.trim();
  const actionsDiv = document.querySelector('.popup-actions');

  // Show loading
  actionsDiv.innerHTML = `
    <div style="text-align: center; padding: 15px; color: #2D3436;">
      <div class="spinner" style="margin: 0 auto 10px;"></div>
      <span style="font-size: 13px;">Processing your feedback...</span>
    </div>
  `;

  chrome.runtime.sendMessage({
    action: 'submitFeedback',
    threadId: currentThreadId,
    feedback: { user_feedback_text: feedbackText }
  }, (response) => {
    if (!response) {
      showFeedbackError(actionsDiv, 'No response from background script.');
      return;
    }

    if (response.success) {
      if (response.status === 'awaiting_feedback') {
        // Adaptive Response Agent triggered regeneration — show new example
        handleRegeneratedExample(response);
      } else {
        // Completed
        actionsDiv.innerHTML = `
          <div style="text-align: center; padding: 15px; color: #00B894; font-weight: 700;">
            ✅ Thanks! Your feedback is shaping future examples.
          </div>
        `;
        setTimeout(removeExistingPopup, 2500);
      }
    } else {
      showFeedbackError(actionsDiv, response.error || 'Failed to submit feedback.');
    }
  });
}

function handleRegeneratedExample(response) {
  // Agent decided to regenerate — update popup with new example
  const popup = document.getElementById('ai-example-popup');
  if (!popup) return;

  const content = popup.querySelector('.example-content');
  const actionsDiv = popup.querySelector('.popup-actions');

  // Update thread_id if returned (same thread, just update reference)
  if (response.thread_id) currentThreadId = response.thread_id;

  // Show regeneration notice briefly, then display new example
  if (content && response.generated_example) {
    content.textContent = response.generated_example;
    content.className = 'example-content';
  }

  const loopCount = response.loop_count || 1;
  actionsDiv.innerHTML = `
    <div style="text-align: center; padding: 8px; color: #6C5CE7; font-size: 12px;
                font-weight: 700; margin-bottom: 8px;">
      🔄 Example updated based on your feedback (attempt ${loopCount})
    </div>
  `;

  setTimeout(() => {
    showFeedbackUI(actionsDiv);
  }, 1200);
}

function skipFeedback() {
  // Submit empty string — agent will accept with "user skipped" insight
  const actionsDiv = document.querySelector('.popup-actions');
  actionsDiv.innerHTML = `
    <div style="text-align: center; padding: 15px; color: #636E72; font-size: 13px;">
      <div class="spinner" style="margin: 0 auto 10px;"></div>
      <span>Closing...</span>
    </div>
  `;
  chrome.runtime.sendMessage({
    action: 'submitFeedback',
    threadId: currentThreadId,
    feedback: { user_feedback_text: '' }
  }, () => {
    removeExistingPopup();
  });
}

function showFeedbackError(actionsDiv, message) {
  actionsDiv.innerHTML = `
    <div style="text-align: center; padding: 12px; color: #D63031; font-weight: 700; font-size: 13px;">
      ❌ ${escapeHtml(message)}
    </div>
  `;
  setTimeout(() => showFeedbackUI(actionsDiv), 2500);
}

// ─── Regenerate (manual, no thread) ───────────────────────────────────────────

function regenerateExample(topic) {
  const popup = document.getElementById('ai-example-popup');
  if (!popup) return;

  const content = popup.querySelector('.example-content');
  const loading = popup.querySelector('.loading');

  if (content && loading) {
    content.style.display = 'none';
    loading.style.display = 'flex';
    currentThreadId = null;
    generateExampleForPopup(topic);
  }
}

// ─── Positioning ───────────────────────────────────────────────────────────────

function positionPopup(popup) {
  popup.style.position = 'fixed';
  popup.style.top = '50%';
  popup.style.left = '50%';
  popup.style.transform = 'translate(-50%, -50%)';
}

function updatePopupPosition() {
  if (!popupElement || !currentSelection) return;
  if (!isSelectionVisible()) { removeExistingPopup(); return; }
  positionPopup(popupElement);
}

function setupDynamicPositioning() {
  removeDynamicPositioning();
  let scrollTimeout, resizeTimeout;
  window.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(updatePopupPosition, 50);
  }, { passive: true });
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(updatePopupPosition, 100);
  });
}

function removeDynamicPositioning() {
  if (popupElement && popupElement._scrollHandler) {
    window.removeEventListener('scroll', popupElement._scrollHandler);
    window.removeEventListener('resize', popupElement._resizeHandler);
  }
}

// ─── Styles ────────────────────────────────────────────────────────────────────

function addPopupStyles() {
  if (document.getElementById('ai-example-styles')) return;

  const styles = document.createElement('style');
  styles.id = 'ai-example-styles';
  styles.textContent = `
    @import url('https://fonts.googleapis.com/css2?family=Bubblegum+Sans&family=Comic+Neue:wght@400;700&display=swap');

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
      box-shadow: 6px 6px 0 rgba(255,193,7,0.4), 0 10px 40px rgba(0,0,0,0.3);
      z-index: 10000;
      font-family: 'Comic Neue', 'Comic Sans MS', cursive;
      font-size: 14px;
      line-height: 1.5;
      overflow: hidden;
      border: 4px solid #2D3436;
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
    }

    .popup-header h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      font-family: 'Bubblegum Sans', cursive;
    }

    .close-btn {
      background: #FF6B6B;
      border: 3px solid #2D3436;
      color: #2D3436;
      font-size: 20px;
      font-weight: 700;
      cursor: pointer;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
      box-shadow: 3px 3px 0 rgba(0,0,0,0.2);
    }

    .close-btn:hover { transform: scale(1.1) rotate(5deg); }

    .popup-content {
      flex-grow: 1;
      padding: 20px;
      overflow-y: auto;
      min-height: 0;
    }

    .topic-section {
      margin-bottom: 15px;
      padding: 12px;
      background: linear-gradient(135deg, #E3F2FD 0%, #FFF9C4 100%);
      border-radius: 10px 3px 10px 3px;
      border: 3px solid #2D3436;
      box-shadow: 3px 3px 0 rgba(0,0,0,0.1);
    }

    .topic-section strong { color: #FF6B6B; font-family: 'Bubblegum Sans', cursive; }

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

    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

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
      box-shadow: 4px 4px 0 rgba(40,167,69,0.3);
      margin-bottom: 12px;
    }

    .error-content {
      background: linear-gradient(135deg, #FFB8B8 0%, #FFA8A8 100%);
      color: #D63031;
      padding: 15px;
      border-radius: 12px 4px 12px 4px;
      border: 3px solid #2D3436;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-weight: 600;
      margin-bottom: 12px;
    }

    .popup-actions { margin-top: 4px; }

    .feedback-section {
      background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
      padding: 15px;
      border-radius: 12px 4px 12px 4px;
      border: 3px solid #2D3436;
      box-shadow: 3px 3px 0 rgba(0,0,0,0.1);
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
      box-shadow: 4px 4px 0 rgba(0,0,0,0.2);
      width: 100%;
    }

    .action-btn:hover { transform: translateY(-2px); box-shadow: 6px 6px 0 rgba(0,0,0,0.2); }
    .action-btn:active { transform: translateY(2px); box-shadow: 2px 2px 0 rgba(0,0,0,0.2); }

    .regenerate-btn { background: linear-gradient(135deg, #74B9FF 0%, #A29BFE 100%); }
    .submit-feedback-btn { background: linear-gradient(135deg, #55EFC4 0%, #81ECEC 100%) !important; }

    @media (max-width: 480px) {
      #ai-example-popup { width: 95vw; max-height: 85vh; }
    }
  `;
  document.head.appendChild(styles);
}

// ─── Utilities ─────────────────────────────────────────────────────────────────

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

window.addEventListener('beforeunload', removeExistingPopup);
