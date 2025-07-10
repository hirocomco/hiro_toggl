#!/usr/bin/env python3
"""
Example script showing how to use the Toggl API to get total time tracked for members.

This script demonstrates various ways to retrieve time tracking data:
1. Get total time for a specific member
2. Get total time for all members in a workspace
3. Get time data for a specific date range
4. Handle different authentication methods

Usage:
    python get_member_time_example.py
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "config"))

from toggl_client import TogglClient, MemberTimeTotal, TogglAPIError
from config import TogglConfig


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_member_time_summary(member: MemberTimeTotal) -> None:
    """Print a formatted summary of member time data."""
    print(f"\n📊 Time Summary for {member.user_name} (ID: {member.user_id})")
    print("=" * 50)
    print(
        f"Total Time:     {member.total_hours:.2f} hours ({member.total_duration_seconds} seconds)"
    )
    print(
        f"Billable Time:  {member.billable_hours:.2f} hours ({member.billable_duration_seconds} seconds)"
    )
    print(f"Time Entries:   {member.entry_count}")

    if member.total_hours > 0:
        billable_percentage = (member.billable_hours / member.total_hours) * 100
        print(f"Billable Rate:  {billable_percentage:.1f}%")


def print_workspace_summary(members: List[MemberTimeTotal]) -> None:
    """Print a summary table of all workspace members."""
    if not members:
        print("❌ No time tracking data found for this workspace.")
        return

    print(f"\n📈 Workspace Time Summary ({len(members)} members)")
    print("=" * 80)
    print(
        f"{'Name':<20} {'Total Hours':<12} {'Billable Hours':<15} {'Entries':<8} {'Billable %':<10}"
    )
    print("-" * 80)

    total_hours = 0
    total_billable = 0
    total_entries = 0

    for member in sorted(members, key=lambda m: m.total_hours, reverse=True):
        billable_pct = (
            (member.billable_hours / member.total_hours * 100)
            if member.total_hours > 0
            else 0
        )

        print(
            f"{member.user_name:<20} {member.total_hours:<12.2f} {member.billable_hours:<15.2f} "
            f"{member.entry_count:<8} {billable_pct:<10.1f}%"
        )

        total_hours += member.total_hours
        total_billable += member.billable_hours
        total_entries += member.entry_count

    print("-" * 80)
    overall_billable_pct = (
        (total_billable / total_hours * 100) if total_hours > 0 else 0
    )
    print(
        f"{'TOTAL':<20} {total_hours:<12.2f} {total_billable:<15.2f} "
        f"{total_entries:<8} {overall_billable_pct:<10.1f}%"
    )


def example_get_specific_member_time(
    client: TogglClient, workspace_id: int, user_id: int
):
    """Example: Get total time for a specific member."""
    print(f"\n🔍 Getting time data for user {user_id} in workspace {workspace_id}...")

    try:
        # Get time data for specific member
        member_time = client.get_member_total_time(workspace_id, user_id)
        print_member_time_summary(member_time)

        # Get time data for specific date range (last 30 days)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        print(
            f"\n📅 Getting time data for last 30 days ({start_date} to {end_date})..."
        )
        member_time_period = client.get_member_total_time(
            workspace_id, user_id, start_date, end_date
        )
        print_member_time_summary(member_time_period)

    except TogglAPIError as e:
        print(f"❌ Error getting member time data: {e}")


def example_get_all_members_time(client: TogglClient, workspace_id: int):
    """Example: Get total time for all members in workspace."""
    print(f"\n👥 Getting time data for all members in workspace {workspace_id}...")

    try:
        # Get time data for all members
        all_members = client.get_member_total_time(workspace_id)
        print_workspace_summary(all_members)

        # Get time data for current month
        now = datetime.now()
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        print(
            f"\n📅 Getting time data for current month ({start_date} to {end_date})..."
        )
        monthly_members = client.get_member_total_time(
            workspace_id, None, start_date, end_date
        )
        print_workspace_summary(monthly_members)

    except TogglAPIError as e:
        print(f"❌ Error getting workspace time data: {e}")


def example_workspace_info(client: TogglClient):
    """Example: Get workspace information."""
    print("\n🏢 Getting workspace information...")

    try:
        # Get current user
        user = client.get_current_user()
        print(
            f"Current User: {user.get('fullname', 'Unknown')} ({user.get('email', 'Unknown')})"
        )

        # Get workspaces
        workspaces = client.get_workspaces()
        print(f"\n📋 Available Workspaces ({len(workspaces)}):")

        for workspace in workspaces:
            print(f"  - {workspace['name']} (ID: {workspace['id']})")

            # Get workspace users
            try:
                users = client.get_workspace_users(workspace["id"])
                print(f"    Users: {len(users)} members")

                for user in users[:3]:  # Show first 3 users
                    print(f"      • {user.get('name', 'Unknown')} (ID: {user['id']})")

                if len(users) > 3:
                    print(f"      ... and {len(users) - 3} more")

            except TogglAPIError as e:
                print(f"    ❌ Could not get users: {e}")

        return workspaces

    except TogglAPIError as e:
        print(f"❌ Error getting workspace info: {e}")
        return []


def main():
    """Main example function."""
    setup_logging()

    print("🚀 Toggl API - Member Time Tracking Example")
    print("=" * 60)

    # Load configuration
    config = TogglConfig.from_env()

    if not config.is_valid():
        print("❌ Configuration Error!")
        print("\nPlease set your Toggl credentials using one of these methods:")
        print("\n1. API Token (Recommended):")
        print("   export TOGGL_API_TOKEN='your_api_token_here'")
        print("\n2. Email/Password:")
        print("   export TOGGL_EMAIL='your_email@example.com'")
        print("   export TOGGL_PASSWORD='your_password'")
        print("\n3. Optional - Set default workspace:")
        print("   export TOGGL_WORKSPACE_ID='123456'")
        print("\nYou can find your API token in your Toggl profile settings.")
        return

    # Initialize client
    try:
        if config.api_token:
            client = TogglClient(api_token=config.api_token)
            print("✅ Authenticated with API token")
        else:
            client = TogglClient(email=config.email, password=config.password)
            print("✅ Authenticated with email/password")

    except TogglAPIError as e:
        print(f"❌ Authentication failed: {e}")
        return

    # Get workspace information
    workspaces = example_workspace_info(client)

    if not workspaces:
        print("❌ No workspaces found or accessible.")
        return

    # Use default workspace or first available
    workspace_id = config.default_workspace_id or workspaces[0]["id"]
    workspace_name = next(
        (w["name"] for w in workspaces if w["id"] == workspace_id), "Unknown"
    )

    print(f"\n🎯 Using workspace: {workspace_name} (ID: {workspace_id})")

    # Example 1: Get all members time
    example_get_all_members_time(client, workspace_id)

    # Example 2: Get specific member time (if we have users)
    try:
        users = client.get_workspace_users(workspace_id)
        if users:
            # Use first user as example
            example_user_id = users[0]["id"]
            example_get_specific_member_time(client, workspace_id, example_user_id)
        else:
            print("\n⚠️  No users found in workspace for specific member example.")

    except TogglAPIError as e:
        print(f"⚠️  Could not get workspace users for example: {e}")

    print("\n✨ Example completed!")


if __name__ == "__main__":
    main()
