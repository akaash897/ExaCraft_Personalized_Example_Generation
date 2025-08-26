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
  console.log("Context menu clicked:", info);
  if (info.menuItemId === "generateExample") {
    const selectedText = info.selectionText;
    console.log("Selected text:", selectedText);
    
    // Send message to content script to show popup
    chrome.tabs.sendMessage(tab.id, {
      action: "showExamplePopup",
      topic: selectedText
    }, (response) => {
      console.log("Message sent to content script, response:", response);
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
  
  if (request.action === "beginLearningSession") {
    console.log("Learning session started");
    
    // Get user profile and start session via API
    chrome.storage.local.get("userProfile", async (result) => {
      const userProfile = result.userProfile || {};
      const user_id = userProfile.name ? 
        userProfile.name.toLowerCase().replace(/\s+/g, '_') : 
        'anonymous_user';
      
      try {
        const response = await fetch('http://localhost:8000/start-learning-session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ user_id: user_id })
        });
        
        const data = await response.json();
        console.log('Session started:', data);
      } catch (error) {
        console.warn('Failed to start session via API:', error);
      }
    });
    
    sendResponse({ success: true });
    return true;
  }
  
  if (request.action === "endLearningSession") {
    console.log("Learning session ended");
    
    // Get user profile and end session via API
    chrome.storage.local.get("userProfile", async (result) => {
      const userProfile = result.userProfile || {};
      const user_id = userProfile.name ? 
        userProfile.name.toLowerCase().replace(/\s+/g, '_') : 
        'anonymous_user';
      
      try {
        const response = await fetch('http://localhost:8000/end-learning-session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ user_id: user_id })
        });
        
        const data = await response.json();
        console.log('Session ended:', data);
      } catch (error) {
        console.warn('Failed to end session via API:', error);
      }
    });
    
    sendResponse({ success: true });
    return true;
  }
  
  if (request.action === "recordStruggleSignal") {
    console.log("Struggle signal recorded:", request.topic, request.signal_type);
    
    // Send struggle signal to API
    chrome.storage.local.get("userProfile", async (result) => {
      const userProfile = result.userProfile || {};
      const user_id = userProfile.name ? 
        userProfile.name.toLowerCase().replace(/\s+/g, '_') : 
        'anonymous_user';
      
      try {
        await fetch('http://localhost:8000/record-struggle-signal', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            topic: request.topic,
            user_id: user_id,
            signal_type: request.signal_type
          })
        });
      } catch (error) {
        console.warn('Failed to record struggle signal:', error);
      }
    });
    
    sendResponse({ success: true });
    return true;
  }
});

// Function to generate example with dynamic learning context
async function generateExample(topic) {
  try {
    // Get user profile from storage
    const result = await chrome.storage.local.get("userProfile");
    const userProfile = result.userProfile || {};
    
    // Generate user_id from profile name or use anonymous
    const user_id = userProfile.name ? 
      userProfile.name.toLowerCase().replace(/\s+/g, '_') : 
      'anonymous_user';
    
    // Call the adaptive API endpoint
    const response = await fetch('http://localhost:8000/generate-adaptive-example', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        topic: topic,
        user_profile: userProfile,
        user_id: user_id
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Log learning context for debugging (can be removed in production)
    if (data.learning_context) {
      console.log('Learning context:', data.learning_context);
    }
    
    return data.example;
    
  } catch (error) {
    console.error('Error generating example:', error);
    
    // Fallback to a simple example if API is not available
    return `**Topic: ${topic}**\n\nAPI not available. Please ensure your Python server is running on localhost:8000.\n\nTo start the server, run:\npython api_server.py`;
  }
}