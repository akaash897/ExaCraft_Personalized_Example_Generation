// Background script for AI Example Generator Extension

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
    
    // Send message to content script to show popup
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
      .then(example => {
        sendResponse({ success: true, example: example });
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });
    
    return true; // Keep message channel open for async response
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

// Function to generate example by calling your local API
async function generateExample(topic) {
  try {
    // Get user profile from storage
    const result = await chrome.storage.local.get("userProfile");
    const userProfile = result.userProfile || {};
    
    // Call your local Python API
    const response = await fetch('http://localhost:8000/generate-example', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        topic: topic,
        user_profile: userProfile
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.example;
    
  } catch (error) {
    console.error('Error generating example:', error);
    
    // Fallback to a simple example if API is not available
    return `**Topic: ${topic}**\n\nAPI not available. Please ensure your Python server is running on localhost:8000.\n\nTo start the server, run:\npython api_server.py`;
  }
}