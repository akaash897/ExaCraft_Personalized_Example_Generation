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
from core.example_generator import ExampleGenerator, UserProfile, validate_profile_data

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
            "GET /test-example",
            "POST /validate-profile"
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
            "POST /validate-profile",
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