// Background script for ExaCraft AI Example Generator Extension

// Create context menu when extension is installed
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "generateExample",
    title: "Generate AI Example for '%s'",
    contexts: ["selection"]
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "generateExample") {
    const selectedText = info.selectionText;
    chrome.tabs.sendMessage(tab.id, {
      action: "showExamplePopup",
      topic: selectedText
    });
  }
});

// Handle messages from content script and popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "generateExample") {
    generateExample(request.topic)
      .then(response => sendResponse(response))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === "submitFeedback") {
    submitFeedback(request.threadId, request.feedback)
      .then(response => sendResponse(response))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === "saveUserProfile") {
    chrome.storage.local.set({ userProfile: request.profile }, () => {
      sendResponse({ success: true });
    });
    return true;
  }

  if (request.action === "getUserProfile") {
    chrome.storage.local.get("userProfile", (result) => {
      sendResponse({ profile: result.userProfile });
    });
    return true;
  }
});

// Generate example using the workflow endpoint (always workflow-based)
async function generateExample(topic) {
  try {
    const result = await chrome.storage.local.get(["userProfile", "llmProvider"]);
    const userProfile = result.userProfile || {};
    const llmProvider = result.llmProvider || 'gemini';

    const user_id = userProfile.name
      ? userProfile.name.toLowerCase().replace(/\s+/g, '_')
      : 'anonymous_user';

    const response = await fetch('http://localhost:8000/workflows/feedback/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: user_id,
        topic: topic,
        mode: 'adaptive',
        provider: llmProvider
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (!data.generated_example) {
      throw new Error('No example generated. Check API logs.');
    }

    return {
      success: true,
      example: data.generated_example,
      threadId: data.thread_id,
      topic: topic
    };

  } catch (error) {
    console.error('Error generating example:', error);
    return {
      success: false,
      example: `**Topic: ${topic}**\n\nAPI not available. Please ensure your Python server is running on localhost:8000.\n\nTo start the server, run:\npython api_server.py`,
    };
  }
}

// Submit natural-language feedback and resume workflow.
// If the Adaptive Response Agent triggered regeneration, returns the new example
// with status: "awaiting_feedback" so content.js can display it.
async function submitFeedback(threadId, feedback) {
  try {
    const response = await fetch(`http://localhost:8000/workflows/${threadId}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_feedback_text: feedback.user_feedback_text || ""
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    // Pass the full API response back — content.js handles both
    // status: "completed" and status: "awaiting_feedback" (regeneration loop)
    return {
      success: data.success,
      status: data.status,
      generated_example: data.generated_example || null,
      example_id: data.example_id || null,
      loop_count: data.loop_count || 0,
      thread_id: data.thread_id || threadId,
      message: data.message || ''
    };

  } catch (error) {
    console.error('Error submitting feedback:', error);
    return { success: false, error: error.message };
  }
}
