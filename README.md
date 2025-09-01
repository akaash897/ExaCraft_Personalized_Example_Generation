# ExaCraft: Dynamic Learning Context Adaptation for Personalized Educational Examples

This repository contains the implementation of **ExaCraft**, an AI system that generates personalized educational examples by adapting to learners' dynamic context. ExaCraft combines user-defined profiles with real-time analysis of learner behavior to ensure examples are both culturally relevant and tailored to individual learning needs.

## System Architecture

ExaCraft consists of three integrated components:

1. **Browser Extension** (Chrome/Manifest V3) - Seamless integration with web browsing workflows, providing zero-disruption example generation via right-click context menus
2. **Python Flask API Server** - RESTful backend service that orchestrates AI content generation with behavioral analytics using Google Gemini AI through LangChain
3. **Learning Context Engine** - Novel component that tracks and analyzes dynamic learning context, detecting struggle indicators and mastery patterns for real-time adaptation

## Key Features

- **Hybrid Personalization Framework**: Combines user-configured static profiles (location, education, profession, complexity preferences) with dynamic behavioral adaptation
- **Real-time Learning Analytics**: Continuously monitors interaction patterns to detect struggle indicators, mastery signals, and learning progression
- **Cultural and Professional Relevance**: Generates examples tailored to user's geographical location, educational background, and professional context
- **Cross-session Continuity**: Maintains personalization patterns across multiple browsing sessions for long-term learning progressions
- **Zero-disruption Workflow**: Integrates seamlessly with natural web browsing through Chrome extension

## Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup**
   Create a `.env` file with your Google Gemini API key:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
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
4. Right-click on any highlighted text to generate personalized examples
5. Configure your profile through the extension popup for personalized content

## Core Components

- **`api_server.py`** - Flask REST API with Google Gemini AI integration through LangChain for refined prompt engineering
- **`cli_app.py`** - Interactive command-line interface for direct system interaction
- **`core/example_generator.py`** - Main business logic with ExampleGenerator, UserProfile, and LearningContext classes implementing hybrid personalization
- **Chrome Extension** - `manifest.json`, `background.js`, `content.js`, `popup.html/js` providing seamless workflow integration with behavioral analytics

## API Endpoints

- `GET /health` - Health check
- `POST /generate-example` - Generate static personalized example
- `POST /generate-adaptive-example` - Generate dynamically adaptive example
- `GET /get-learning-context` - Retrieve user learning context
- `POST /record-struggle-signal` - Record behavioral struggle signals
- `POST /start-learning-session` - Start new learning session
- `POST /end-learning-session` - End current learning session

## Dynamic Learning Context Adaptation

ExaCraft's core innovation lies in its ability to adapt to five key aspects of learning context:

1. **Indicators of Struggle** - Topic repetition patterns (≥3x) and regeneration button clicks trigger complexity reduction
2. **Mastery Patterns** - Rapid topic progression through diverse subjects (≥3 different topics) increases example sophistication  
3. **Topic Progression History** - Maintains timestamped interaction sequences for learning velocity analysis
4. **Session Boundaries** - Tracks learning session starts/ends with persistent cross-session context
5. **Learning Progression Signals** - Multi-signal behavioral analysis for real-time personalization adjustments

The system evolves examples from basic concepts to advanced technical implementations, responding dynamically to user interaction patterns while maintaining cultural and professional relevance.

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

## Research Contributions

ExaCraft makes the following key contributions to educational AI research and practice:

- **Hybrid Personalization Framework** that combines user-configured static profiles with dynamic behavioral adaptation
- **Seamless Workflow Integration** via browser extension providing zero-disruption example generation with integrated profile management
- **Cross-session Personalization Continuity** that maintains both static preferences and dynamic adaptation patterns across multiple browsing sessions
- **Behavioral Analytics Model** using multi-signal analysis to detect struggle and mastery, dynamically adjusting example complexity while preserving cultural relevance

## Demo and Publication

- **Video Demo**: https://youtu.be/w1P3n8qEOdg
- **Conference**: CODS-2025 Demo Track (ACM India Joint International Conference on Data Science)
- **Paper Title**: "ExaCraft: Dynamic Learning Context Adaptation for Personalized Educational Examples"
- **Authors**: Akaash Chatterjee, Suman Kundu (Indian Institute of Technology Jodhpur)