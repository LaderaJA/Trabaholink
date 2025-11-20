#!/bin/bash
# Install Enhanced OCR Dependencies

echo "=========================================="
echo "Installing Enhanced OCR Dependencies"
echo "=========================================="
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
cd "$(dirname "$0")"
source ../.venv/bin/activate

echo ""
echo "Step 1: Downgrading NumPy to < 2.0 (required for OpenCV)..."
echo ""
pip install "numpy<2.0,>=1.21.0"

echo ""
echo "Step 2: Installing OpenCV..."
echo ""
pip install opencv-python-headless==4.10.0.84

echo ""
echo "Step 3: Installing PyTorch (this may take a few minutes)..."
echo ""
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo ""
echo "Step 4: Installing EasyOCR..."
echo ""
pip install easyocr

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Testing installation..."
echo ""

# Test imports
python3 << EOF
try:
    import easyocr
    print("✅ EasyOCR installed successfully")
except ImportError:
    print("❌ EasyOCR installation failed")

try:
    import cv2
    print("✅ OpenCV installed successfully")
except ImportError:
    print("❌ OpenCV installation failed")

try:
    import torch
    print("✅ PyTorch installed successfully")
except ImportError:
    print("❌ PyTorch installation failed")
EOF

echo ""
echo "=========================================="
echo "Enhanced OCR is ready to use!"
echo "=========================================="
echo ""
echo "Note: EasyOCR models (~500MB) will be downloaded"
echo "automatically on first use."
echo ""
echo "For GPU acceleration (optional, 5-10x faster):"
echo "  pip uninstall torch torchvision"
echo "  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118"
echo ""
