#!/usr/bin/env python3
"""
Diagnostic tool for OCR issues - saves preprocessed images for inspection.

Usage:
    python diagnose_ocr.py path/to/id_image.jpg
"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')

import django
django.setup()

from PIL import Image
import cv2
import numpy as np


def save_preprocessed_images(image_path, output_dir="ocr_debug"):
    """Save all preprocessing steps for visual inspection."""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n🔍 Diagnosing OCR for: {image_path}")
    print(f"📁 Saving preprocessed images to: {output_dir}/")
    print("="*80)
    
    # Load image
    image = Image.open(image_path)
    img_array = np.array(image)
    
    # Convert to grayscale
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Save original
    cv2.imwrite(f"{output_dir}/00_original.png", gray)
    print("✅ Saved: 00_original.png")
    
    # STEP 1: Resize if needed
    height, width = gray.shape
    print(f"\n📐 Original size: {width}x{height}")
    
    if width < 1500:
        scale = 1500 / width
        new_width = int(width * scale)
        new_height = int(height * scale)
        gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(f"{output_dir}/01_resized.png", gray)
        print(f"✅ Saved: 01_resized.png ({new_width}x{new_height})")
    
    # STEP 2: Deskew
    try:
        coords = np.column_stack(np.where(gray > 0))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            if abs(angle) > 0.5:
                (h, w) = gray.shape
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                cv2.imwrite(f"{output_dir}/02_deskewed.png", gray)
                print(f"✅ Saved: 02_deskewed.png (rotated {angle:.2f}°)")
    except Exception as e:
        print(f"⚠️  Deskew failed: {e}")
    
    # STEP 3: Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, h=20, templateWindowSize=7, searchWindowSize=21)
    cv2.imwrite(f"{output_dir}/03_denoised.png", denoised)
    print("✅ Saved: 03_denoised.png")
    
    # STEP 4: Otsu threshold
    _, otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(f"{output_dir}/04_otsu_threshold.png", otsu)
    print("✅ Saved: 04_otsu_threshold.png")
    
    # STEP 5: Adaptive threshold (Gaussian)
    adaptive1 = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 11
    )
    cv2.imwrite(f"{output_dir}/05_adaptive_gaussian.png", adaptive1)
    print("✅ Saved: 05_adaptive_gaussian.png")
    
    # STEP 6: Adaptive threshold (Mean)
    adaptive2 = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 8
    )
    cv2.imwrite(f"{output_dir}/06_adaptive_mean.png", adaptive2)
    print("✅ Saved: 06_adaptive_mean.png")
    
    # STEP 7: CLAHE
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    cv2.imwrite(f"{output_dir}/07_clahe.png", enhanced)
    print("✅ Saved: 07_clahe.png")
    
    _, clahe_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(f"{output_dir}/08_clahe_threshold.png", clahe_thresh)
    print("✅ Saved: 08_clahe_threshold.png")
    
    # STEP 8: Morphological closing
    kernel_rect = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    morph_close = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel_rect, iterations=1)
    cv2.imwrite(f"{output_dir}/09_morph_close.png", morph_close)
    print("✅ Saved: 09_morph_close.png")
    
    # STEP 9: Morphological opening
    morph_open = cv2.morphologyEx(otsu, cv2.MORPH_OPEN, kernel_rect, iterations=1)
    cv2.imwrite(f"{output_dir}/10_morph_open.png", morph_open)
    print("✅ Saved: 10_morph_open.png")
    
    # STEP 10: Sharpening
    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
    _, sharp_thresh = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(f"{output_dir}/11_sharpened.png", sharp_thresh)
    print("✅ Saved: 11_sharpened.png")
    
    # STEP 11: Inverted
    _, inverted = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cv2.imwrite(f"{output_dir}/12_inverted.png", inverted)
    print("✅ Saved: 12_inverted.png")
    
    # STEP 12: Bilateral filter
    bilateral = cv2.bilateralFilter(denoised, 9, 75, 75)
    _, bilateral_thresh = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(f"{output_dir}/13_bilateral.png", bilateral_thresh)
    print("✅ Saved: 13_bilateral.png")
    
    # STEP 13: High contrast
    normalized = cv2.normalize(denoised, None, 0, 255, cv2.NORM_MINMAX)
    _, high_contrast = cv2.threshold(normalized, 127, 255, cv2.THRESH_BINARY)
    cv2.imwrite(f"{output_dir}/14_high_contrast.png", high_contrast)
    print("✅ Saved: 14_high_contrast.png")
    
    print("\n" + "="*80)
    print(f"✅ All preprocessing steps saved to: {output_dir}/")
    print("\n📋 Next steps:")
    print("1. Open the images in the folder")
    print("2. Find which preprocessing step gives the clearest text")
    print("3. That's the version Tesseract should work best on")
    print("\n💡 Tips:")
    print("- Look for clear, black text on white background")
    print("- Text should be sharp and well-defined")
    print("- No noise or artifacts around text")
    print("- If all images look bad, the original photo quality is too poor")
    print("="*80 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose_ocr.py path/to/id_image.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    save_preprocessed_images(image_path)


if __name__ == "__main__":
    main()
