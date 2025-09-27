#!/usr/bin/env python3
"""
Helper script to set up Gemini API key for INGRES RAG Chatbot
"""

import os
import sys
from pathlib import Path


def setup_gemini_api():
    print("🔑 Gemini API Key Setup")
    print("=" * 30)
    print()

    print(
        "To use Google Gemini AI for generating responses, you need a Gemini API key."
    )
    print()
    print("📋 Steps to get your Gemini API key:")
    print("1. Go to https://makersuite.google.com/app/apikey")
    print("2. Sign in with your Google account")
    print("3. Click 'Create API Key'")
    print("4. Copy the generated API key")
    print()

    # Check if .env file exists
    env_file = Path(".env")

    if env_file.exists():
        print("📄 Found existing .env file")

        # Read current content
        with open(env_file, "r") as f:
            content = f.read()

        # Check if GEMINI_API_KEY is already set
        if "GEMINI_API_KEY=" in content and "your_gemini_api_key_here" not in content:
            print("✅ Gemini API key appears to be already configured")
            return
    else:
        print("📄 Creating .env file")
        content = """MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=ingres_rag
GEMINI_API_KEY=your_gemini_api_key_here
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_DIMENSION=384
TOP_K_RESULTS=5
"""

    print()
    api_key = input("🔐 Enter your Gemini API key (or press Enter to skip): ").strip()

    if api_key:
        # Update the content
        if "GEMINI_API_KEY=" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("GEMINI_API_KEY="):
                    lines[i] = f"GEMINI_API_KEY={api_key}"
                    break
            content = "\n".join(lines)
        else:
            content += f"\nGEMINI_API_KEY={api_key}\n"

        # Write updated content
        with open(env_file, "w") as f:
            f.write(content)

        print("✅ Gemini API key saved to .env file")
        print()
        print("🚀 You can now run the system with:")
        print("   python run.py")
    else:
        print("⚠️  No API key provided. The system will work with fallback responses.")
        print()
        print("💡 You can add your API key later by editing the .env file:")
        print(f"   GEMINI_API_KEY=your_actual_api_key")

        # Still create .env with placeholder if it doesn't exist
        if not env_file.exists():
            with open(env_file, "w") as f:
                f.write(content)
            print("📄 Created .env file with default settings")


def check_current_setup():
    """Check current API key setup"""
    print("\n🔍 Current Setup Check:")
    print("-" * 25)

    env_file = Path(".env")
    if not env_file.exists():
        print("❌ No .env file found")
        return False

    with open(env_file, "r") as f:
        content = f.read()

    if "GEMINI_API_KEY=" in content:
        for line in content.split("\n"):
            if line.startswith("GEMINI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                if api_key and api_key != "your_gemini_api_key_here":
                    print("✅ Gemini API key is configured")
                    return True
                else:
                    print("⚠️  Gemini API key placeholder found - needs to be replaced")
                    return False

    print("❌ No Gemini API key found in .env file")
    return False


def main():
    print("🌊 INGRES RAG Chatbot - Gemini API Setup")
    print("=" * 45)

    # Check current setup
    is_configured = check_current_setup()

    if is_configured:
        print("\n✅ System is ready to use Gemini AI!")
        print("\n🚀 Run the chatbot with: python run.py")
        return

    print("\n" + "=" * 45)
    setup_gemini_api()

    print("\n" + "=" * 45)
    print("📚 Additional Information:")
    print("- Gemini API is free with generous limits")
    print("- The system works without API key using fallback responses")
    print("- API key is stored locally in .env file")
    print("- Never share your API key publicly")


if __name__ == "__main__":
    main()
