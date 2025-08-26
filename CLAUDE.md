# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AI Example Generator with Dynamic Learning Context Adaptation** project consisting of three main components:
1. **Browser Extension** (Chrome/Manifest V3) - Frontend interface for users with behavioral analytics
2. **Python Flask API Server** - Backend service with dynamic learning context tracking using Google Gemini AI
3. **CLI Application** - Command-line interface for direct interaction

The system generates personalized examples that adapt dynamically based on user behavior patterns, going beyond static personalization to track learning progress, struggle indicators, and mastery signals through real-time behavioral analytics.

## Architecture

### Core Components

- **`core/example_generator.py`** - Main business logic with `ExampleGenerator`, `UserProfile`, and `LearningContext` classes
- **`api_server.py`** - Flask REST API server with 10+ endpoints for dynamic learning context management
- **`cli_app.py`** - Interactive command-line application
- **Extension files** - `manifest.json`, `background.js`, `content.js`, `popup.html/js` with behavioral tracking
- **`learning_contexts/`** - Directory storing dynamic learning context JSON files per user
- **`user_profiles/`** - Directory storing user profile JSON files for CLI mode

### Dynamic Learning Context Architecture

The system implements **5 categories of dynamic learning context**:
1. **Recent Topic History** - Timestamped topic interactions with session tracking
2. **Struggle Indicators** - Topic repetition patterns (≥3x) and regeneration button clicks
3. **Mastery Signals** - Quick progression through diverse topics (≥3 different topics)
4. **Session Management** - Learning session boundaries with cross-session continuity
5. **Behavioral Signal Integration** - Multi-signal analysis for adaptive content generation

### Enhanced Data Flow

1. User highlights text → Context menu triggers extension → Background script processes
2. Extension calls `/generate-adaptive-example` with topic, profile, and user_id
3. API loads `LearningContext` from `learning_contexts/{user_id}.json`
4. System analyzes behavioral patterns and adapts prompt engineering accordingly
5. Gemini AI generates context-aware example using dynamic adaptation rules
6. Learning context updated with new interaction data and behavioral signals
7. Generated example displayed in popup with regeneration tracking

### Dual Profile System

**User Profiles** support two modes:
- **API Mode**: Profile data passed directly in requests (extension usage)
- **CLI Mode**: Profiles stored as JSON files in `user_profiles/` directory
- **Sync Mode**: Extension profiles can sync to CLI files via `/sync-profile` endpoint

**Learning Contexts** are user-specific and persistent:
- Stored in `learning_contexts/{user_id}.json`
- Track behavioral patterns across sessions
- Automatically clean entries older than 7 days
- Support session start/end lifecycle management

## Development Commands

### Python Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Create .env file with:
GEMINI_API_KEY=your_api_key_here
```

### Running the Application

**Start API Server:**
```bash
python api_server.py
# Runs on http://localhost:8000
```

**Run CLI Application:**
```bash
python cli_app.py
```

**Load Browser Extension:**
1. Open Chrome → Extensions → Developer mode
2. Click "Load unpacked" and select this directory
3. Ensure API server is running on localhost:8000

### Testing

**Test API Health:**
```bash
curl http://localhost:8000/health
```

**Test Static Example Generation:**
```bash
curl -X POST http://localhost:8000/generate-example \
  -H "Content-Type: application/json" \
  -d '{"topic": "machine learning", "user_profile": {"education": "graduate", "profession": "Data Scientist"}}'
```

**Test Dynamic Adaptive Example Generation:**
```bash
curl -X POST http://localhost:8000/generate-adaptive-example \
  -H "Content-Type: application/json" \
  -d '{"topic": "machine learning", "user_profile": {"education": "graduate", "profession": "Data Scientist"}, "user_id": "test_user"}'
```

**Test Learning Context Management:**
```bash
# Start learning session
curl -X POST http://localhost:8000/start-learning-session \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'

# Get learning context
curl "http://localhost:8000/get-learning-context?user_id=test_user"

# Record struggle signal
curl -X POST http://localhost:8000/record-struggle-signal \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "topic": "neural networks", "signal_type": "regeneration_requested"}'

# End learning session
curl -X POST http://localhost:8000/end-learning-session \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'
```

**Test Extension with Behavioral Analytics:**
1. Highlight text on any webpage
2. Right-click → "Generate AI Example for '[text]'"
3. View generated example in popup
4. Click "🔄 Regenerate" button to record struggle signal
5. Try different topics to trigger mastery detection
6. Use popup to start/end learning sessions

## Configuration

### Environment Variables
- `GEMINI_API_KEY` - Required Google Gemini API key for AI generation

### API Endpoints

**Core Generation:**
- `GET /health` - Health check and service info
- `POST /generate-example` - Generate static personalized example
- `POST /generate-adaptive-example` - Generate dynamically adaptive example with learning context
- `GET /test-example` - Test endpoint with sample data
- `GET /api-info` - API documentation

**Dynamic Learning Context Management:**
- `GET /get-learning-context?user_id={id}` - Retrieve user's learning context data
- `POST /record-struggle-signal` - Record behavioral struggle signals
- `POST /start-learning-session` - Start new learning session for user
- `POST /end-learning-session` - End current learning session
- `GET /get-session-status?user_id={id}` - Get current session status

**Profile Management:**
- `POST /validate-profile` - Validate user profile data structure
- `POST /sync-profile` - Sync extension profile to CLI file system

### User Profile Fields
- `name` - User's name (also used to generate user_id for learning context)
- `location` - Geographic location (string or object with city/country)
- `education` - Education level (high_school, undergraduate, graduate, professional)
- `profession` - Job title/profession
- `complexity` - Preferred example complexity (simple, medium, advanced)
- `cultural_background` - Cultural context for examples

### Learning Context Data Structure
Each user's learning context (`learning_contexts/{user_id}.json`) contains:
- `recent_topics[]` - Array of recent topic interactions with timestamps
- `struggle_indicators{}` - Topics with repetition counts and struggle signals
- `mastery_indicators{}` - Quick progression patterns and successful topics
- `session_history[]` - Past learning sessions with duration and topics
- `current_session{}` - Active session data (if any) with real-time tracking

## Extension Development

The extension uses Manifest V3 with behavioral analytics integration:
- **Service Worker** (`background.js`) - Handles API calls, context menus, and learning context management
- **Content Script** (`content.js`) - Manages popup display, positioning, and regeneration tracking
- **Popup** (`popup.html/js`) - User profile management and learning session controls

### Behavioral Analytics Features
- **Regeneration Tracking** - "🔄 Regenerate" button sends struggle signals to API
- **Session Management** - Start/end learning sessions via extension popup
- **Automatic User ID Generation** - Uses profile name to create consistent user_id
- **Context Menu Integration** - Right-click highlighted text triggers adaptive generation
- **Error Handling** - Graceful fallback when API server unavailable

### Extension Permissions
- `activeTab` - Access to current tab content
- `contextMenus` - Right-click context menu integration
- `storage` - User profile storage
- `http://localhost:*/*` - Local API server communication

## File Structure Conventions

- **Core Logic**: Place business logic in `core/` directory
- **User Profiles**: CLI profiles stored in `user_profiles/*.json`
- **Learning Contexts**: Dynamic learning data in `learning_contexts/*.json`
- **Extension Assets**: HTML/JS/CSS files in root for extension packaging
- **Python Modules**: Use descriptive imports and proper error handling

### Key Files and Directories
```
├── core/
│   └── example_generator.py          # Main logic with LearningContext class
├── learning_contexts/                # User learning context storage
│   ├── shyam.json                   # Example user context
│   └── {user_id}.json               # Per-user learning data
├── user_profiles/                   # CLI profile storage
│   └── {user_id}.json               # Per-user profile data
├── api_server.py                    # Flask API with 10+ endpoints
├── background.js                    # Extension service worker
├── content.js                       # Extension content script
└── popup.html/js                    # Extension popup interface
```

## Behavioral Learning Analytics Implementation

### Struggle Detection Logic
- Topic repetition ≥3 times triggers struggle indicator
- Regeneration button clicks recorded as explicit struggle signals
- Struggle indicators stored with timestamps and signal types

### Mastery Detection Logic
- Quick progression through ≥3 different topics indicates mastery
- Mastery patterns influence prompt complexity increases
- Mastery data includes recent topic arrays and timestamps

### Session Lifecycle Management
- Sessions have unique IDs with start/end timestamps
- Cross-session learning continuity maintained via persistent storage
- Session data includes topic progression and struggle signals
- Old entries automatically cleaned after 7 days

## Error Handling

- API endpoints return consistent JSON format with `success` boolean
- CLI application provides user-friendly error messages
- Extension includes fallback behavior when API is unavailable
- Profile validation ensures data integrity across components
- Learning context files have robust error handling and default creation
- Comprehensive logging for behavioral analytics debugging