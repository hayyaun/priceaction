#!/bin/bash

# BTC/USDT Trading Bot Setup Script

echo "=========================================="
echo "BTC/USDT Trading Bot Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Check if venv exists and is valid
if [ -d "venv" ]; then
    # Check if venv is valid
    if [ ! -f "venv/bin/activate" ]; then
        echo ""
        echo "⚠ Incomplete virtual environment found. Removing..."
        rm -rf venv
    else
        echo ""
        echo "✓ Virtual environment already exists"
    fi
fi

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    
    # Try to create venv
    if python3 -m venv venv 2>/dev/null; then
        echo "✓ Virtual environment created successfully"
    else
        echo "⚠ python3-venv is not installed"
        echo ""
        echo "Please run this command first:"
        echo "  sudo apt install python3-venv"
        echo ""
        echo "Then run this setup script again."
        exit 1
    fi
fi

# Activate venv and install dependencies
echo ""
echo "Installing dependencies..."

# Check if we can activate venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    INSTALL_STATUS=$?
    
    if [ $INSTALL_STATUS -ne 0 ]; then
        echo ""
        echo "⚠ Installation failed!"
        echo ""
        echo "If you have Python 3.8, some packages may not be available."
        echo "Python 3.9+ is recommended for full compatibility."
        echo ""
        deactivate 2>/dev/null
        exit 1
    fi
else
    echo "⚠ Virtual environment activation failed"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp config.example.env .env
    echo ".env file created. Please edit it with your API keys."
else
    echo ""
    echo ".env file already exists. Skipping..."
fi

# Create logs directory
mkdir -p logs

# Deactivate venv for now
deactivate 2>/dev/null || true

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To use the bot:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Edit .env file with your configuration"
echo "3. Run the bot: python main.py"
echo ""
echo "For testing without API keys (dry run):"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "For testnet: Get keys from https://testnet.binancefuture.com/"
echo "For mainnet: ONLY after thorough testing!"
echo ""
echo "Read README.md for detailed instructions."
echo ""

