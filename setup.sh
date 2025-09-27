#!/bin/bash

echo "🌊 INGRES RAG Chatbot Setup Script"
echo "=================================="

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
echo "📋 Python version: $python_version"

if [[ $(echo "$python_version < 3.8" | bc -l) -eq 1 ]]; then
    echo "❌ Python 3.8 or higher is required"
    exit 1
fi

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check MongoDB
echo "🔍 Checking MongoDB..."
if ! command -v mongod &> /dev/null; then
    echo "⚠️  MongoDB not found. Please install MongoDB:"
    echo "   macOS: brew install mongodb/brew/mongodb-community"
    echo "   Ubuntu: sudo apt-get install mongodb"
    echo "   Or use Docker: docker run -d -p 27017:27017 --name mongodb mongo:latest"
else
    echo "✅ MongoDB found"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/raw/website_texts
mkdir -p data/raw/report_pdfs
mkdir -p data/structure_tables
mkdir -p logs

# Set permissions
chmod +x run.py

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Configure .env file with your API keys"
echo "3. Make sure MongoDB is running"
echo "4. Place your data files in the data/ directory"
echo "5. Run the system: python run.py"
echo ""
echo "📖 For detailed instructions, see README.md"