# ✅ Requirements Files Consolidated

## What Changed

### Before:
- `requirements.txt` - Core dependencies
- `requirements_enhanced_ocr.txt` - OCR dependencies
- `requirements_philsys.txt` - PhilSys verification dependencies

### After:
- **Single `requirements.txt`** - All dependencies organized by category

## Benefits

✅ **Easier to manage** - One file instead of three  
✅ **No redundancy** - Removed duplicate packages  
✅ **Better organized** - Clear sections with comments  
✅ **Version consistency** - No conflicting versions  
✅ **Faster Docker builds** - Single pip install command  

## What Was Removed/Updated

### Removed Duplicates:
- ❌ `numpy` (was in 3 files with different versions)
- ❌ `opencv-python-headless` (was in 3 files)
- ❌ `pytesseract` (was in 3 files)
- ❌ `pyzbar` (was in 2 files)
- ❌ `cryptography` (was in 2 files)
- ❌ `redis` (was in 2 files)
- ❌ `playwright` (was in 2 files)
- ❌ `Pillow` (was in 2 files)

### Version Resolution:
- ✅ `numpy<2.0,>=1.21.0` - For OpenCV compatibility
- ✅ `opencv-python-headless==4.10.0.84` - Latest stable
- ✅ `playwright==1.49.1` - Latest version
- ✅ `cryptography==44.0.1` - Latest version
- ✅ `redis==5.2.1` - Latest version

### Added (from enhanced_ocr):
- ✅ `torch>=2.2.0` - For EasyOCR deep learning
- ✅ `torchvision>=0.17.0` - PyTorch vision library
- ✅ `easyocr>=1.7.0` - Advanced OCR capability

### Added (from philsys):
- ✅ `celery==5.3.4` - Async task queue

## Files Updated

1. ✅ `requirements.txt` - Consolidated and organized
2. ✅ `Dockerfile` - Updated to use single requirements file
3. ✅ Removed old files:
   - `requirements_enhanced_ocr.txt`
   - `requirements_philsys.txt`
   - `requirements_philsys_fixed.txt`

## Docker Build

The Dockerfile now has a simpler installation:

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
```

Instead of:

```dockerfile
COPY requirements.txt .
COPY requirements_enhanced_ocr.txt .
COPY requirements_philsys.txt .
RUN pip install -r requirements.txt && \
    pip install -r requirements_enhanced_ocr.txt && \
    pip install -r requirements_philsys.txt
```

## Total Package Count

**87 packages** organized into 13 categories:
1. Core Django & Web Framework (5)
2. ASGI & WebSocket Support (4)
3. Async & Task Queue (2)
4. Database (1)
5. Geospatial (3)
6. Authentication & Security (7)
7. Image Processing & Computer Vision (3)
8. OCR (4)
9. Face Recognition (3)
10. QR Code & Barcode (1)
11. Browser Automation (1)
12. Email (4)
13. Utilities & Dependencies (49)

## Next Steps

1. Test the build: `sudo docker-compose build --no-cache`
2. Verify all dependencies install correctly
3. Test application functionality

## Notes

- NumPy version is locked to `<2.0` for OpenCV compatibility
- OpenCV uses headless version for Docker (no GUI dependencies)
- Playwright browsers need to be installed after pip: `playwright install chromium`
- For GPU acceleration with EasyOCR, see instructions in requirements.txt

