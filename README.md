# ExaCraft: Dynamic Learning Context Adaptation for Personalized Educational Examples

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.1.1-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-Latest-orange.svg)
![Chrome](https://img.shields.io/badge/Chrome-Extension-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-red.svg)

**An AI-powered educational system that generates culturally relevant, personalized examples by adapting to learners' dynamic context in real-time.**

[🎥 Video Demo](https://youtu.be/w1P3n8qEOdg) • [📄 Research Paper](https://github.com/yourusername/ExaCraft) • [🚀 Quick Start](#quick-start) • [📚 Documentation](#documentation)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Demo](#demo)
- [System Architecture](#system-architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Dynamic Learning Context](#dynamic-learning-context)
- [Evaluation Framework](#evaluation-framework)
- [Project Structure](#project-structure)
- [Research Contributions](#research-contributions)
- [Publication](#publication)
- [Contributing](#contributing)
- [License](#license)
- [Citation](#citation)
- [Authors](#authors)

---

## 🎯 Overview

ExaCraft is an innovative educational AI system that revolutionizes how learners receive personalized examples. Unlike traditional static personalization, ExaCraft implements a **hybrid personalization framework** that combines:

- **Static Profiles**: User-configured preferences (location, education, profession, complexity)
- **Dynamic Behavioral Adaptation**: Real-time analysis of learning patterns, struggle indicators, and mastery signals

The system seamlessly integrates into web browsing workflows via a Chrome extension, providing zero-disruption example generation while continuously adapting to learning behavior across multiple sessions.

## ✨ Key Features

### 🎓 Hybrid Personalization Framework
Combines user-configured static profiles with dynamic behavioral adaptation for truly personalized learning experiences.

### 🤝 Collaborative Filtering (NEW!)
Leverages user similarity to recommend examples:
- **User Similarity Matching**: Finds similar learners based on education, profession, interests, and learning style
- **Example Effectiveness Tracking**: Records which examples work well for which users
- **Pattern Reuse**: Adapts successful examples from similar users to new learners
- **Cold Start Mitigation**: New users benefit immediately from existing user data
- **LangGraph Integration**: Seamlessly integrated into workflow for automatic CF
- See [Collaborative Filtering Documentation](COLLABORATIVE_FILTERING.md) and [Workflow Integration](docs/workflow_collaborative_integration.md) for details

### 📊 Real-time Learning Analytics
Continuously monitors interaction patterns to detect:
- **Struggle Indicators**: Topic repetition patterns (≥3x), regeneration requests
- **Mastery Signals**: Quick progression through diverse topics
- **Learning Velocity**: Cross-session progression tracking

### 🌍 Cultural & Professional Relevance
Generates examples tailored to user's:
- Geographical location and cultural background
- Educational background and complexity preferences
- Professional context and domain expertise

### 🔄 Cross-session Continuity
Maintains personalization patterns across multiple browsing sessions for long-term learning progressions with 7-day context retention.

### ⚡ Zero-disruption Workflow
Seamless Chrome extension integration with right-click context menus and profile management.

---

## 🎥 Demo

[![ExaCraft Demo](https://img.youtube.com/vi/w1P3n8qEOdg/maxresdefault.jpg)](https://youtu.be/w1P3n8qEOdg)

**Watch the full demo**: [https://youtu.be/w1P3n8qEOdg](https://youtu.be/w1P3n8qEOdg)

---

## 🏗️ System Architecture

ExaCraft consists of two integrated components:

```
┌─────────────────────────────────────────────────────────────┐
│                     EXACRAFT SYSTEM                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  Chrome Browser  │◄────►│  Flask API       │           │
│  │  Extension       │      │  Server          │           │
│  │  (Manifest V3)   │      │  (Port 8000)     │           │
│  └──────────────────┘      └────────┬─────────┘           │
│         │                           │                      │
│         │                           ▼                      │
│         │                  ┌──────────────────┐           │
│         │                  │  Google Gemini   │           │
│         │                  │  AI (LangChain)  │           │
│         │                  └──────────────────┘           │
│         │                           │                      │
│         └──────────┬────────────────┘                      │
│                    ▼                                       │
│         ┌─────────────────────┐                           │
│         │  Learning Context   │                           │
│         │  Engine             │                           │
│         │  • User Profiles    │                           │
│         │  • Behavior Signals │                           │
│         │  • Session Tracking │                           │
│         └─────────────────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Components

1. **🌐 Browser Extension** (Chrome/Manifest V3)
   - Context menu integration for text selection
   - Profile configuration popup interface
   - Real-time example display overlay

2. **🔧 Flask API Server** (Python)
   - RESTful backend service
   - Google Gemini AI integration via LangChain
   - Behavioral analytics processing
   - Session and context management
   - Dynamic behavior tracking
   - Struggle/mastery pattern detection
   - Cross-session continuity
   - Adaptive complexity adjustment

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Chrome browser
- Google Gemini API key ([Get one here](https://ai.google.dev/))

### Installation in 3 Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ExaCraft.git
   cd ExaCraft
   ```

2. **Install dependencies & configure**
   ```bash
   pip install -r requirements.txt

   # Create .env file with your API key
   echo "GEMINI_API_KEY=your_api_key_here" > .env
   ```

3. **Start the server**
   ```bash
   python api_server.py
   ```
   Server will start on `http://localhost:8000`

4. **Test Collaborative Filtering (Optional)**
   ```bash
   # Run the collaborative filtering demo
   python test_collaborative_filtering.py
   ```
   This will create sample users and demonstrate how similar users' examples influence new generations.

   See [Collaborative Filtering Documentation](COLLABORATIVE_FILTERING.md) for detailed usage.

---

## 📦 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/ExaCraft.git
cd ExaCraft
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `langchain` - LLM framework
- `langchain-google-genai` - Google Gemini integration
- `python-dotenv` - Environment variable management
- `flask` - Web framework
- `flask-cors` - CORS support for extension

### Step 3: Configure Environment Variables

Create a `.env` file in the root directory:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

**Getting your API key:**
1. Visit [Google AI Studio](https://ai.google.dev/)
2. Sign in with your Google account
3. Generate an API key
4. Copy and paste into `.env` file

### Step 4: Install Chrome Extension

1. Start the API server:
   ```bash
   python api_server.py
   ```

2. Open Chrome and navigate to `chrome://extensions/`

3. Enable **Developer mode** (toggle in top-right corner)

4. Click **"Load unpacked"**

5. Select the ExaCraft repository directory

6. The extension icon should appear in your Chrome toolbar

---

## 💻 Usage

### 🖥️ API Server

Start the Flask backend server:

```bash
python api_server.py
```

**Output:**
```
🚀 Starting AI Example Generator API Server...
📡 Server will run on http://localhost:8000
✅ Example Generator initialized successfully
```

The server must be running for the extension to function.

### 🌐 Browser Extension

1. **Configure Your Profile**
   - Click the ExaCraft extension icon
   - Fill in your profile information:
     - Name
     - Location
     - Education level
     - Profession
     - Preferred complexity
   - Click "Save Profile"

2. **Generate Examples**
   - Highlight any text on a webpage
   - Right-click → Select "Generate Example with AI"
   - A personalized example appears in an overlay
   - Click "Regenerate" for alternative examples
   - Examples adapt based on your interaction patterns

3. **Track Learning Progress**
   - The system automatically tracks:
     - Topics you explore
     - Areas where you struggle (repeated requests)
     - Topics you master quickly
   - Complexity adjusts automatically based on behavior

---

## 📡 API Reference

### Base URL
```
http://localhost:8000
```

### Endpoints

#### Health Check
```http
GET /health
```
Returns service status and available endpoints.

#### Generate Example (Static)
```http
POST /generate-example
Content-Type: application/json

{
  "topic": "blockchain",
  "user_profile": {
    "name": "John Doe",
    "location": "San Francisco, USA",
    "education": "graduate",
    "profession": "Software Engineer",
    "complexity": "advanced"
  }
}
```

#### Generate Example (Adaptive)
```http
POST /generate-adaptive-example
Content-Type: application/json

{
  "topic": "neural networks",
  "user_id": "john_doe",
  "user_profile": { ... }
}
```
Uses dynamic learning context for behavioral adaptation.

#### Get Learning Context
```http
GET /get-learning-context?user_id=john_doe
```
Retrieves complete learning history and behavioral patterns.

#### Record Struggle Signal
```http
POST /record-struggle-signal
Content-Type: application/json

{
  "user_id": "john_doe",
  "topic": "quantum computing",
  "signal_type": "regeneration_request"
}
```

#### Start Learning Session
```http
POST /start-learning-session
Content-Type: application/json

{
  "user_id": "john_doe"
}
```

#### End Learning Session
```http
POST /end-learning-session
Content-Type: application/json

{
  "user_id": "john_doe"
}
```

#### Get Session Status
```http
GET /get-session-status?user_id=john_doe
```

#### Validate Profile
```http
POST /validate-profile
Content-Type: application/json

{
  "profile": { ... }
}
```

#### Sync Profile
```http
POST /sync-profile
Content-Type: application/json

{
  "profile": { ... }
}
```
Syncs extension profile to file system.

### Response Format

All endpoints return JSON with standard structure:

```json
{
  "success": true,
  "timestamp": "2025-01-20T12:34:56.789Z",
  "data": { ... }
}
```

Error responses:
```json
{
  "success": false,
  "error": "Error message",
  "timestamp": "2025-01-20T12:34:56.789Z"
}
```

---

## 🧠 Dynamic Learning Context

ExaCraft's core innovation lies in its ability to adapt to five key aspects of learning context:

### 1. 📉 Indicators of Struggle

**Detection:**
- Topic repetition patterns (≥3 requests for same topic)
- "Regenerate" button clicks
- Prolonged session on single concept

**Adaptation:**
- Reduces example complexity
- Uses more concrete, visual analogies
- Builds confidence with encouraging tone
- Connects to previously mastered topics
- Breaks concepts into smaller steps

### 2. 📈 Mastery Patterns

**Detection:**
- Quick progression through diverse topics (≥3 different topics in 5 interactions)
- Short session duration per topic
- Minimal regeneration requests

**Adaptation:**
- Increases complexity and sophistication
- Introduces nuanced, advanced concepts
- Makes connections between multiple topics
- Challenges appropriately with edge cases

### 3. 📚 Topic Progression History

**Tracking:**
- Timestamped interaction sequences
- Learning velocity analysis
- Cross-topic connections

**Usage:**
- Builds directly on recent topics
- Makes explicit connections to prior learning
- Uses learning journey as foundation

### 4. ⏱️ Session Boundaries

**Management:**
- Tracks session start/end times
- Maintains session-specific metrics
- Calculates duration and topic count
- Persists across sessions (7-day retention)

### 5. 🎯 Learning Progression Signals

**Multi-signal Analysis:**
- Combines struggle + mastery indicators
- Analyzes session patterns
- Adjusts in real-time
- Preserves cultural relevance throughout

### Personalization Hierarchy

The system enforces this adaptation order:

```
1. Dynamic Learning Context (struggle/mastery/connections)
         ↓
2. Cultural Personalization (location, background)
         ↓
3. Professional Relevance (domain, expertise)
```

This ensures behavioral adaptation takes precedence over static preferences.

---

## 🧪 Evaluation Framework

ExaCraft includes a comprehensive **LLM-as-a-Judge** evaluation framework for assessing the quality and effectiveness of generated examples.

### Multi-Model Evaluation

The framework uses **multiple LLM judges** (GPT-4, Claude, Gemini) to evaluate examples across 5 key dimensions:

1. **Pedagogical Quality** - Clarity, correctness, teaching effectiveness
2. **Personalization Fit** - Alignment with user profile (culture, profession)
3. **Complexity Appropriateness** - Difficulty matches learner state
4. **Topic Relevance** - How well the example addresses the concept
5. **Engagement Potential** - Interestingness and relatability

### Quick Start

```bash
# Install evaluation dependencies
pip install openai anthropic

# Configure API keys in .env
echo "OPENAI_API_KEY=your_key" >> .env
echo "ANTHROPIC_API_KEY=your_key" >> .env

# Run setup check
python tests/evaluation/setup_check.py

# Run full evaluation
python tests/evaluation/run_evaluation.py

# Analyze results
python tests/evaluation/analyze_results.py tests/evaluation/results/<file>.json
```

### Features

- **7 Test Scenarios** - Covering beginners, advanced learners, edge cases
- **Multi-Judge Scoring** - Reduces model-specific bias
- **Adaptive vs Static Comparison** - Validates learning context benefits
- **Judge Agreement Metrics** - Measures evaluation consistency
- **Automated Analysis** - Generates insights and recommendations

### Example Usage

```python
from tests.evaluation import LLMJudge

judge = LLMJudge(
    openai_api_key="...",
    anthropic_api_key="...",
    gemini_api_key="..."
)

evaluation = judge.evaluate_example(
    example="Your generated example...",
    topic="recursion",
    profile_summary=profile_summary,
    context_summary=context_summary,
    judges=["gpt4", "claude", "gemini"]
)

print(f"Overall score: {evaluation.overall_average():.2f}/5.0")
```

**See full documentation**: [`tests/evaluation/README.md`](tests/evaluation/README.md)

---

## 📁 Project Structure

```
ExaCraft/
├── 📂 core/
│   ├── __init__.py
│   └── example_generator.py      # Core business logic
│       ├── ExampleGenerator       # AI generation class
│       ├── UserProfile            # Profile management
│       └── LearningContext        # Behavior tracking
│
├── 📂 tests/evaluation/           # LLM-as-Judge evaluation framework
│   ├── llm_judge.py               # Multi-model evaluation engine
│   ├── test_scenarios.py          # Test case definitions
│   ├── run_evaluation.py          # Evaluation orchestrator
│   ├── analyze_results.py         # Results analysis tools
│   ├── example_usage.py           # Usage examples
│   ├── setup_check.py             # Setup verification
│   ├── README.md                  # Evaluation docs
│   └── results/                   # Evaluation outputs
│
├── 📂 learning_contexts/          # Dynamic behavior storage
│   └── {user_id}.json             # Per-user context files
│
├── 📂 user_profiles/              # Static profile storage
│   └── {user_id}.json             # Per-user profile files
│
├── 📂 DOCS/                       # Documentation files
│
├── 🐍 api_server.py               # Flask REST API
├── 🐍 setup.py                    # Package setup
│
├── 🔧 manifest.json               # Chrome extension manifest
├── 📜 background.js               # Extension service worker
├── 📜 content.js                  # Extension content script
├── 🎨 popup.html                  # Extension popup UI
├── 📜 popup.js                    # Popup logic
│
├── 📋 requirements.txt            # Python dependencies
├── 🔒 .env                        # Environment variables (gitignored)
├── 📖 README.md                   # This file
├── 📖 CLAUDE.md                   # Claude Code guidance
└── 📄 LICENSE                     # MIT License
```

### Key Files

| File | Purpose |
|------|---------|
| `core/example_generator.py` | Main business logic with ExampleGenerator, UserProfile, and LearningContext classes |
| `api_server.py` | Flask REST API with 11 endpoints for generation and tracking |
| `background.js` | Extension service worker handling context menu and API calls |
| `content.js` | Content script for displaying results on webpages |
| `popup.html/js` | Extension popup for profile configuration |

---

## 🔬 Research Contributions

ExaCraft makes the following key contributions to educational AI research and practice:

### 1. Hybrid Personalization Framework
First system to combine user-configured static profiles with dynamic behavioral adaptation in a unified framework, demonstrating superior personalization over static-only approaches.

### 2. Seamless Workflow Integration
Novel browser extension architecture providing zero-disruption example generation integrated directly into natural web browsing workflows with cross-session context persistence.

### 3. Cross-session Personalization Continuity
Maintains both static preferences and dynamic adaptation patterns across multiple browsing sessions with 7-day context retention and automatic data expiration.

### 4. Behavioral Analytics Model
Multi-signal analysis system detecting struggle and mastery patterns, dynamically adjusting example complexity while preserving cultural and professional relevance through hierarchical personalization.

### Research Impact

- **Domain**: Educational AI, Personalized Learning, Human-Computer Interaction
- **Novel Approach**: Real-time behavioral adaptation combined with static personalization
- **Practical Application**: Production-ready Chrome extension with API backend
- **Evaluation**: Demonstrated at CODS-2025 Demo Track

---

## 📄 Publication

### Conference Presentation

**Title**: "ExaCraft: Dynamic Learning Context Adaptation for Personalized Educational Examples"

**Authors**: Akaash Chatterjee, Suman Kundu

**Affiliation**: Indian Institute of Technology Jodhpur

**Conference**: ACM India Joint International Conference on Data Science and Management of Data (CODS-COMAD 2025) - Demo Track

**Video Demo**: [https://youtu.be/w1P3n8qEOdg](https://youtu.be/w1P3n8qEOdg)

### Abstract

ExaCraft presents a novel approach to generating personalized educational examples through hybrid personalization that combines static user profiles with dynamic learning context adaptation. The system implements a three-component architecture consisting of a Chrome browser extension, Flask API server, and learning context engine. Real-time behavioral analytics detect struggle indicators and mastery patterns, automatically adjusting example complexity while maintaining cultural and professional relevance. Cross-session continuity enables long-term learning progression tracking with persistent context retention. The system demonstrates zero-disruption integration into natural web browsing workflows, making personalized learning accessible without workflow interruption.

---

## 🤝 Contributing

We welcome contributions to ExaCraft! Here's how you can help:

### Reporting Issues

Found a bug or have a feature request? Please open an issue on GitHub:
- Use the issue templates provided
- Include detailed reproduction steps for bugs
- Provide context for feature requests

### Development Workflow

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/ExaCraft.git
   cd ExaCraft
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow existing code style
   - Add tests if applicable
   - Update documentation

4. **Test your changes**
   ```bash
   python api_server.py  # Test API server
   # Test extension manually in Chrome
   ```

5. **Commit and push**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Wait for review

### Areas for Contribution

- 🌐 **Browser Support**: Firefox, Safari extension ports
- 🧪 **Testing**: Unit tests, integration tests
- 📚 **Documentation**: Tutorials, API docs, use cases
- 🎨 **UI/UX**: Extension popup improvements, overlay design
- 🤖 **AI Models**: Support for additional LLM providers
- 🌍 **Internationalization**: Multi-language support
- 🔒 **Security**: Authentication, API key management
- 📊 **Analytics**: Advanced learning metrics, visualizations

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Akaash Chatterjee, Suman Kundu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## 📖 Citation

If you use ExaCraft in your research, please cite:

```bibtex
@inproceedings{chatterjee2025exacraft,
  title={ExaCraft: Dynamic Learning Context Adaptation for Personalized Educational Examples},
  author={Chatterjee, Akaash and Kundu, Suman},
  booktitle={Proceedings of the ACM India Joint International Conference on Data Science and Management of Data (CODS-COMAD)},
  year={2025},
  organization={ACM},
  note={Demo Track}
}
```

---

## 👥 Authors

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/yourusername">
        <img src="https://github.com/yourusername.png" width="100px;" alt="Akaash Chatterjee"/><br />
        <sub><b>Akaash Chatterjee</b></sub>
      </a><br />
      <sub>Indian Institute of Technology Jodhpur</sub>
    </td>
    <td align="center">
      <a href="https://github.com/collaborator">
        <img src="https://github.com/collaborator.png" width="100px;" alt="Suman Kundu"/><br />
        <sub><b>Suman Kundu</b></sub>
      </a><br />
      <sub>Indian Institute of Technology Jodhpur</sub>
    </td>
  </tr>
</table>

---

## 🙏 Acknowledgments

- **Google Gemini AI**: For providing the powerful language model API
- **LangChain**: For the excellent LLM framework
- **CODS-COMAD 2025**: For accepting our demo submission
- **IIT Jodhpur**: For institutional support

---

## 📞 Contact

- **Email**: akaash.chatterjee@example.com
- **GitHub Issues**: [Report a bug or request a feature](https://github.com/yourusername/ExaCraft/issues)
- **Research Lab**: [IIT Jodhpur CS Department](https://www.iitj.ac.in)

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/ExaCraft&type=Date)](https://star-history.com/#yourusername/ExaCraft&Date)

---

<div align="center">

**Made with ❤️ for personalized learning**

[⬆ Back to Top](#exacraft-dynamic-learning-context-adaptation-for-personalized-educational-examples)

</div>
