#!/bin/bash
# Combined Startup Script for Trabaholink
# Handles virtual environment, Playwright installation, and Celery startup

set -e  # Exit on error

echo "🚀 Trabaholink Startup Script"
echo "================================"
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/.venv"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found at: $VENV_DIR"
    echo "💡 Please create it first with: python3 -m venv $VENV_DIR"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated: $VIRTUAL_ENV"
echo ""

# Check Python version
echo "🐍 Python version:"
python --version
echo ""

# Check if Playwright is installed in the virtual environment
echo "🎭 Checking Playwright installation..."
if ! python -c "import playwright" 2>/dev/null; then
    echo "📦 Playwright not found in virtual environment. Installing..."
    pip install playwright
    echo ""
    
    # Install Playwright browsers
    echo "📥 Installing Playwright browsers (this may take a few minutes)..."
    python -m playwright install chromium
    
    if [ $? -eq 0 ]; then
        echo "✅ Playwright installed successfully!"
    else
        echo "❌ Failed to install Playwright browsers"
        exit 1
    fi
else
    echo "✅ Playwright already installed"
    
    # Check if browsers are installed
    if [ ! -d "$HOME/.cache/ms-playwright/chromium-"* ] 2>/dev/null; then
        echo "⚠️  Playwright browsers not found. Installing..."
        python -m playwright install chromium
    else
        echo "✅ Playwright browsers already installed"
    fi
fi
echo ""

# Install system dependencies for Ubuntu 24.04 (if needed)
echo "📦 Checking system dependencies for Ubuntu 24.04..."
echo "⚠️  This may require sudo password"
echo ""

# Check if we're on Ubuntu 24.04
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$VERSION_ID" == "24.04" ]]; then
        echo "Detected Ubuntu 24.04 - checking for t64 libraries..."
        
        # Check if key libraries are installed
        if ! dpkg -l | grep -q "libasound2t64"; then
            echo "Installing Ubuntu 24.04 system dependencies..."
            sudo apt-get update
            sudo apt-get install -y \
                libasound2t64 \
                libatk-bridge2.0-0t64 \
                libatk1.0-0t64 \
                libatspi2.0-0t64 \
                libcups2t64 \
                libdbus-1-3 \
                libdrm2 \
                libgbm1 \
                libglib2.0-0t64 \
                libgtk-3-0t64 \
                libnspr4 \
                libnss3 \
                libpango-1.0-0 \
                libx11-6 \
                libxcb1 \
                libxcomposite1 \
                libxdamage1 \
                libxext6 \
                libxfixes3 \
                libxkbcommon0 \
                libxrandr2 \
                libxshmfence1 \
                xvfb \
                fonts-liberation \
                fonts-noto-color-emoji \
                libu2f-udev \
                libvulkan1 \
                xdg-utils 2>/dev/null || true
        else
            echo "✅ System dependencies already installed"
        fi
    fi
fi
echo ""

# Display Playwright info
if [ -d "$HOME/.cache/ms-playwright" ]; then
    echo "📍 Playwright browsers location: $HOME/.cache/ms-playwright"
    echo "📊 Disk space used: $(du -sh "$HOME/.cache/ms-playwright" 2>/dev/null | cut -f1)"
    echo ""
fi

# Start Celery
echo "🔄 Starting Celery worker..."
echo "================================"
echo ""

cd "$SCRIPT_DIR"
exec python -m celery -A Trabaholink worker -l info
