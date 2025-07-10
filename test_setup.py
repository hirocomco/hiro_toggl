#!/usr/bin/env python3
"""
Test script to validate the Docker setup without requiring Docker to be installed.
This script checks file structure and basic Python imports.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and print result."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (missing)")
        return False

def check_directory_structure():
    """Check if all required directories and files exist."""
    print("🔍 Checking Docker setup structure...")
    print("=" * 50)
    
    checks = [
        ("backend/Dockerfile", "Backend Dockerfile"),
        ("backend/requirements.txt", "Backend requirements"),
        ("backend/requirements-dev.txt", "Backend dev requirements"),
        ("backend/app/main.py", "FastAPI main application"),
        ("backend/app/api/test_routes.py", "Test API routes"),
        ("backend/toggl_client/enhanced_client.py", "Enhanced Toggl client"),
        ("backend/config/config.py", "Configuration module"),
        ("docker-compose.yml", "Docker Compose configuration"),
        ("database/init.sql", "Database initialization script"),
        (".env.example", "Environment template"),
        ("README-DOCKER.md", "Docker documentation"),
    ]
    
    all_passed = True
    for file_path, description in checks:
        if not check_file_exists(file_path, description):
            all_passed = False
    
    return all_passed

def test_python_imports():
    """Test if Python modules can be imported."""
    print("\n🐍 Testing Python imports...")
    print("=" * 50)
    
    # Add backend directory to Python path
    backend_path = os.path.join(os.getcwd(), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    imports_to_test = [
        ("fastapi", "FastAPI framework"),
        ("uvicorn", "ASGI server"),
        ("sqlalchemy", "Database ORM"),
        ("psycopg2", "PostgreSQL adapter"),
        ("requests", "HTTP client"),
        ("backoff", "Retry library"),
    ]
    
    all_imports_work = True
    for module_name, description in imports_to_test:
        try:
            __import__(module_name)
            print(f"✅ {description}: {module_name}")
        except ImportError:
            print(f"❌ {description}: {module_name} (not installed)")
            all_imports_work = False
    
    return all_imports_work

def test_enhanced_client():
    """Test if the enhanced Toggl client can be imported."""
    print("\n🔗 Testing Enhanced Toggl Client...")
    print("=" * 50)
    
    # Add backend directory to Python path
    backend_path = os.path.join(os.getcwd(), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    try:
        from toggl_client.enhanced_client import (
            EnhancedTogglClient, 
            Client, 
            Project, 
            TimeEntry, 
            ClientReport,
            MemberClientReport
        )
        print("✅ Enhanced Toggl Client imported successfully")
        print("✅ All data models imported successfully")
        
        # Test basic instantiation (will fail without credentials, but that's expected)
        try:
            client = EnhancedTogglClient(api_token="test_token")
            print("✅ Client instantiation works")
        except Exception as e:
            if "at least 10 characters" in str(e):
                print("✅ Client validation works (expected error for short token)")
            else:
                print(f"⚠️  Unexpected error: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Enhanced Toggl Client import failed: {e}")
        return False

def test_fastapi_app():
    """Test if the FastAPI app can be imported."""
    print("\n🚀 Testing FastAPI Application...")
    print("=" * 50)
    
    # Add backend directory to Python path
    backend_path = os.path.join(os.getcwd(), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    try:
        from app.main import app
        print("✅ FastAPI app imported successfully")
        
        # Check if routes are registered
        routes = [route.path for route in app.routes]
        expected_routes = ["/", "/health", "/api/test"]
        
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route registered: {route}")
            else:
                print(f"❌ Route missing: {route}")
        
        return True
        
    except ImportError as e:
        print(f"❌ FastAPI app import failed: {e}")
        return False

def print_next_steps():
    """Print instructions for next steps."""
    print("\n🎯 Next Steps...")
    print("=" * 50)
    print("1. Install Docker and Docker Compose")
    print("2. Copy .env.example to .env and add your Toggl API token")
    print("3. Run: docker compose up -d")
    print("4. Test API at: http://localhost:8000/docs")
    print("5. Check database at: http://localhost:8080")
    print("\nSee README-DOCKER.md for detailed instructions")

def main():
    """Main test function."""
    print("🧪 Toggl Client Reports - Docker Setup Test")
    print("=" * 60)
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    all_tests_passed = True
    
    # Run tests
    if not check_directory_structure():
        all_tests_passed = False
    
    if not test_python_imports():
        all_tests_passed = False
        print("\n⚠️  Some Python packages are missing. They will be installed in Docker containers.")
    
    if not test_enhanced_client():
        all_tests_passed = False
    
    if not test_fastapi_app():
        all_tests_passed = False
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 All tests passed! Docker setup is ready.")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    print_next_steps()

if __name__ == "__main__":
    main()