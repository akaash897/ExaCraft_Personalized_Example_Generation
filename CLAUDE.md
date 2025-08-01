# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AI Example Generator** project consisting of three main components:
1. **Browser Extension** (Chrome/Manifest V3) - Frontend interface for users
2. **Python Flask API Server** - Backend service that generates examples using Google Gemini AI
3. **CLI Application** - Command-line interface for direct interaction

The system generates personalized examples for any topic by leveraging user profile information and Google's Gemini AI model through LangChain.

## Architecture

### Core Components

- **`core/example_generator.py`** - Main business logic containing `ExampleGenerator` class and `UserProfile` management
- **`api_server.py`** - Flask REST API server with endpoints for extension communication
- **`cli_app.py`** - Interactive command-line application
- **Extension files** - `manifest.json`, `background.js`, `content.js`, `popup.html/js`

### Data Flow

1. User highlights text on webpage → Context menu triggers extension
2. Extension calls `/generate-example` API endpoint with topic and user profile
3. API server uses `ExampleGenerator` to create personalized example via Gemini AI
4. Generated example displayed in extension popup

### User Profile System

Profiles support two modes:
- **API Mode**: Profile data passed directly in requests (extension usage)
- **CLI Mode**: Profiles stored as JSON files in `user_profiles/` directory

Profile structure includes: name, location, education, profession, complexity preference, cultural background.

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

**Test Example Generation:**
```bash
curl -X POST http://localhost:8000/generate-example \
  -H "Content-Type: application/json" \
  -d '{"topic": "machine learning", "user_profile": {"education": "graduate", "profession": "Data Scientist"}}'
```

**Test Extension:**
1. Highlight text on any webpage
2. Right-click → "Generate AI Example for '[text]'"
3. View generated example in popup

## Configuration

### Environment Variables
- `GEMINI_API_KEY` - Required Google Gemini API key for AI generation

### API Endpoints
- `GET /health` - Health check and service info
- `POST /generate-example` - Generate personalized example
- `POST /validate-profile` - Validate user profile data
- `GET /test-example` - Test endpoint with sample data
- `GET /api-info` - API documentation

### User Profile Fields
- `name` - User's name
- `location` - Geographic location (string or object with city/country)
- `education` - Education level (high_school, undergraduate, graduate, professional)
- `profession` - Job title/profession
- `complexity` - Preferred example complexity (simple, medium, advanced)
- `cultural_background` - Cultural context for examples

## Extension Development

The extension uses Manifest V3 with:
- **Service Worker** (`background.js`) - Handles API calls and context menus
- **Content Script** (`content.js`) - Manages popup display and positioning
- **Popup** (`popup.html/js`) - User profile management interface

### Extension Permissions
- `activeTab` - Access to current tab content
- `contextMenus` - Right-click context menu integration
- `storage` - User profile storage
- `http://localhost:*/*` - Local API server communication

## File Structure Conventions

- **Core Logic**: Place business logic in `core/` directory
- **User Profiles**: CLI profiles stored in `user_profiles/*.json`
- **Extension Assets**: HTML/JS/CSS files in root for extension packaging
- **Python Modules**: Use descriptive imports and proper error handling

## Error Handling

- API endpoints return consistent JSON format with `success` boolean
- CLI application provides user-friendly error messages
- Extension includes fallback behavior when API is unavailable
- Profile validation ensures data integrity across components