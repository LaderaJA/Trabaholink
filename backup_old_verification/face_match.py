"""Face detection and similarity utilities using `face_recognition` or OpenCV."""
from __future__ import annotations

import logging
import numpy as np
from typing import Tuple

try:
    import face_recognition
except ImportError:  # pragma: no cover - optional dependency
    face_recognition = None

try:
    import cv2
except ImportError:  # pragma: no cover - optional dependency
    cv2 = None

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD_VERIFIED = 0.6
SIMILARITY_THRESHOLD_MANUAL = 0.3


class FaceMatchError(RuntimeError):
    """Raised when face matching cannot be performed."""


def compute_similarity(id_image_path: str, selfie_image_path: str) -> Tuple[float, dict]:
    """Compute facial similarity between the ID and selfie images.

    Returns the similarity score in the range [0, 1] and debug metadata.
    Uses face_recognition if available, otherwise falls back to OpenCV.
    """

    # Try face_recognition first (more accurate)
    if face_recognition is not None:
        try:
            logger.info("Attempting face matching with face_recognition library (deep learning)")
            result = _compute_similarity_face_recognition(id_image_path, selfie_image_path)
            logger.info("Successfully used face_recognition library with score: %.4f", result[0])
            return result
        except FaceMatchError as e:
            logger.warning("face_recognition failed (no faces detected): %s, falling back to OpenCV", e)
        except Exception as e:
            logger.error("face_recognition failed with unexpected error: %s, falling back to OpenCV", e, exc_info=True)
    else:
        logger.warning("face_recognition library not available, using OpenCV fallback")
    
    # Fallback to OpenCV
    if cv2 is not None:
        logger.info("Using OpenCV for face matching (basic histogram method)")
        result = _compute_similarity_opencv(id_image_path, selfie_image_path)
        logger.info("OpenCV face matching completed with score: %.4f", result[0])
        return result
    
    raise FaceMatchError("Neither face_recognition nor OpenCV is available")


def _compute_similarity_face_recognition(id_image_path: str, selfie_image_path: str) -> Tuple[float, dict]:
    """Compute similarity using face_recognition library (deep learning based)."""
    logger.debug("Loading images for face_recognition")
    id_image = face_recognition.load_image_file(id_image_path)
    selfie_image = face_recognition.load_image_file(selfie_image_path)

    logger.debug("Detecting faces and computing encodings")
    # Use more robust face detection with model parameter
    id_encodings = face_recognition.face_encodings(id_image, model='large')
    selfie_encodings = face_recognition.face_encodings(selfie_image, model='large')

    if not id_encodings:
        raise FaceMatchError("Unable to locate face in ID image")
    if not selfie_encodings:
        raise FaceMatchError("Unable to locate face in selfie image")

    # Use the first detected face from each image
    id_encoding = id_encodings[0]
    selfie_encoding = selfie_encodings[0]

    # Compute face distance (lower is more similar)
    distance = face_recognition.face_distance([id_encoding], selfie_encoding)[0]
    
    # Convert distance to similarity score (0-1 range, higher is more similar)
    # face_recognition distance typically ranges from 0 (identical) to 1+ (very different)
    # We use 1 - distance, but cap at 0 for very different faces
    similarity = max(0.0, min(1.0, 1 - distance))

    logger.info("Face recognition similarity: %.4f (distance: %.4f, ID faces: %d, Selfie faces: %d)", 
                similarity, distance, len(id_encodings), len(selfie_encodings))
    
    return similarity, {
        "method": "face_recognition",
        "distance": float(distance),
        "similarity": float(similarity),
        "id_faces_detected": len(id_encodings),
        "selfie_faces_detected": len(selfie_encodings),
        "model": "large",
        "algorithm": "Deep Learning CNN (dlib)"
    }


def _compute_similarity_opencv(id_image_path: str, selfie_image_path: str) -> Tuple[float, dict]:
    """Compute similarity using OpenCV face detection and comparison."""
    # Load cascade classifier for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Read images
    id_image = cv2.imread(id_image_path)
    selfie_image = cv2.imread(selfie_image_path)
    
    if id_image is None or selfie_image is None:
        raise FaceMatchError("Unable to load one or both images")
    
    # Convert to grayscale
    id_gray = cv2.cvtColor(id_image, cv2.COLOR_BGR2GRAY)
    selfie_gray = cv2.cvtColor(selfie_image, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    id_faces = face_cascade.detectMultiScale(id_gray, 1.3, 5)
    selfie_faces = face_cascade.detectMultiScale(selfie_gray, 1.3, 5)
    
    if len(id_faces) == 0 or len(selfie_faces) == 0:
        raise FaceMatchError("Unable to locate faces in one or both images")
    
    # Extract the first face from each image
    id_x, id_y, id_w, id_h = id_faces[0]
    selfie_x, selfie_y, selfie_w, selfie_h = selfie_faces[0]
    
    id_face = id_gray[id_y:id_y+id_h, id_x:id_x+id_w]
    selfie_face = selfie_gray[selfie_y:selfie_y+selfie_h, selfie_x:selfie_x+selfie_w]
    
    # Resize to same dimensions for comparison
    target_size = (100, 100)
    id_face_resized = cv2.resize(id_face, target_size)
    selfie_face_resized = cv2.resize(selfie_face, target_size)
    
    # Compute histogram similarity
    id_hist = cv2.calcHist([id_face_resized], [0], None, [256], [0, 256])
    selfie_hist = cv2.calcHist([selfie_face_resized], [0], None, [256], [0, 256])
    
    # Normalize histograms
    cv2.normalize(id_hist, id_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    cv2.normalize(selfie_hist, selfie_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    
    # Compare histograms using correlation
    correlation = cv2.compareHist(id_hist, selfie_hist, cv2.HISTCMP_CORREL)
    
    # Also compute structural similarity using template matching
    result = cv2.matchTemplate(id_face_resized, selfie_face_resized, cv2.TM_CCOEFF_NORMED)
    template_score = np.max(result)
    
    # Combine both metrics (weighted average)
    similarity = (correlation * 0.6 + template_score * 0.4)
    
    # Ensure similarity is in [0, 1] range
    similarity = max(0.0, min(1.0, similarity))
    
    logger.debug("Face similarity computed (OpenCV): %s", similarity)
    return similarity, {
        "method": "opencv",
        "correlation": float(correlation),
        "template_score": float(template_score),
        "id_faces": len(id_faces),
        "selfie_faces": len(selfie_faces),
    }
