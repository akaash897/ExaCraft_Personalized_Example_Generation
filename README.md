# Dynamic Learning Context Adaptation for Personalized Example Generation

This repository contains the implementation for an adaptive example generation system that dynamically personalizes content based on user behavior patterns and learning context.

## System Architecture

The system consists of three main components:

1. **Browser Extension** (Chrome/Manifest V3) - Frontend interface with behavioral analytics
2. **Python Flask API Server** - Backend service with dynamic learning context tracking
3. **CLI Application** - Command-line interface for direct interaction

## Key Features

- **Dynamic Learning Context Adaptation**: Tracks user learning patterns and adapts content complexity in real-time
- **Behavioral Analytics**: Monitors struggle indicators, mastery signals, and learning progression
- **Multi-modal Interface**: Browser extension, web API, and command-line interface
- **Persistent Learning Context**: Maintains user learning history across sessions

## Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup**
   Create a `.env` file with your API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

### API Server
```bash
python api_server.py
```
The server runs on http://localhost:8000

### CLI Application
```bash
python cli_app.py
```

### Browser Extension
1. Open Chrome → Extensions → Developer mode
2. Click "Load unpacked" and select this directory
3. Ensure API server is running on localhost:8000

## Core Components

- **`api_server.py`** - Flask REST API with 10+ endpoints for dynamic learning context management
- **`cli_app.py`** - Interactive command-line application
- **`core/example_generator.py`** - Main business logic with ExampleGenerator, UserProfile, and LearningContext classes
- **Extension files** - `manifest.json`, `background.js`, `content.js`, `popup.html/js` with behavioral tracking

## API Endpoints

- `GET /health` - Health check
- `POST /generate-example` - Generate static personalized example
- `POST /generate-adaptive-example` - Generate dynamically adaptive example
- `GET /get-learning-context` - Retrieve user learning context
- `POST /record-struggle-signal` - Record behavioral struggle signals
- `POST /start-learning-session` - Start new learning session
- `POST /end-learning-session` - End current learning session

## Dynamic Learning Context

The system implements 5 categories of dynamic learning context:

1. **Recent Topic History** - Timestamped topic interactions with session tracking
2. **Struggle Indicators** - Topic repetition patterns (≥3x) and regeneration button clicks
3. **Mastery Signals** - Quick progression through diverse topics (≥3 different topics)
4. **Session Management** - Learning session boundaries with cross-session continuity
5. **Behavioral Signal Integration** - Multi-signal analysis for adaptive content generation

## File Structure

```
├── core/
│   ├── __init__.py
│   └── example_generator.py     # Main logic with LearningContext class
├── learning_contexts/           # User learning context storage
├── user_profiles/              # CLI profile storage
├── api_server.py               # Flask API server
├── cli_app.py                  # CLI application
├── background.js               # Extension service worker
├── content.js                  # Extension content script
├── popup.html/js               # Extension popup interface
├── manifest.json               # Extension manifest
└── requirements.txt            # Python dependencies
```

## Research Contribution

This work presents a novel approach to dynamic personalization that goes beyond static user profiles by incorporating real-time behavioral analytics and learning context adaptation.