#!/usr/bin/env python3
"""
MongoDB Atlas Setup Script for INGRES RAG Chatbot

This script helps you configure MongoDB Atlas connection for your chatbot.
"""

import os
import sys
import re
from pathlib import Path


def setup_mongodb_atlas():
    print("🍃 MongoDB Atlas Setup for INGRES RAG Chatbot")
    print("=" * 50)
    print()

    print("📋 Steps to set up MongoDB Atlas:")
    print("1. Go to https://www.mongodb.com/cloud/atlas")
    print("2. Create a free account (if you don't have one)")
    print("3. Create a new cluster (free tier available)")
    print("4. Create a database user with read/write permissions")
    print("5. Get your connection string")
    print()

    print("🔗 Getting your connection string:")
    print("1. In MongoDB Atlas, click 'Connect' on your cluster")
    print("2. Choose 'Drivers'")
    print("3. Select 'Python' and version '3.6 or later'")
    print("4. Copy the connection string")
    print()

    # Check if .env file exists
    env_file = Path(".env")

    if env_file.exists():
        print("📄 Found existing .env file")

        # Read current content
        with open(env_file, "r") as f:
            content = f.read()
    else:
        print("📄 Creating .env file")
        content = """MONGODB_URL=mongodb+srv://<username>:<password>@<cluster-name>.mongodb.net/<database-name>?retryWrites=true&w=majority
DATABASE_NAME=ingres_rag
GEMINI_API_KEY=your_gemini_api_key_here
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_DIMENSION=384
TOP_K_RESULTS=5
"""

    print()
    connection_string = input(
        "🔐 Enter your MongoDB Atlas connection string (or press Enter to skip): "
    ).strip()

    if connection_string:
        # Validate connection string format
        if not connection_string.startswith("mongodb+srv://"):
            print(
                "⚠️  Warning: Connection string should start with 'mongodb+srv://' for Atlas"
            )

        # Extract database name from connection string if provided
        database_name = "ingres_rag"
        db_match = re.search(r"\.net/([^?]+)", connection_string)
        if db_match:
            database_name = db_match.group(1)
        else:
            # If no database in URL, add it
            if "?" in connection_string:
                connection_string = connection_string.replace("?", f"/{database_name}?")
            else:
                connection_string = f"{connection_string}/{database_name}"

        # Update the content
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("MONGODB_URL="):
                lines[i] = f"MONGODB_URL={connection_string}"
            elif line.startswith("DATABASE_NAME="):
                lines[i] = f"DATABASE_NAME={database_name}"
        content = "\n".join(lines)

        # Write updated content
        with open(env_file, "w") as f:
            f.write(content)

        print("✅ MongoDB Atlas connection string saved to .env file")
        print(f"📊 Database name set to: {database_name}")
        print()
        print("🚀 You can now run the system with:")
        print("   python run.py")
    else:
        print("⚠️  No connection string provided.")
        print()
        print("💡 You can add your connection string later by editing the .env file:")
        print("   MONGODB_URL=your_actual_connection_string")

        # Still create .env with placeholder if it doesn't exist
        if not env_file.exists():
            with open(env_file, "w") as f:
                f.write(content)
            print("📄 Created .env file with placeholder settings")


def check_current_setup():
    """Check current MongoDB setup"""
    print("\n🔍 Current MongoDB Setup Check:")
    print("-" * 35)

    env_file = Path(".env")
    if not env_file.exists():
        print("❌ No .env file found")
        return False

    with open(env_file, "r") as f:
        content = f.read()

    if "MONGODB_URL=" in content:
        for line in content.split("\n"):
            if line.startswith("MONGODB_URL="):
                url = line.split("=", 1)[1].strip()
                if url.startswith("mongodb+srv://") and "<username>" not in url:
                    print("✅ MongoDB Atlas connection string is configured")
                    return True
                elif url.startswith("mongodb://localhost"):
                    print(
                        "⚠️  Local MongoDB URL found - switching to Atlas is recommended"
                    )
                    return False
                else:
                    print("⚠️  MongoDB URL placeholder found - needs to be replaced")
                    return False

    print("❌ No MongoDB URL found in .env file")
    return False


def test_connection():
    """Test MongoDB Atlas connection"""
    print("\n🔍 Testing MongoDB Atlas Connection:")
    print("-" * 40)

    try:
        import motor.motor_asyncio
        import asyncio
        from app.config import settings

        async def test_mongo():
            try:
                client = motor.motor_asyncio.AsyncIOMotorClient(
                    settings.mongodb_url, serverSelectionTimeoutMS=5000
                )

                # Test connection
                await client.admin.command("ping")
                print("✅ Successfully connected to MongoDB Atlas!")

                # Test database access
                db = client[settings.database_name]
                collections = await db.list_collection_names()
                print(f"📊 Database: {settings.database_name}")
                print(f"📚 Collections: {len(collections)} found")

                client.close()
                return True

            except Exception as e:
                print(f"❌ Connection failed: {e}")
                return False

        # Run the test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(test_mongo())
        loop.close()

        return success

    except ImportError as e:
        print(f"⚠️  Cannot test connection - missing dependencies: {e}")
        print("   Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    print("🌊 INGRES RAG Chatbot - MongoDB Atlas Setup")
    print("=" * 50)

    # Check current setup
    is_configured = check_current_setup()

    if is_configured:
        print("\n✅ MongoDB Atlas appears to be configured!")

        # Offer to test connection
        test_conn = (
            input("\n🧪 Would you like to test the connection? (y/n): ").lower().strip()
        )
        if test_conn in ["y", "yes"]:
            success = test_connection()
            if success:
                print("\n🚀 System is ready! Run with: python run.py")
            else:
                print("\n❌ Connection test failed. Please check your configuration.")
        else:
            print("\n🚀 Run the chatbot with: python run.py")
        return

    print("\n" + "=" * 50)
    setup_mongodb_atlas()

    # Offer to test connection after setup
    if Path(".env").exists():
        test_conn = (
            input("\n🧪 Would you like to test the connection? (y/n): ").lower().strip()
        )
        if test_conn in ["y", "yes"]:
            test_connection()

    print("\n" + "=" * 50)
    print("📚 Additional Information:")
    print("- MongoDB Atlas free tier provides 512 MB storage")
    print("- No credit card required for free tier")
    print("- Supports up to 100 connections")
    print("- Perfect for development and small applications")
    print("- Connection string is stored locally in .env file")


if __name__ == "__main__":
    main()
