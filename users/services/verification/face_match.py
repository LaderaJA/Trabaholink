"""
Enhanced Face Recognition Module V2
Improved face detection and matching with multiple algorithms
"""
import logging
import numpy as np
from typing import Tuple, Dict, Optional
from PIL import Image
import cv2

logger = logging.getLogger(__name__)

# Try to import face_recognition (dlib-based)
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition library not available, using OpenCV only")

# Similarity thresholds
SIMILARITY_THRESHOLD_VERIFIED = 0.60  # Auto-verify threshold
SIMILARITY_THRESHOLD_MANUAL = 0.40    # Manual review threshold


class FaceMatchError(RuntimeError):
    """Raised when face matching cannot be performed."""
    pass


class FaceMatcherV2:
    """Enhanced face matching with improved preprocessing and multiple algorithms."""
    
    def __init__(self):
        """Initialize face matcher with cascade classifiers."""
        # Load Haar cascades for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
        logger.info("FaceMatcherV2 initialized (memory-optimized)")
    
    def _resize_image_if_needed(self, image: np.ndarray, max_dimension: int = 1200) -> np.ndarray:
        """
        Resize image if it exceeds max dimension to save memory.
        Face recognition doesn't need ultra-high resolution images.
        """
        height, width = image.shape[:2]
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height} for memory optimization")
            return resized
        return image
    
    def preprocess_image(self, image_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load and preprocess image for face detection.
        Returns both color and grayscale versions.
        """
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise FaceMatchError(f"Unable to load image: {image_path}")
        
        # Resize if too large (for performance) or too small (for better detection)
        height, width = img.shape[:2]
        max_dimension = 1024
        min_dimension = 300
        
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")
        elif max(height, width) < min_dimension:
            # Upscale small images for better face detection
            scale = min_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            logger.info(f"Upscaled small image from {width}x{height} to {new_width}x{new_height}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Enhance contrast with more aggressive CLAHE for difficult images
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced_gray, None, h=10)
        
        return img, denoised
    
    def detect_faces_opencv(self, image: np.ndarray, gray: np.ndarray) -> list:
        """
        Detect faces using OpenCV Haar cascades with multiple attempts.
        Returns list of face rectangles.
        """
        # Try with default parameters first
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # If no faces found, try with more lenient parameters
        if len(faces) == 0:
            logger.info("No faces with default params, trying lenient detection")
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,  # Smaller scale factor = more thorough
                minNeighbors=3,     # Lower threshold = more detections
                minSize=(20, 20),   # Smaller minimum face size
                flags=cv2.CASCADE_SCALE_IMAGE
            )
        
        # Filter faces by eye detection (more reliable)
        valid_faces = []
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=5)
            
            # Valid face should have at least 1 eye detected
            if len(eyes) > 0:
                valid_faces.append((x, y, w, h))
        
        # If no valid faces, return all detected faces
        if len(valid_faces) == 0:
            valid_faces = list(faces)
        
        logger.info(f"Detected {len(valid_faces)} valid faces (out of {len(faces)} detected)")
        return valid_faces
    
    def extract_face_region(self, image: np.ndarray, face_rect: tuple) -> np.ndarray:
        """Extract and normalize face region."""
        x, y, w, h = face_rect
        
        # Add padding
        padding = int(0.2 * min(w, h))
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = w + 2 * padding
        h = h + 2 * padding
        
        # Ensure we don't exceed image boundaries
        y_end = min(image.shape[0], y + h)
        x_end = min(image.shape[1], x + w)
        
        face = image[y:y_end, x:x_end]
        
        # Resize to standard size
        face_resized = cv2.resize(face, (128, 128))
        
        return face_resized
    
    def compute_similarity_deep_learning(self, id_path: str, selfie_path: str) -> Tuple[float, Dict]:
        """
        Compute similarity using face_recognition library (deep learning).
        This is the most accurate method.
        
        OPTIMIZED: Uses HOG model instead of CNN to reduce memory usage from ~1.5GB to ~200MB
        """
        if not FACE_RECOGNITION_AVAILABLE:
            raise FaceMatchError("face_recognition library not available")
        
        logger.info("Using deep learning face recognition (dlib) with HOG model")
        
        try:
            # Load images
            id_image = face_recognition.load_image_file(id_path)
            selfie_image = face_recognition.load_image_file(selfie_path)
            
            # Resize images to reduce memory footprint
            # Max dimension of 1200px is sufficient for face recognition
            id_image = self._resize_image_if_needed(id_image, max_dimension=1200)
            selfie_image = self._resize_image_if_needed(selfie_image, max_dimension=1200)
            
            # Detect faces and compute encodings
            # Use 'hog' model instead of 'cnn' - much faster and less memory intensive
            # HOG is accurate enough for PhilSys ID verification (85%+ accuracy vs 95% for CNN)
            # Try with upsampling=1 first, then increase if no faces found
            id_face_locations = face_recognition.face_locations(id_image, model='hog', number_of_times_to_upsample=1)
            if not id_face_locations:
                # Retry with more upsampling for difficult images
                logger.info("No faces detected with upsample=1, retrying with upsample=2")
                id_face_locations = face_recognition.face_locations(id_image, model='hog', number_of_times_to_upsample=2)
            
            selfie_face_locations = face_recognition.face_locations(selfie_image, model='hog', number_of_times_to_upsample=1)
            if not selfie_face_locations:
                logger.info("No faces detected in selfie with upsample=1, retrying with upsample=2")
                selfie_face_locations = face_recognition.face_locations(selfie_image, model='hog', number_of_times_to_upsample=2)
            
            if not id_face_locations:
                raise FaceMatchError("No face detected in ID image")
            if not selfie_face_locations:
                raise FaceMatchError("No face detected in selfie image")
            
            # Get encodings using 'small' model (default) - faster and less memory
            # Small model is sufficient for ID verification tasks
            id_encodings = face_recognition.face_encodings(id_image, id_face_locations, num_jitters=1)
            selfie_encodings = face_recognition.face_encodings(selfie_image, selfie_face_locations, num_jitters=1)
            
            if not id_encodings or not selfie_encodings:
                raise FaceMatchError("Failed to generate face encodings")
            
            # Use first detected face
            id_encoding = id_encodings[0]
            selfie_encoding = selfie_encodings[0]
            
            # Compute face distance
            distance = face_recognition.face_distance([id_encoding], selfie_encoding)[0]
            
            # Convert distance to similarity (0-1, higher is more similar)
            # Typical distance range: 0 (identical) to 1+ (very different)
            # We use sigmoid-like function for better scaling
            similarity = 1 / (1 + distance)
            
            # Also compute boolean match
            matches = face_recognition.compare_faces([id_encoding], selfie_encoding, tolerance=0.6)
            is_match = matches[0]
            
            logger.info(f"Deep learning similarity: {similarity:.4f}, distance: {distance:.4f}, match: {is_match}")
            
            return similarity, {
                'method': 'deep_learning_hog',
                'algorithm': 'dlib face recognition (HOG + small model)',
                'distance': float(distance),
                'similarity': float(similarity),
                'is_match': bool(is_match),
                'id_faces_detected': len(id_face_locations),
                'selfie_faces_detected': len(selfie_face_locations),
                'model': 'hog+small',
                'confidence': 'high',
                'memory_optimized': True
            }
            
        except FaceMatchError:
            raise
        except Exception as e:
            logger.exception(f"Deep learning face recognition failed: {e}")
            raise FaceMatchError(f"Deep learning method failed: {e}")
    
    def compute_similarity_opencv_advanced(self, id_path: str, selfie_path: str) -> Tuple[float, Dict]:
        """
        Advanced OpenCV-based face matching using multiple techniques.
        """
        logger.info("Using advanced OpenCV face matching")
        
        # Preprocess images
        id_img, id_gray = self.preprocess_image(id_path)
        selfie_img, selfie_gray = self.preprocess_image(selfie_path)
        
        # Detect faces
        id_faces = self.detect_faces_opencv(id_img, id_gray)
        selfie_faces = self.detect_faces_opencv(selfie_img, selfie_gray)
        
        if len(id_faces) == 0:
            raise FaceMatchError("No face detected in ID image")
        if len(selfie_faces) == 0:
            raise FaceMatchError("No face detected in selfie image")
        
        # Extract face regions
        id_face = self.extract_face_region(id_gray, id_faces[0])
        selfie_face = self.extract_face_region(selfie_gray, selfie_faces[0])
        
        # Method 1: Histogram correlation
        id_hist = cv2.calcHist([id_face], [0], None, [256], [0, 256])
        selfie_hist = cv2.calcHist([selfie_face], [0], None, [256], [0, 256])
        cv2.normalize(id_hist, id_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        cv2.normalize(selfie_hist, selfie_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        hist_similarity = cv2.compareHist(id_hist, selfie_hist, cv2.HISTCMP_CORREL)
        
        # Method 2: Template matching
        if id_face.shape == selfie_face.shape:
            result = cv2.matchTemplate(id_face, selfie_face, cv2.TM_CCOEFF_NORMED)
            template_score = np.max(result)
        else:
            template_score = 0
        
        # Method 3: Structural Similarity (SSIM)
        ssim_score = self.compute_ssim(id_face, selfie_face)
        
        # Method 4: Feature matching with ORB
        orb_score = self.compute_orb_similarity(id_face, selfie_face)
        
        # Combine scores with weights
        weights = {
            'histogram': 0.25,
            'template': 0.20,
            'ssim': 0.30,
            'orb': 0.25
        }
        
        combined_similarity = (
            hist_similarity * weights['histogram'] +
            template_score * weights['template'] +
            ssim_score * weights['ssim'] +
            orb_score * weights['orb']
        )
        
        # Ensure in valid range
        combined_similarity = max(0.0, min(1.0, combined_similarity))
        
        logger.info(f"OpenCV similarity: {combined_similarity:.4f} "
                   f"(hist={hist_similarity:.2f}, template={template_score:.2f}, "
                   f"ssim={ssim_score:.2f}, orb={orb_score:.2f})")
        
        return combined_similarity, {
            'method': 'opencv_advanced',
            'algorithm': 'Multi-metric ensemble',
            'histogram_correlation': float(hist_similarity),
            'template_matching': float(template_score),
            'ssim': float(ssim_score),
            'orb_matching': float(orb_score),
            'similarity': float(combined_similarity),
            'id_faces_detected': len(id_faces),
            'selfie_faces_detected': len(selfie_faces),
            'confidence': 'medium'
        }
    
    def compute_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Compute Structural Similarity Index (SSIM)."""
        # Ensure same size
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        # Compute SSIM
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2
        
        img1 = img1.astype(np.float64)
        img2 = img2.astype(np.float64)
        
        mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)
        
        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2
        
        sigma1_sq = cv2.GaussianBlur(img1 ** 2, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(img2 ** 2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu1_mu2
        
        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
        
        return float(ssim_map.mean())
    
    def compute_orb_similarity(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Compute similarity using ORB feature matching."""
        try:
            # Initialize ORB detector
            orb = cv2.ORB_create(nfeatures=500)
            
            # Detect keypoints and compute descriptors
            kp1, des1 = orb.detectAndCompute(img1, None)
            kp2, des2 = orb.detectAndCompute(img2, None)
            
            if des1 is None or des2 is None or len(kp1) < 2 or len(kp2) < 2:
                return 0.0
            
            # Match features using BFMatcher
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            
            # Sort matches by distance
            matches = sorted(matches, key=lambda x: x.distance)
            
            # Calculate similarity based on good matches
            good_matches = [m for m in matches if m.distance < 50]
            similarity = len(good_matches) / max(len(kp1), len(kp2))
            
            return min(1.0, similarity)
            
        except Exception as e:
            logger.debug(f"ORB matching failed: {e}")
            return 0.0
    
    def compute_similarity(self, id_path: str, selfie_path: str) -> Tuple[float, Dict]:
        """
        Main method to compute face similarity.
        Tries deep learning first, falls back to OpenCV if unavailable.
        """
        # Try deep learning method (most accurate)
        if FACE_RECOGNITION_AVAILABLE:
            try:
                return self.compute_similarity_deep_learning(id_path, selfie_path)
            except FaceMatchError as e:
                logger.warning(f"Deep learning method failed: {e}, falling back to OpenCV")
            except Exception as e:
                logger.error(f"Deep learning method error: {e}, falling back to OpenCV")
        
        # Fallback to OpenCV
        return self.compute_similarity_opencv_advanced(id_path, selfie_path)


# Convenience function for backward compatibility
def compute_similarity(id_image_path: str, selfie_image_path: str) -> Tuple[float, dict]:
    """
    Compute facial similarity between ID and selfie images.
    Returns (similarity_score, metadata_dict).
    """
    matcher = FaceMatcherV2()
    return matcher.compute_similarity(id_image_path, selfie_image_path)
