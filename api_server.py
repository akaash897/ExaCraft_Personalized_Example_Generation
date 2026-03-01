"""
Flask API Server for AI Example Generator
Provides REST API endpoints for the browser extension.
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import core logic from separate modules
from core.example_generator import ExampleGenerator, validate_profile_data
from core.user_profile import UserProfile
from core.learning_context import LearningContext
from core.feedback_manager import FeedbackManager
from core.workflow_manager import WorkflowManager
from core.user_similarity import UserSimilarity
from core.example_history import ExampleHistory
from core.utils.validators import (
    validate_workflow_start_request,
    validate_workflow_resume_request,
    validate_user_id,
    validate_topic
)
from config.settings import get_checkpointer

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for browser extension

# Initialize the generator once with default provider
from config.settings import DEFAULT_LLM_PROVIDER, LLM_API_KEYS

default_provider = DEFAULT_LLM_PROVIDER
default_api_key = LLM_API_KEYS.get(default_provider)

if not default_api_key:
    print(f"Error: {default_provider.upper()}_API_KEY not found in environment variables.")
    print("Please create a .env file with your API key.")
    print("Available providers: gemini (GEMINI_API_KEY), openai (OPENAI_API_KEY)")
    exit(1)

try:
    generator = ExampleGenerator(api_key=default_api_key, provider=default_provider)
    print(f"[OK] Example Generator initialized successfully with {default_provider}")
    print(f"[INFO] Model: {generator.model_config['model']}, Temperature: {generator.model_config['temperature']}")
except Exception as e:
    print(f"[ERROR] Failed to initialize Example Generator: {e}")
    exit(1)

# Initialize WorkflowManager with checkpointer
try:
    checkpointer = get_checkpointer()
    workflow_manager = WorkflowManager(checkpointer)
    print("[OK] Workflow Manager initialized successfully")
except Exception as e:
    print(f"[WARNING] Workflow Manager initialization failed: {e}")
    print("Falling back to basic functionality")
    workflow_manager = None


def get_generator_for_request(data: dict) -> ExampleGenerator:
    """
    Create generator instance based on request parameters

    Args:
        data: Request JSON containing optional 'provider' field

    Returns:
        ExampleGenerator instance configured for requested provider

    Raises:
        ValueError: If API key not configured for provider
    """
    provider = data.get('provider', DEFAULT_LLM_PROVIDER)

    # Get API key for requested provider
    api_key = LLM_API_KEYS.get(provider)
    if not api_key:
        raise ValueError(f"API key not configured for provider: {provider}")

    # Reuse default generator if provider matches
    if provider == generator.provider:
        return generator

    # Create new generator for different provider
    return ExampleGenerator(api_key=api_key, provider=provider)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "AI Example Generator API (Collaborative Filtering)",
        "version": "3.0.0",
        "features": [
            "Collaborative Filtering",
            "User Similarity Matching",
            "Example History Tracking",
            "LangGraph Workflows",
            "Adaptive Learning Context"
        ],
        "endpoints": [
            "GET /health",
            "GET /api-info",
            "POST /workflows/feedback/start (NEW - Phase 1)",
            "POST /workflows/<thread_id>/resume (NEW - Phase 1)",
            "GET /workflows/<thread_id>/state (NEW - Phase 1)",
            "DELETE /workflows/<thread_id> (NEW - Phase 1)",
            "GET /workflows (NEW - Phase 1)",
            "POST /generate-example (Legacy)",
            "POST /generate-adaptive-example (Legacy)",
            "GET /get-learning-context",
            "POST /record-struggle-signal",
            "POST /start-learning-session",
            "POST /end-learning-session",
            "GET /get-session-status",
            "GET /test-example",
            "POST /validate-profile",
            "POST /sync-profile"
        ],
        "workflow_manager_status": "active" if workflow_manager else "unavailable",
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

        # Get generator for requested provider
        try:
            request_generator = get_generator_for_request(data)
            provider_used = request_generator.provider
        except ValueError as ve:
            return jsonify({
                "success": False,
                "error": str(ve),
                "example": "Provider API key not configured"
            }), 400

        # Generate example using core logic
        example = request_generator.generate_example(topic, user_profile)
        
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
            "provider": provider_used,
            "model": request_generator.model_config,
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

        # Get generator for requested provider
        try:
            request_generator = get_generator_for_request(data)
            provider_used = request_generator.provider
        except ValueError as ve:
            return jsonify({
                "success": False,
                "error": str(ve)
            }), 400

        # Build feedback influence data for legacy endpoint
        from core.feedback_manager import FeedbackManager
        from core.workflow_nodes import _build_feedback_influence

        feedback_influence = None
        if learning_context:
            feedback_mgr = FeedbackManager(user_id)
            recent_feedback = feedback_mgr.get_feedback_patterns(topic=topic, limit=5)
            all_recent_feedback = feedback_mgr.get_feedback_patterns(limit=10)
            current_thresholds = feedback_mgr.get_current_thresholds()

            feedback_influence = _build_feedback_influence(
                learning_context=learning_context,
                feedback_mgr=feedback_mgr,
                topic=topic,
                recent_feedback=recent_feedback,
                all_recent_feedback=all_recent_feedback,
                current_thresholds=current_thresholds
            )

        example = request_generator.generate_example(topic, user_profile, learning_context)

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
            "feedback_influence": feedback_influence,
            "provider": provider_used,
            "model": request_generator.model_config,
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


# ==================== COLLABORATIVE FILTERING ENDPOINTS ====================

@app.route('/generate-collaborative-example', methods=['POST'])
def generate_collaborative_example():
    """Generate example using collaborative filtering from similar users"""
    try:
        data = request.get_json()

        # Validate request
        if not data or 'topic' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'topic' in request body"
            }), 400

        topic = data['topic'].strip()
        if not topic:
            return jsonify({
                "success": False,
                "error": "Topic cannot be empty"
            }), 400

        # Get user profile and user_id
        user_profile_data = data.get('user_profile', {})
        user_id = data.get('user_id') or user_profile_data.get('name', 'anonymous_user')

        # Validate profile data if provided
        if user_profile_data and not validate_profile_data(user_profile_data):
            return jsonify({
                "success": False,
                "error": "Invalid profile data format"
            }), 400

        # Get collaborative filtering settings
        use_collaborative = data.get('use_collaborative_filtering', True)
        record_history = data.get('record_history', True)

        # Get generator for requested provider
        try:
            request_generator = get_generator_for_request(data)
            provider_used = request_generator.provider
        except ValueError as ve:
            return jsonify({
                "success": False,
                "error": str(ve)
            }), 400

        # Generate collaborative example
        result = request_generator.generate_collaborative_example(
            topic=topic,
            profile_data=user_profile_data,
            user_id=user_id,
            use_collaborative_filtering=use_collaborative,
            record_history=record_history
        )

        # Check if generation was successful
        example_text = result.get("example", "")
        if example_text.startswith("Error generating example:"):
            return jsonify({
                "success": False,
                "error": example_text,
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }), 500

        return jsonify({
            "success": True,
            "topic": topic,
            "example": example_text,
            "example_id": result.get("example_id"),
            "similar_users": result.get("similar_users", []),
            "source_examples": result.get("source_examples", []),
            "metadata": result.get("metadata", {}),
            "provider": provider_used,
            "model": request_generator.model_config,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/find-similar-users', methods=['POST'])
def find_similar_users():
    """Find users similar to the given user based on profile"""
    try:
        data = request.get_json()

        if not data or 'user_id' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'user_id' in request body"
            }), 400

        user_id = data['user_id']
        user_profile_data = data.get('user_profile', {})
        top_k = data.get('top_k', 5)
        min_similarity = data.get('min_similarity', 0.3)

        # Validate profile data
        if user_profile_data and not validate_profile_data(user_profile_data):
            return jsonify({
                "success": False,
                "error": "Invalid profile data format"
            }), 400

        # Find similar users
        similarity_engine = UserSimilarity()
        all_profiles = similarity_engine.get_all_user_profiles()

        similar_users = similarity_engine.find_similar_users(
            target_user_id=user_id,
            target_profile=user_profile_data,
            all_profiles=all_profiles,
            top_k=top_k,
            min_similarity=min_similarity
        )

        return jsonify({
            "success": True,
            "user_id": user_id,
            "similar_users": [
                {
                    "user_id": uid,
                    "similarity_score": score
                }
                for uid, score in similar_users
            ],
            "total_users_analyzed": len(all_profiles),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/example-history/record-feedback', methods=['POST'])
def record_example_feedback():
    """Record user feedback on a generated example"""
    try:
        data = request.get_json()

        required_fields = ['user_id', 'example_id', 'accepted']
        if not data or not all(field in data for field in required_fields):
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(required_fields)}"
            }), 400

        user_id = data['user_id']
        example_id = data['example_id']
        accepted = data['accepted']
        regeneration_requested = data.get('regeneration_requested', False)

        # Record feedback
        history = ExampleHistory(user_id=user_id)
        success = history.record_feedback(
            example_id=example_id,
            accepted=accepted,
            regeneration_requested=regeneration_requested
        )

        if success:
            return jsonify({
                "success": True,
                "message": "Feedback recorded successfully",
                "user_id": user_id,
                "example_id": example_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Example ID not found",
                "example_id": example_id
            }), 404

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/example-history/statistics', methods=['GET'])
def get_example_statistics():
    """Get statistics about example history for a user"""
    try:
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({
                "success": False,
                "error": "Missing user_id parameter"
            }), 400

        history = ExampleHistory(user_id=user_id)
        stats = history.get_statistics()

        return jsonify({
            "success": True,
            "user_id": user_id,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/example-history/effective-examples', methods=['GET'])
def get_effective_examples():
    """Get most effective examples for a user or topic"""
    try:
        user_id = request.args.get('user_id')
        topic = request.args.get('topic')
        min_score = float(request.args.get('min_score', 0.5))
        limit = int(request.args.get('limit', 5))

        if not user_id:
            return jsonify({
                "success": False,
                "error": "Missing user_id parameter"
            }), 400

        history = ExampleHistory(user_id=user_id)

        if topic:
            examples = history.get_effective_examples_for_topic(
                topic=topic,
                min_score=min_score,
                limit=limit
            )
        else:
            examples = history.get_user_most_effective_examples(limit=limit)

        # Clean up examples for response (remove some internal fields)
        clean_examples = []
        for ex in examples:
            clean_examples.append({
                "example_id": ex.get("example_id"),
                "topic": ex.get("topic"),
                "example_text": ex.get("example_text"),
                "timestamp": ex.get("timestamp"),
                "effectiveness_score": ex.get("effectiveness_score")
            })

        return jsonify({
            "success": True,
            "user_id": user_id,
            "topic": topic,
            "examples": clean_examples,
            "count": len(clean_examples),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


# ==================== LANGGRAPH WORKFLOW ENDPOINTS ====================

@app.route('/workflows/feedback/start', methods=['POST'])
def start_feedback_workflow():
    """Start a new feedback generation workflow (Phase 1)"""
    try:
        data = request.get_json()

        # Validate request
        is_valid, error_msg = validate_workflow_start_request(data)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }), 400

        # Check if workflow_manager is available
        if workflow_manager is None:
            return jsonify({
                "success": False,
                "error": "Workflow functionality not available",
                "timestamp": datetime.now().isoformat()
            }), 503

        # Start workflow with collaborative filtering support
        result = workflow_manager.start_feedback_workflow(
            user_id=data["user_id"],
            topic=data["topic"],
            mode=data.get("mode", "adaptive"),
            provider=data.get("provider"),  # Pass provider to workflow
            use_collaborative_filtering=data.get("use_collaborative_filtering", True)
        )

        return jsonify(result), 200 if result.get("success") else 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to start workflow: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/workflows/<thread_id>/resume', methods=['POST'])
def resume_feedback_workflow(thread_id):
    """Resume interrupted workflow with user feedback"""
    try:
        data = request.get_json()

        # Validate feedback ratings
        is_valid, error_msg = validate_workflow_resume_request(data)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }), 400

        # Check if workflow_manager is available
        if workflow_manager is None:
            return jsonify({
                "success": False,
                "error": "Workflow functionality not available",
                "timestamp": datetime.now().isoformat()
            }), 503

        # Resume workflow
        result = workflow_manager.resume_feedback_workflow(
            thread_id=thread_id,
            difficulty_rating=data["difficulty_rating"],
            clarity_rating=data["clarity_rating"],
            usefulness_rating=data["usefulness_rating"]
        )

        return jsonify(result), 200 if result.get("success") else 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to resume workflow: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/workflows/<thread_id>/state', methods=['GET'])
def get_workflow_state(thread_id):
    """Get current state of a workflow"""
    try:
        # Check if workflow_manager is available
        if workflow_manager is None:
            return jsonify({
                "success": False,
                "error": "Workflow functionality not available",
                "timestamp": datetime.now().isoformat()
            }), 503

        result = workflow_manager.get_workflow_state(thread_id)
        return jsonify(result), 200 if result.get("success") else 404

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get workflow state: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/workflows/<thread_id>', methods=['DELETE'])
def delete_workflow(thread_id):
    """Delete/cancel a workflow"""
    try:
        # Check if workflow_manager is available
        if workflow_manager is None:
            return jsonify({
                "success": False,
                "error": "Workflow functionality not available",
                "timestamp": datetime.now().isoformat()
            }), 503

        result = workflow_manager.delete_workflow(thread_id)
        return jsonify(result), 200 if result.get("success") else 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to delete workflow: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/workflows', methods=['GET'])
def get_active_workflows():
    """Get list of active workflows, optionally filtered by user_id"""
    try:
        user_id = request.args.get('user_id')

        # Check if workflow_manager is available
        if workflow_manager is None:
            return jsonify({
                "success": False,
                "error": "Workflow functionality not available",
                "timestamp": datetime.now().isoformat()
            }), 503

        result = workflow_manager.get_active_threads(user_id)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get active workflows: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


# ==================== INFORMATION & UTILITY ENDPOINTS ====================

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
            "POST /generate-collaborative-example",
            "GET /get-learning-context",
            "POST /record-struggle-signal",
            "POST /start-learning-session",
            "POST /end-learning-session",
            "GET /get-session-status",
            "POST /validate-profile",
            "POST /sync-profile",
            "POST /find-similar-users",
            "POST /example-history/record-feedback",
            "GET /example-history/statistics",
            "GET /example-history/effective-examples",
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
    print("=" * 70)
    print("Starting AI Example Generator API Server (Collaborative Filtering)")
    print("=" * 70)
    print("Server will run on http://localhost:8000")
    print("Extension can connect to this server")
    print("")
    print("NEW: Collaborative Filtering Endpoints")
    print("   - POST /generate-collaborative-example  (Generate with similar users)")
    print("   - POST /find-similar-users              (Find similar users)")
    print("   - POST /example-history/record-feedback (Record example feedback)")
    print("   - GET  /example-history/statistics      (Get history statistics)")
    print("   - GET  /example-history/effective-examples (Get effective examples)")
    print("")
    print("LangGraph Workflow Endpoints (Phase 1)")
    print("   - POST /workflows/feedback/start  (Start feedback workflow)")
    print("   - POST /workflows/<id>/resume     (Resume with feedback)")
    print("   - GET  /workflows/<id>/state      (Get workflow state)")
    print("   - DELETE /workflows/<id>          (Delete workflow)")
    print("   - GET  /workflows                 (List active workflows)")
    print("")
    print("Core Endpoints:")
    print("   - GET  /health                    (Health check)")
    print("   - GET  /api-info                  (API documentation)")
    print("   - POST /generate-example          (Generate examples)")
    print("   - POST /generate-adaptive-example (Adaptive generation)")
    print("   - POST /validate-profile          (Validate profile data)")
    print("   - GET  /test-example              (Test endpoint)")
    print("=" * 70)
    print("Example workflow usage:")
    print("   # Start workflow")
    print("   curl -X POST http://localhost:8000/workflows/feedback/start \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"user_id\": \"user123\", \"topic\": \"recursion\"}'")
    print("")
    print("   # Resume with feedback")
    print("   curl -X POST http://localhost:8000/workflows/<thread_id>/resume \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"difficulty_rating\": 3, \"clarity_rating\": 4, \"usefulness_rating\": 5}'")
    print("=" * 70)

    app.run(host='0.0.0.0', port=8000, debug=True)