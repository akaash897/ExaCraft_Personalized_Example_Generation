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
      .then(response => {
        sendResponse(response);
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });

    return true; // Keep message channel open for async response
  }

  if (request.action === "submitFeedback") {
    submitFeedback(request.threadId, request.feedback)
      .then(response => {
        sendResponse(response);
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });

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
// Supports both legacy and workflow-based generation
async function generateExample(topic) {
  try {
    // Get user profile, feature flags, and provider settings from storage
    const result = await chrome.storage.local.get(["userProfile", "feedbackWorkflowEnabled", "llmProvider"]);
    const userProfile = result.userProfile || {};
    const feedbackWorkflowEnabled = result.feedbackWorkflowEnabled || false;
    const llmProvider = result.llmProvider || 'gemini';

    // Generate user_id from profile name or use anonymous
    const user_id = userProfile.name ?
      userProfile.name.toLowerCase().replace(/\s+/g, '_') :
      'anonymous_user';

    // Choose endpoint based on feature flag
    if (feedbackWorkflowEnabled) {
      // NEW: Use workflow-based generation with human-in-the-loop
      console.log('[Workflow Mode] Starting feedback workflow for topic:', topic);
      const response = await fetch('http://localhost:8000/workflows/feedback/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
      console.log('[Workflow Mode] Workflow started:', data);

      // Check if example was generated
      if (!data.generated_example) {
        console.error('[Workflow Mode] No example in response:', data);
        throw new Error('No example generated. Check API logs.');
      }

      // Return workflow response with thread_id for feedback submission
      return {
        success: true,
        example: data.generated_example,
        threadId: data.thread_id,
        feedbackInfluence: data.feedback_influence || null,
        workflowMode: true,
        topic: topic
      };

    } else {
      // LEGACY: Use direct generation without feedback
      console.log('[Legacy Mode] Generating example for topic:', topic);
      const response = await fetch('http://localhost:8000/generate-adaptive-example', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic: topic,
          user_profile: userProfile,
          user_id: user_id,
          provider: llmProvider
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Log learning context for debugging
      if (data.learning_context) {
        console.log('Learning context:', data.learning_context);
      }

      // Log feedback influence for debugging
      if (data.feedback_influence) {
        console.log('Feedback influence:', data.feedback_influence);
      }

      return {
        success: true,
        example: data.example,
        feedbackInfluence: data.feedback_influence || null,
        workflowMode: false
      };
    }

  } catch (error) {
    console.error('Error generating example:', error);

    // Fallback to a simple error message
    return {
      success: false,
      example: `**Topic: ${topic}**\n\nAPI not available. Please ensure your Python server is running on localhost:8000.\n\nTo start the server, run:\npython api_server.py`,
      workflowMode: false
    };
  }
}

// Function to submit feedback and resume workflow
async function submitFeedback(threadId, feedback) {
  try {
    console.log('[Workflow Mode] Submitting feedback for thread:', threadId, feedback);

    const response = await fetch(`http://localhost:8000/workflows/${threadId}/resume`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        difficulty_rating: feedback.difficulty_rating,
        clarity_rating: feedback.clarity_rating,
        usefulness_rating: feedback.usefulness_rating
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('[Workflow Mode] Feedback submitted successfully:', data);

    return {
      success: true,
      message: 'Feedback recorded! Your learning context has been updated.'
    };

  } catch (error) {
    console.error('Error submitting feedback:', error);
    return {
      success: false,
      error: error.message
    };
  }
}