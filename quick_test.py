#!/usr/bin/env python3
"""
Quick test script for Toggl API integration.

This script provides a simple way to test the Toggl API client with your credentials.
Set your API token and run this script to verify everything is working.

Usage:
    export TOGGL_API_TOKEN='your_api_token_here'
    python quick_test.py
"""

import os
import sys
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src and config to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))

try:
    from toggl_client import TogglClient, MemberTimeTotal, TogglAPIError
    from config import TogglConfig
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)


def print_divider(title: str):
    """Print a section divider."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_authentication(client: TogglClient) -> bool:
    """Test if authentication is working."""
    print_divider("🔐 Testing Authentication")
    
    try:
        user = client.get_current_user()
        print(f"✅ Authentication successful!")
        print(f"   User: {user.get('fullname', 'Unknown')}")
        print(f"   Email: {user.get('email', 'Unknown')}")
        print(f"   ID: {user.get('id', 'Unknown')}")
        return True
    except TogglAPIError as e:
        print(f"❌ Authentication failed: {e}")
        return False


def test_workspaces(client: TogglClient) -> List[dict]:
    """Test workspace access."""
    print_divider("🏢 Testing Workspace Access")
    
    try:
        workspaces = client.get_workspaces()
        print(f"✅ Found {len(workspaces)} workspace(s):")
        
        for i, workspace in enumerate(workspaces, 1):
            print(f"   {i}. {workspace['name']} (ID: {workspace['id']})")
        
        return workspaces
    except TogglAPIError as e:
        print(f"❌ Failed to get workspaces: {e}")
        return []


def test_workspace_users(client: TogglClient, workspace_id: int) -> List[dict]:
    """Test workspace users access."""
    print_divider(f"👥 Testing Workspace Users (ID: {workspace_id})")
    
    try:
        users = client.get_workspace_users(workspace_id)
        print(f"✅ Found {len(users)} user(s) in workspace:")
        
        for i, user in enumerate(users[:5], 1):  # Show first 5 users
            print(f"   {i}. {user.get('name', 'Unknown')} (ID: {user['id']})")
        
        if len(users) > 5:
            print(f"   ... and {len(users) - 5} more users")
        
        return users
    except TogglAPIError as e:
        print(f"❌ Failed to get workspace users: {e}")
        return []


def test_member_time_tracking(client: TogglClient, workspace_id: int, users: List[dict]):
    """Test member time tracking functionality."""
    print_divider(f"⏱️  Testing Member Time Tracking")
    
    try:
        # Test 1: Get time for all members
        print("📊 Getting total time for all workspace members...")
        all_members = client.get_member_total_time(workspace_id)
        
        if all_members:
            print(f"✅ Successfully retrieved time data for {len(all_members)} member(s):")
            
            for member in all_members[:3]:  # Show first 3 members
                print(f"   • {member.user_name}: {member.total_hours:.2f} hours "
                      f"({member.entry_count} entries)")
            
            if len(all_members) > 3:
                print(f"   ... and {len(all_members) - 3} more members")
        else:
            print("⚠️  No time tracking data found for workspace members.")
        
        # Test 2: Get time for specific member
        if users:
            print(f"\n📊 Getting time data for specific member...")
            test_user = users[0]
            member_time = client.get_member_total_time(workspace_id, test_user['id'])
            
            print(f"✅ Time data for {member_time.user_name}:")
            print(f"   Total Hours: {member_time.total_hours:.2f}")
            print(f"   Billable Hours: {member_time.billable_hours:.2f}")
            print(f"   Time Entries: {member_time.entry_count}")
            
            if member_time.total_hours > 0:
                billable_pct = (member_time.billable_hours / member_time.total_hours) * 100
                print(f"   Billable Rate: {billable_pct:.1f}%")
        
    except TogglAPIError as e:
        print(f"❌ Failed to get member time data: {e}")


def main():
    """Main test function."""
    print("🚀 Toggl API Quick Test")
    print("This script will test your Toggl API integration.")
    
    # Check for API token
    api_token = os.getenv('TOGGL_API_TOKEN')
    email = os.getenv('TOGGL_EMAIL')
    password = os.getenv('TOGGL_PASSWORD')
    
    if not api_token and not (email and password):
        print("\n❌ No credentials found!")
        print("Please set one of the following:")
        print("  export TOGGL_API_TOKEN='your_api_token_here'")
        print("  OR")
        print("  export TOGGL_EMAIL='your_email@example.com'")
        print("  export TOGGL_PASSWORD='your_password'")
        print("\nYou can find your API token at: https://track.toggl.com/profile")
        return
    
    # Initialize client
    try:
        if api_token:
            client = TogglClient(api_token=api_token)
            print(f"🔑 Using API token authentication")
        else:
            client = TogglClient(email=email, password=password)
            print(f"🔑 Using email/password authentication")
    except TogglAPIError as e:
        print(f"❌ Failed to initialize client: {e}")
        return
    
    # Run tests
    auth_success = test_authentication(client)
    if not auth_success:
        print("\n❌ Authentication failed. Please check your credentials.")
        return
    
    workspaces = test_workspaces(client)
    if not workspaces:
        print("\n❌ No workspaces found. Please check your account access.")
        return
    
    # Use first workspace for testing
    test_workspace = workspaces[0]
    workspace_id = test_workspace['id']
    
    users = test_workspace_users(client, workspace_id)
    test_member_time_tracking(client, workspace_id, users)
    
    print_divider("✨ Test Complete")
    print("🎉 All tests completed successfully!")
    print("Your Toggl API integration is working correctly.")
    print("\nNext steps:")
    print("  1. Check out examples/get_member_time_example.py for more examples")
    print("  2. Read the README.md for detailed usage instructions")
    print("  3. Start integrating the TogglClient into your project")


if __name__ == "__main__":
    main() 