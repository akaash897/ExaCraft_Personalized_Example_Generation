"""
Flask API Server for AI Example Generator
Provides REST API endpoints for the browser extension.
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import core logic from separate module
from core.example_generator import ExampleGenerator, UserProfile, LearningContext, validate_profile_data

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for browser extension

# Initialize the generator once
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables.")
    print("Please create a .env file with your API key.")
    exit(1)

try:
    generator = ExampleGenerator(api_key)
    print("✅ Example Generator initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Example Generator: {e}")
    exit(1)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "AI Example Generator API",
        "version": "1.0.0",
        "endpoints": [
            "GET /health",
            "POST /generate-example", 
            "POST /generate-adaptive-example",
            "GET /get-learning-context",
            "POST /record-struggle-signal",
            "POST /start-learning-session",
            "POST /end-learning-session",
            "GET /get-session-status",
            "GET /test-example",
            "POST /validate-profile",
            "POST /sync-profile"
        ],
        "timestamp": datetime.now().isoformat()
    })


@app.route('/generate-example', methods=['POST'])
def generate_example():
    """Generate a personalized example"""
    try:
        data = request.get_json()
        
        # Validate request
        if not data or 'topic' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'topic' in request body",
                "example": "Request must include a 'topic' field"
            }), 400
        
        topic = data['topic'].strip()
        if not topic:
            return jsonify({
                "success": False,
                "error": "Topic cannot be empty",
                "example": "Please provide a valid topic"
            }), 400
        
        # Get user profile from request or use default
        user_profile_data = data.get('user_profile', {})
        
        # Validate profile data if provided
        if user_profile_data and not validate_profile_data(user_profile_data):
            return jsonify({
                "success": False,
                "error": "Invalid profile data format",
                "example": "Profile data validation failed"
            }), 400
        
        # Create user profile instance
        user_profile = UserProfile(profile_data=user_profile_data)
        
        # Generate example using core logic
        example = generator.generate_example(topic, user_profile)
        
        # Check if generation was successful
        if example.startswith("Error generating example:"):
            return jsonify({
                "success": False,
                "error": example,
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }), 500
        
        return jsonify({
            "success": True,
            "topic": topic,
            "example": example,
            "profile_used": bool(user_profile_data),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "example": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/validate-profile', methods=['POST'])
def validate_profile():
    """Validate user profile data"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "valid": False,
                "error": "No data provided"
            }), 400
        
        profile_data = data.get('profile', {})
        is_valid = validate_profile_data(profile_data)
        
        return jsonify({
            "success": True,
            "valid": is_valid,
            "profile": profile_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "valid": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/test-example', methods=['GET'])
def test_example():
    """Test endpoint to generate a sample example"""
    try:
        # Create test profile
        test_profile_data = {
            "name": "Test User",
            "location": "San Francisco, USA",
            "education": "undergraduate",
            "profession": "Software Developer",
            "complexity": "medium"
        }
        
        test_profile = UserProfile(profile_data=test_profile_data)
        
        # Generate test example
        example = generator.generate_example("machine learning", test_profile)
        
        return jsonify({
            "success": True,
            "topic": "machine learning",
            "example": example,
            "profile_used": test_profile_data,
            "note": "This is a test endpoint with sample data",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Test failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/generate-adaptive-example', methods=['POST'])
def generate_adaptive_example():
    """Generate a dynamically personalized example with learning context"""
    try:
        data = request.get_json()
        
        # Validate request
        if not data or 'topic' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'topic' in request body",
                "example": "Request must include a 'topic' field"
            }), 400
        
        topic = data['topic'].strip()
        if not topic:
            return jsonify({
                "success": False,
                "error": "Topic cannot be empty",
                "example": "Please provide a valid topic"
            }), 400
        
        # Get user profile and user_id
        user_profile_data = data.get('user_profile', {})
        user_id = data.get('user_id') or user_profile_data.get('name', 'anonymous_user')
        
        # Validate profile data if provided
        if user_profile_data and not validate_profile_data(user_profile_data):
            return jsonify({
                "success": False,
                "error": "Invalid profile data format",
                "example": "Profile data validation failed"
            }), 400
        
        # Generate adaptive example using learning context
        user_profile = UserProfile(profile_data=user_profile_data)
        learning_context = LearningContext(user_id=user_id) if user_id else None
        
        example = generator.generate_example(topic, user_profile, learning_context)
        
        # Check if generation was successful
        if example.startswith("Error generating example:"):
            return jsonify({
                "success": False,
                "error": example,
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # Get learning context summary for response
        context_summary = learning_context.get_learning_state_summary() if learning_context else {}
        
        return jsonify({
            "success": True,
            "topic": topic,
            "example": example,
            "profile_used": bool(user_profile_data),
            "learning_context": context_summary,
            "user_id": user_id,
            "adaptation_type": "dynamic_learning_aware",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "example": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/get-learning-context', methods=['GET'])
def get_learning_context():
    """Get learning context for a user"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "Missing user_id parameter"
            }), 400
        
        learning_context = LearningContext(user_id=user_id)
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "learning_context": learning_context.context_data,
            "summary": learning_context.get_learning_state_summary(),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/record-struggle-signal', methods=['POST'])
def record_struggle_signal():
    """Record struggle signals like regeneration requests"""
    try:
        data = request.get_json()
        
        if not data or 'topic' not in data or 'user_id' not in data:
            return jsonify({
                "success": False,
                "error": "Missing required fields: topic, user_id"
            }), 400
        
        user_id = data['user_id']
        topic = data['topic']
        signal_type = data.get('signal_type', 'general_struggle')
        
        # Load learning context and record struggle
        learning_context = LearningContext(user_id=user_id)
        
        # Add explicit struggle signal
        if "struggle_indicators" not in learning_context.context_data:
            learning_context.context_data["struggle_indicators"] = {}
            
        if topic not in learning_context.context_data["struggle_indicators"]:
            learning_context.context_data["struggle_indicators"][topic] = {
                "repeat_count": 1,
                "last_seen": datetime.now().isoformat()
            }
        
        # Add struggle signal information
        learning_context.context_data["struggle_indicators"][topic]["signals"] = \
            learning_context.context_data["struggle_indicators"][topic].get("signals", [])
        
        learning_context.context_data["struggle_indicators"][topic]["signals"].append({
            "type": signal_type,
            "timestamp": datetime.now().isoformat()
        })
        
        # Also record in current session if active
        learning_context.record_session_struggle_signal(topic, signal_type)
        
        learning_context.save_context()
        
        return jsonify({
            "success": True,
            "message": "Struggle signal recorded",
            "topic": topic,
            "signal_type": signal_type,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/start-learning-session', methods=['POST'])
def start_learning_session():
    """Start a new learning session for a user"""
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data:
            return jsonify({
                "success": False,
                "error": "Missing user_id in request body"
            }), 400
        
        user_id = data['user_id']
        
        # Create or get learning context
        learning_context = LearningContext(user_id=user_id)
        
        # Start new session
        session_id = learning_context.start_learning_session()
        
        return jsonify({
            "success": True,
            "message": "Learning session started",
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/end-learning-session', methods=['POST'])
def end_learning_session():
    """End the current learning session for a user"""
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data:
            return jsonify({
                "success": False,
                "error": "Missing user_id in request body"
            }), 400
        
        user_id = data['user_id']
        
        # Get learning context
        learning_context = LearningContext(user_id=user_id)
        
        # End current session
        session_ended = learning_context.end_learning_session()
        
        if session_ended:
            return jsonify({
                "success": True,
                "message": "Learning session ended",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "message": "No active session to end",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/get-session-status', methods=['GET'])
def get_session_status():
    """Get current session status for a user"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                "success": False,
                "error": "Missing user_id parameter"
            }), 400
        
        learning_context = LearningContext(user_id=user_id)
        
        if "current_session" in learning_context.context_data:
            current_session = learning_context.context_data["current_session"]
            session_summary = learning_context.get_session_summary()
            
            return jsonify({
                "success": True,
                "user_id": user_id,
                "session_active": current_session.get("session_active", False),
                "session_info": {
                    "session_id": current_session.get("session_id"),
                    "session_active": current_session.get("session_active", False),
                    "topics_in_session": [topic["topic"] for topic in current_session.get("topics_in_session", [])],
                    "duration_minutes": learning_context.get_session_duration_minutes()
                },
                "current_session": current_session,
                "session_summary": session_summary,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": True,
                "user_id": user_id,
                "session_active": False,
                "message": "No active session",
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/sync-profile', methods=['POST'])
def sync_profile():
    """Sync Chrome extension profile to file system for CLI access"""
    try:
        data = request.get_json()
        
        if not data or 'profile' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'profile' in request body"
            }), 400
        
        profile_data = data['profile']
        
        # Validate profile data
        if not validate_profile_data(profile_data):
            return jsonify({
                "success": False,
                "error": "Invalid profile data format"
            }), 400
        
        # Extract or generate user_id for filename
        user_id = profile_data.get('name', 'extension_user').replace(' ', '_').lower()
        if not user_id or user_id == '':
            user_id = 'extension_user'
        
        # Convert extension profile format to CLI format
        cli_profile_data = {
            "user_id": user_id,
            "name": profile_data.get('name', ''),
            "location": profile_data.get('location', ''),
            "education": {
                "level": profile_data.get('education', ''),
                "field": "",
                "background": ""
            },
            "culture": {
                "language": "English",
                "cultural_background": profile_data.get('cultural_background', ''),
                "religion": "",
                "traditions": []
            },
            "demographics": {
                "age_range": "",
                "profession": profile_data.get('profession', ''),
                "interests": []
            },
            "preferences": {
                "example_complexity": profile_data.get('complexity', 'medium'),
                "preferred_domains": [],
                "learning_style": "practical"
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "synced_from_extension": True
        }
        
        # Create UserProfile instance and save to file
        user_profile = UserProfile(user_id=user_id)
        user_profile.profile_data = cli_profile_data
        
        if user_profile.save_profile():
            return jsonify({
                "success": True,
                "message": "Profile synced successfully",
                "user_id": user_id,
                "file_path": f"user_profiles/{user_id}.json",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to save profile to file system"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Sync error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api-info', methods=['GET'])
def api_info():
    """API information and usage examples"""
    return jsonify({
        "service": "AI Example Generator API",
        "version": "1.0.0",
        "description": "Generate personalized examples for any topic using AI",
        "usage": {
            "generate_example": {
                "method": "POST",
                "endpoint": "/generate-example",
                "body": {
                    "topic": "string (required)",
                    "user_profile": {
                        "name": "string (optional)",
                        "location": "string (optional)",
                        "education": "string (optional)",
                        "profession": "string (optional)",
                        "complexity": "simple|medium|advanced (optional)"
                    }
                }
            }
        },
        "example_request": {
            "topic": "blockchain",
            "user_profile": {
                "name": "John Doe",
                "location": "New York, USA",
                "education": "undergraduate",
                "profession": "Finance Analyst",
                "complexity": "medium"
            }
        }
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": [
            "GET /health",
            "GET /api-info",
            "POST /generate-example",
            "POST /generate-adaptive-example",
            "GET /get-learning-context",
            "POST /record-struggle-signal",
            "POST /start-learning-session",
            "POST /end-learning-session",
            "GET /get-session-status",
            "POST /validate-profile",
            "POST /sync-profile",
            "GET /test-example"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "message": "Something went wrong on the server"
    }), 500


if __name__ == '__main__':
    print("🚀 Starting AI Example Generator API Server...")
    print("📡 Server will run on http://localhost:8000")
    print("🔌 Extension can connect to this server")
    print("")
    print("💡 Available endpoints:")
    print("   - GET  /health          (Health check)")
    print("   - GET  /api-info        (API documentation)")
    print("   - POST /generate-example (Generate examples)")
    print("   - POST /validate-profile (Validate profile data)")
    print("   - GET  /test-example    (Test endpoint)")
    print("=" * 60)
    print("📝 Example usage:")
    print("   curl -X POST http://localhost:8000/generate-example \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"topic\": \"AI\", \"user_profile\": {\"education\": \"graduate\"}}'")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8000, debug=True)