#!/bin/bash
# Fix Enhanced OCR Dependencies Issues

echo "=========================================="
echo "Fixing Enhanced OCR Dependencies"
echo "=========================================="
echo ""

# Activate virtual environment
cd "$(dirname "$0")"
source ../.venv/bin/activate

echo "Issue: NumPy 2.x is incompatible with OpenCV"
echo "Solution: Downgrade to NumPy 1.x"
echo ""

echo "Step 1: Uninstalling incompatible packages..."
pip uninstall -y opencv-python opencv-python-headless numpy

echo ""
echo "Step 2: Installing NumPy 1.x (compatible version)..."
pip install "numpy<2.0,>=1.21.0"

echo ""
echo "Step 3: Installing OpenCV (headless version, no GUI)..."
pip install opencv-python-headless==4.10.0.84

echo ""
echo "Step 4: Installing PyTorch (CPU version)..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo ""
echo "Step 5: Installing EasyOCR..."
pip install easyocr

echo ""
echo "=========================================="
echo "Testing installation..."
echo "=========================================="
echo ""

# Test imports
python3 << 'EOF'
import sys

print("Testing imports...\n")

# Test NumPy
try:
    import numpy as np
    print(f"✅ NumPy {np.__version__} installed successfully")
    if np.__version__.startswith('2.'):
        print("   ⚠️  Warning: NumPy 2.x detected, may cause issues")
except ImportError as e:
    print(f"❌ NumPy installation failed: {e}")
    sys.exit(1)

# Test OpenCV
try:
    import cv2
    print(f"✅ OpenCV {cv2.__version__} installed successfully")
except Exception as e:
    print(f"❌ OpenCV installation failed: {e}")
    sys.exit(1)

# Test PyTorch
try:
    import torch
    print(f"✅ PyTorch {torch.__version__} installed successfully")
except ImportError as e:
    print(f"❌ PyTorch installation failed: {e}")
    sys.exit(1)

# Test EasyOCR
try:
    import easyocr
    print(f"✅ EasyOCR installed successfully")
except Exception as e:
    print(f"❌ EasyOCR installation failed: {e}")
    print(f"   Error: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("✅ All dependencies installed successfully!")
print("="*50)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Enhanced OCR is ready to use!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Test with: python test_ocr_comparison.py image.jpg"
    echo "2. Enhanced OCR will be used automatically"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ Installation failed"
    echo "=========================================="
    echo ""
    echo "Please check the error messages above."
    echo ""
fi
