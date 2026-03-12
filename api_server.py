"""
Flask API Server for ExaCraft AI Example Generator
Provides REST API endpoints for the Chrome extension.
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from core.example_generator import validate_profile_data
from core.user_profile import UserProfile
from core.workflow_manager import WorkflowManager
from core.utils.validators import (
    validate_workflow_start_request,
    validate_workflow_resume_request,
)
from config.settings import get_checkpointer, DEFAULT_LLM_PROVIDER, LLM_API_KEYS

load_dotenv()

app = Flask(__name__)
CORS(app)

# ── Validate API key on startup ────────────────────────────────────────────────
default_api_key = LLM_API_KEYS.get(DEFAULT_LLM_PROVIDER)
if not default_api_key:
    print(f"Error: {DEFAULT_LLM_PROVIDER.upper()}_API_KEY not found in environment variables.")
    print("Please create a .env file with your API key.")
    exit(1)

try:
    checkpointer = get_checkpointer()
    workflow_manager = WorkflowManager(checkpointer)
    print("[OK] Workflow Manager initialized successfully")
except Exception as e:
    print(f"[WARNING] Workflow Manager initialization failed: {e}")
    workflow_manager = None


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "ExaCraft AI Example Generator API",
        "version": "5.0.0",
        "features": [
            "Natural Language Feedback",
            "Adaptive Response Agent (autonomous tool-calling)",
            "Persistent Learning Patterns",
            "Regeneration Loop (max 3 cycles)",
            "Multi-Provider LLM (Gemini + OpenAI)"
        ],
        "endpoints": [
            "GET  /health",
            "GET  /api-info",
            "POST /validate-profile",
            "POST /sync-profile",
            "POST /workflows/feedback/start",
            "POST /workflows/<thread_id>/resume",
            "GET  /workflows/<thread_id>/state",
            "DELETE /workflows/<thread_id>",
            "GET  /workflows"
        ],
        "workflow_manager_status": "active" if workflow_manager else "unavailable",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api-info', methods=['GET'])
def api_info():
    return jsonify({
        "service": "ExaCraft AI Example Generator API",
        "version": "5.0.0",
        "description": (
            "Generate personalized educational examples with autonomous feedback-driven adaptation. "
            "Natural language feedback is interpreted by the Adaptive Response Agent which autonomously "
            "decides to regenerate, accept, or flag persistent learning patterns."
        ),
        "workflow_usage": {
            "start_workflow": {
                "method": "POST",
                "endpoint": "/workflows/feedback/start",
                "body": {
                    "user_id": "string (required)",
                    "topic": "string (required)",
                    "mode": "adaptive (optional, default: adaptive)",
                    "provider": "gemini|openai (optional)"
                },
                "returns": {
                    "thread_id": "string — use this to resume",
                    "generated_example": "string",
                    "status": "awaiting_feedback"
                }
            },
            "resume_workflow": {
                "method": "POST",
                "endpoint": "/workflows/<thread_id>/resume",
                "body": {
                    "user_feedback_text": "string — natural language, empty string = skip"
                },
                "returns_when_done": {
                    "status": "completed",
                    "feedback_processed": "bool"
                },
                "returns_when_regenerated": {
                    "status": "awaiting_feedback",
                    "regeneration_requested": True,
                    "generated_example": "string — the new example",
                    "thread_id": "string — same thread, call resume again"
                }
            }
        },
        "adaptive_response_agent": {
            "description": "Autonomous agent that interprets natural-language feedback",
            "tools": {
                "regenerate": "Triggers immediate example regeneration with specific instructions",
                "accept": "Logs positive/neutral feedback as a learning insight",
                "flag_pattern": "Records a persistent learning trait that affects all future generations"
            },
            "can_combine_tools": True,
            "example": "feedback: 'too abstract, I am a nurse' → calls regenerate + flag_pattern"
        }
    })


@app.route('/validate-profile', methods=['POST'])
def validate_profile():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "valid": False, "error": "No data provided"}), 400

        profile_data = data.get('profile', {})
        is_valid = validate_profile_data(profile_data)
        return jsonify({
            "success": True,
            "valid": is_valid,
            "profile": profile_data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "valid": False, "error": str(e)}), 500


@app.route('/sync-profile', methods=['POST'])
def sync_profile():
    try:
        data = request.get_json()
        if not data or 'profile' not in data:
            return jsonify({"success": False, "error": "Missing 'profile' in request body"}), 400

        profile_data = data['profile']
        if not validate_profile_data(profile_data):
            return jsonify({"success": False, "error": "Invalid profile data format"}), 400

        user_id = profile_data.get('name', 'extension_user').replace(' ', '_').lower() or 'extension_user'

        cli_profile_data = {
            "user_id": user_id,
            "name": profile_data.get('name', ''),
            "location": profile_data.get('location', ''),
            "education": profile_data.get('education', ''),
            "profession": profile_data.get('profession', ''),
            "complexity": profile_data.get('complexity', 'medium'),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "synced_from_extension": True
        }

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
            return jsonify({"success": False, "error": "Failed to save profile to file system"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": f"Sync error: {str(e)}"}), 500


# ══════════════════════════════════════════════════════════════════════════════
# LANGGRAPH WORKFLOW ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/workflows/feedback/start', methods=['POST'])
def start_feedback_workflow():
    """Start a new adaptive example generation workflow."""
    try:
        data = request.get_json()
        is_valid, error_msg = validate_workflow_start_request(data)
        if not is_valid:
            return jsonify({"success": False, "error": error_msg,
                            "timestamp": datetime.now().isoformat()}), 400

        if workflow_manager is None:
            return jsonify({"success": False, "error": "Workflow functionality not available",
                            "timestamp": datetime.now().isoformat()}), 503

        result = workflow_manager.start_feedback_workflow(
            user_id=data["user_id"],
            topic=data["topic"],
            mode=data.get("mode", "adaptive"),
            provider=data.get("provider")
        )
        return jsonify(result), 200 if result.get("success") else 500

    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to start workflow: {str(e)}",
                        "timestamp": datetime.now().isoformat()}), 500


@app.route('/workflows/<thread_id>/resume', methods=['POST'])
def resume_feedback_workflow(thread_id):
    """
    Resume interrupted workflow with natural-language user feedback.

    Body: { "user_feedback_text": "..." }
    Empty string is valid (user skipped).

    If the Adaptive Response Agent decides to regenerate, response will include:
      status: "awaiting_feedback", generated_example: "...", thread_id: "..."
    The extension should display the new example and call resume again.
    """
    try:
        data = request.get_json() or {}
        is_valid, error_msg = validate_workflow_resume_request(data)
        if not is_valid:
            return jsonify({"success": False, "error": error_msg,
                            "timestamp": datetime.now().isoformat()}), 400

        if workflow_manager is None:
            return jsonify({"success": False, "error": "Workflow functionality not available",
                            "timestamp": datetime.now().isoformat()}), 503

        result = workflow_manager.resume_feedback_workflow(
            thread_id=thread_id,
            user_feedback_text=data.get("user_feedback_text", "")
        )
        return jsonify(result), 200 if result.get("success") else 500

    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to resume workflow: {str(e)}",
                        "timestamp": datetime.now().isoformat()}), 500


@app.route('/workflows/<thread_id>/state', methods=['GET'])
def get_workflow_state(thread_id):
    try:
        if workflow_manager is None:
            return jsonify({"success": False, "error": "Workflow functionality not available"}), 503
        result = workflow_manager.get_workflow_state(thread_id)
        return jsonify(result), 200 if result.get("success") else 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/workflows/<thread_id>', methods=['DELETE'])
def delete_workflow(thread_id):
    try:
        if workflow_manager is None:
            return jsonify({"success": False, "error": "Workflow functionality not available"}), 503
        result = workflow_manager.delete_workflow(thread_id)
        return jsonify(result), 200 if result.get("success") else 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/workflows', methods=['GET'])
def get_active_workflows():
    try:
        if workflow_manager is None:
            return jsonify({"success": False, "error": "Workflow functionality not available"}), 503
        result = workflow_manager.get_active_threads(request.args.get('user_id'))
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": [
            "GET  /health",
            "GET  /api-info",
            "POST /validate-profile",
            "POST /sync-profile",
            "POST /workflows/feedback/start",
            "POST /workflows/<thread_id>/resume",
            "GET  /workflows/<thread_id>/state",
            "DELETE /workflows/<thread_id>",
            "GET  /workflows"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "message": "Something went wrong on the server"
    }), 500


if __name__ == '__main__':
    print("=" * 70)
    print("ExaCraft AI Example Generator API — v5.0.0")
    print("=" * 70)
    print("Server: http://localhost:8000")
    print("")
    print("Workflow Endpoints:")
    print("   POST   /workflows/feedback/start    Start generation workflow")
    print("   POST   /workflows/<id>/resume       Resume with NL feedback")
    print("   GET    /workflows/<id>/state        Get workflow state")
    print("   DELETE /workflows/<id>              Cancel workflow")
    print("   GET    /workflows                   List active workflows")
    print("")
    print("Utility Endpoints:")
    print("   GET    /health                      Health check")
    print("   GET    /api-info                    API documentation")
    print("   POST   /validate-profile            Validate profile data")
    print("   POST   /sync-profile                Sync extension profile")
    print("=" * 70)
    app.run(host='0.0.0.0', port=8000, debug=True)
