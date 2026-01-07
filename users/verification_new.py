"""
New ID verification flow using QR code + OCR + Face matching.
Replaces the Playwright automation which violated verify.philsys.gov.ph terms of use.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from PIL import Image
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def verify_philsys_id_offline(
    id_front_path: str,
    id_back_path: str,
    selfie_path: str,
    user_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Verify PhilSys ID using offline methods (no portal automation).
    
    Flow:
    1. Extract QR code from back of ID
    2. Parse QR data to get person information
    3. Compare QR data with user input
    4. Extract face from ID front
    5. Match face from ID with selfie
    6. Calculate verification score
    7. Auto-approve or reject based on score
    
    Args:
        id_front_path: Path to front of PhilSys ID
        id_back_path: Path to back of PhilSys ID (with QR code)
        selfie_path: Path to user's selfie photo
        user_data: Dict with user's submitted data (name, dob, gender, etc.)
        
    Returns:
        Dict with verification result, score, and decision
    """
    result = {
        'success': False,
        'decision': 'pending',
        'overall_score': 0.0,
        'qr_data': {},
        'ocr_data': {},
        'face_match_score': 0.0,
        'data_match_score': 0.0,
        'matches': [],
        'mismatches': [],
        'error': None
    }
    
    try:
        # Step 1: Extract and parse QR code from back of ID
        logger.info("Step 1: Extracting QR code from ID back...")
        qr_result = extract_and_parse_qr_code(id_back_path)
        
        if not qr_result['success']:
            logger.warning(f"QR extraction failed: {qr_result.get('error')}")
            result['error'] = f"QR code extraction failed: {qr_result.get('error')}"
            # Continue without QR data - we can still use OCR
        else:
            result['qr_data'] = qr_result['data']
            logger.info(f"QR data extracted: {qr_result['data'].keys()}")
        
        # Step 2: Extract data from ID front using OCR (as backup)
        logger.info("Step 2: Extracting text from ID front using OCR...")
        ocr_result = extract_ocr_data_from_id(id_front_path)
        
        if ocr_result['success']:
            result['ocr_data'] = ocr_result['data']
            logger.info(f"OCR data extracted: {ocr_result['data'].keys()}")
        else:
            logger.warning(f"OCR extraction failed: {ocr_result.get('error')}")
        
        # Step 3: Compare extracted data with user input
        logger.info("Step 3: Comparing extracted data with user input...")
        
        # Prefer QR data over OCR data (QR is more reliable)
        extracted_data = result['qr_data'] if result['qr_data'] else result['ocr_data']
        
        if not extracted_data:
            result['error'] = "Failed to extract data from ID (both QR and OCR failed)"
            return result
        
        data_comparison = compare_data_fields(user_data, extracted_data)
        result['data_match_score'] = data_comparison['match_score']
        result['matches'] = data_comparison['matches']
        result['mismatches'] = data_comparison['mismatches']
        
        logger.info(f"Data match score: {data_comparison['match_score']:.2%}")
        logger.info(f"Matches: {len(data_comparison['matches'])}")
        logger.info(f"Mismatches: {len(data_comparison['mismatches'])}")
        
        # Step 4: Face matching
        logger.info("Step 4: Comparing face from ID with selfie...")
        face_result = compare_faces(id_front_path, selfie_path)
        
        if face_result['success']:
            result['face_match_score'] = face_result['similarity']
            logger.info(f"Face match score: {face_result['similarity']:.2%}")
        else:
            logger.warning(f"Face matching failed: {face_result.get('error')}")
            result['face_match_score'] = 0.0
        
        # Step 5: Calculate overall verification score
        # Weighted scoring: Data (60%) + Face (40%)
        data_weight = 0.6
        face_weight = 0.4
        
        overall_score = (
            result['data_match_score'] * data_weight +
            result['face_match_score'] * face_weight
        )
        result['overall_score'] = overall_score
        
        logger.info(f"Overall verification score: {overall_score:.2%}")
        
        # Step 6: Make decision based on score
        # Thresholds:
        # - >= 80%: Auto-approve
        # - 60-79%: Pending (manual review)
        # - < 60%: Auto-reject
        
        if overall_score >= 0.80:
            result['decision'] = 'approved'
            result['success'] = True
            logger.info("✅ DECISION: AUTO-APPROVE (score >= 80%)")
        elif overall_score >= 0.60:
            result['decision'] = 'pending'
            result['success'] = True
            logger.info("⚠️  DECISION: MANUAL REVIEW (score 60-79%)")
        else:
            result['decision'] = 'rejected'
            result['success'] = True
            logger.info("❌ DECISION: AUTO-REJECT (score < 60%)")
        
        return result
        
    except Exception as e:
        logger.exception(f"Error in offline verification: {e}")
        result['error'] = str(e)
        return result


def extract_and_parse_qr_code(id_back_path: str) -> Dict[str, Any]:
    """
    Extract QR code from back of PhilSys ID and parse the data.
    
    Returns:
        Dict with success flag and parsed data
    """
    try:
        from users.services.verification.qr import extract_qr_data
        from PIL import Image
        
        # Load image
        img = Image.open(id_back_path)
        
        # Extract QR data
        qr_data = extract_qr_data(img)
        
        if not qr_data:
            return {
                'success': False,
                'error': 'No QR code found in image',
                'data': {}
            }
        
        # Parse the QR data
        parsed_data = parse_philsys_qr_data(qr_data)
        
        return {
            'success': True,
            'data': parsed_data,
            'raw_qr': qr_data.get('qr_raw', '')
        }
        
    except ImportError as e:
        logger.error(f"pyzbar not installed: {e}")
        return {
            'success': False,
            'error': 'QR code library not installed (pyzbar)',
            'data': {}
        }
    except Exception as e:
        logger.exception(f"Error extracting QR code: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': {}
        }


def parse_philsys_qr_data(qr_data: Dict[str, str]) -> Dict[str, str]:
    """
    Parse PhilSys QR code data into structured fields.
    
    PhilSys QR codes typically contain:
    - PCN (PhilSys Card Number)
    - Full Name
    - Date of Birth
    - Sex
    - Address
    - Date of Issuance
    
    The QR raw data may be in format:
    PCN: 1234-5678-9012-3456
    Name: DELA CRUZ, JUAN PEDRO
    DOB: 1990-01-15
    Sex: MALE
    ...
    """
    parsed = {}
    
    # The extract_qr_data already does basic parsing
    # We just need to normalize field names
    
    field_mapping = {
        'pcn': 'pcn',
        'philsys_card_number': 'pcn',
        'name': 'full_name',
        'full_name': 'full_name',
        'date_of_birth': 'date_of_birth',
        'dob': 'date_of_birth',
        'birth_date': 'date_of_birth',
        'sex': 'gender',
        'gender': 'gender',
        'address': 'address',
        'date_of_issuance': 'date_issued',
        'issue_date': 'date_issued',
    }
    
    for key, value in qr_data.items():
        if key == 'qr_raw':
            continue
        
        # Normalize key
        normalized_key = field_mapping.get(key.lower(), key.lower())
        parsed[normalized_key] = value
    
    # If we have raw QR data but no parsed fields, try to extract from raw
    if not parsed and 'qr_raw' in qr_data:
        raw = qr_data['qr_raw']
        parsed = extract_from_raw_qr_text(raw)
    
    return parsed


def extract_from_raw_qr_text(raw_text: str) -> Dict[str, str]:
    """
    Extract fields from raw QR code text using pattern matching.
    """
    import re
    
    data = {}
    
    patterns = {
        'pcn': r'(?:PCN|PhilSys Card Number)[:\s]*([0-9\-]+)',
        'full_name': r'(?:Name|Full Name)[:\s]*([^\n]+)',
        'date_of_birth': r'(?:DOB|Date of Birth|Birth Date)[:\s]*([^\n]+)',
        'gender': r'(?:Sex|Gender)[:\s]*([^\n]+)',
        'address': r'(?:Address)[:\s]*([^\n]+)',
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            data[field] = match.group(1).strip()
    
    return data


def extract_ocr_data_from_id(id_front_path: str) -> Dict[str, Any]:
    """
    Extract text data from ID front using OCR as backup to QR code.
    Optimized: Resize image before OCR to speed up processing.
    """
    try:
        from users.services.verification.ocr_philsys import PhilSysOCRV2
        from PIL import Image
        
        # Load image
        img = Image.open(id_front_path)
        
        # OPTIMIZATION: Resize if too large (speeds up OCR significantly)
        max_dimension = 1200  # Max width or height
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Resized image from {Image.open(id_front_path).size} to {new_size} for faster OCR")
        
        # Extract data using PhilSys OCR
        ocr = PhilSysOCRV2()
        data = ocr.extract_philsys_data(img)
        
        if not data:
            return {
                'success': False,
                'error': 'No data extracted from OCR',
                'data': {}
            }
        
        # Normalize field names to match QR data
        normalized = {
            'full_name': data.get('full_name') or data.get('name'),
            'date_of_birth': data.get('date_of_birth'),
            'gender': data.get('sex'),
            'address': data.get('address'),
            'pcn': data.get('pcn'),
        }
        
        # Remove None values
        normalized = {k: v for k, v in normalized.items() if v}
        
        return {
            'success': True,
            'data': normalized
        }
        
    except Exception as e:
        logger.exception(f"Error extracting OCR data: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': {}
        }


def compare_data_fields(user_data: Dict[str, Any], extracted_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Compare user's input data with extracted data from ID.
    
    Returns match score and details of matches/mismatches.
    """
    matches = []
    mismatches = []
    field_scores = []
    
    # Debug: Log what data we have
    logger.info(f"User data keys: {list(user_data.keys())}")
    logger.info(f"Extracted data keys: {list(extracted_data.keys())}")
    
    # Compare full name (most important - weight: 40%)
    if 'full_name' in extracted_data and user_data.get('full_name'):
        user_name = str(user_data['full_name']).upper().strip()
        extracted_name = str(extracted_data['full_name']).upper().strip()
        
        similarity = calculate_string_similarity(user_name, extracted_name)
        field_scores.append(similarity * 0.4)  # 40% weight
        
        logger.info(f"Name comparison: '{user_name}' vs '{extracted_name}' = {similarity:.2%}")
        
        if similarity >= 0.75:  # 75% threshold for names
            matches.append(f"Name matches ({int(similarity*100)}%)")
        else:
            mismatches.append(f"Name mismatch: '{user_name}' vs '{extracted_name}'")
    else:
        logger.warning(f"Name comparison skipped - extracted: {'full_name' in extracted_data}, user: {bool(user_data.get('full_name'))}")
    
    # Compare date of birth (important - weight: 30%)  
    if 'date_of_birth' in extracted_data and user_data.get('date_of_birth'):
        user_dob = normalize_date_for_comparison(str(user_data['date_of_birth']))
        extracted_dob = normalize_date_for_comparison(str(extracted_data['date_of_birth']))
        
        logger.info(f"DOB comparison: '{user_dob}' vs '{extracted_dob}'")
        
        if user_dob == extracted_dob:
            matches.append("Date of birth matches")
            field_scores.append(0.3)  # 30% weight
        else:
            mismatches.append(f"DOB mismatch: '{user_dob}' vs '{extracted_dob}'")
            field_scores.append(0.0)
    
    # Compare gender (moderate - weight: 20%)
    if 'gender' in extracted_data and user_data.get('gender'):
        user_gender = str(user_data['gender']).lower().strip()
        extracted_gender = str(extracted_data['gender']).lower().strip()
        
        logger.info(f"Gender comparison: '{user_gender}' vs '{extracted_gender}'")
        
        # Check if one contains the other (e.g., "male" in "male")
        if user_gender in extracted_gender or extracted_gender in user_gender:
            matches.append("Gender matches")
            field_scores.append(0.2)  # 20% weight
        else:
            mismatches.append(f"Gender mismatch: '{user_gender}' vs '{extracted_gender}'")
            field_scores.append(0.0)
    
    # Compare address (optional - weight: 10%)
    if 'address' in extracted_data and user_data.get('address'):
        user_addr = str(user_data['address']).upper().strip()
        extracted_addr = str(extracted_data['address']).upper().strip()
        
        similarity = calculate_string_similarity(user_addr, extracted_addr)
        field_scores.append(similarity * 0.1)  # 10% weight
        
        logger.info(f"Address comparison: similarity = {similarity:.2%}")
        
        if similarity >= 0.60:  # Lower threshold for addresses (they can be formatted differently)
            matches.append(f"Address matches ({int(similarity*100)}%)")
        else:
            mismatches.append(f"Address mismatch")
    
    # Calculate overall match score
    match_score = sum(field_scores) if field_scores else 0.0
    
    logger.info(f"Field scores: {field_scores}, Total: {match_score:.2%}")
    logger.info(f"Total matches: {len(matches)}, Total mismatches: {len(mismatches)}")
    
    return {
        'match_score': match_score,
        'matches': matches,
        'mismatches': mismatches,
        'total_checks': len(matches) + len(mismatches)
    }


def compare_faces(id_front_path: str, selfie_path: str) -> Dict[str, Any]:
    """
    Compare face from ID with selfie photo.
    Optimized: Resize images before face detection to speed up processing.
    
    Returns similarity score (0.0 to 1.0).
    """
    import tempfile
    import os
    
    try:
        from users.services.verification.face_match import compare_face_images
        from PIL import Image
        
        # OPTIMIZATION: Resize images to speed up face detection
        max_size = 800  # Resize to max 800px
        
        # Resize ID image
        id_img = Image.open(id_front_path)
        if max(id_img.size) > max_size:
            ratio = max_size / max(id_img.size)
            new_size = tuple(int(dim * ratio) for dim in id_img.size)
            id_img = id_img.resize(new_size, Image.Resampling.LANCZOS)
            # Save to temp file
            temp_id = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            id_img.save(temp_id.name, 'JPEG')
            id_path = temp_id.name
            logger.info(f"Resized ID image for faster face detection: {new_size}")
        else:
            id_path = id_front_path
        
        # Resize selfie image
        selfie_img = Image.open(selfie_path)
        if max(selfie_img.size) > max_size:
            ratio = max_size / max(selfie_img.size)
            new_size = tuple(int(dim * ratio) for dim in selfie_img.size)
            selfie_img = selfie_img.resize(new_size, Image.Resampling.LANCZOS)
            # Save to temp file
            temp_selfie = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            selfie_img.save(temp_selfie.name, 'JPEG')
            selfie_path_resized = temp_selfie.name
            logger.info(f"Resized selfie image for faster face detection: {new_size}")
        else:
            selfie_path_resized = selfie_path
        
        # Compare faces (no signal.alarm - it breaks Celery workers!)
        logger.info("Starting face comparison...")
        result = compare_face_images(id_path, selfie_path_resized)
        logger.info(f"Face comparison complete: {result.get('similarity', 0):.2%}")
        
        # Clean up temp files
        try:
            if id_path != id_front_path and os.path.exists(id_path):
                os.unlink(id_path)
            if selfie_path_resized != selfie_path and os.path.exists(selfie_path_resized):
                os.unlink(selfie_path_resized)
        except:
            pass
        
        return {
            'success': True,
            'similarity': result.get('similarity', 0.0),
            'match': result.get('match', False),
            'details': result
        }
        
    except Exception as e:
        logger.exception(f"Error comparing faces: {e}")
        return {
            'success': False,
            'error': str(e),
            'similarity': 0.0
        }


def calculate_string_similarity(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, str1, str2).ratio()


def normalize_date_for_comparison(date_str: str) -> str:
    """
    Normalize date string to YYYY-MM-DD format for comparison.
    Handles multiple date formats.
    """
    from datetime import datetime
    import re
    
    if not date_str:
        return ''
    
    date_str = str(date_str).strip()
    
    # List of formats to try
    formats = [
        '%Y-%m-%d',           # 1995-01-09
        '%B %d, %Y',          # September 01, 1995
        '%b %d, %Y',          # Sep 01, 1995
        '%m/%d/%Y',           # 09/01/1995
        '%d/%m/%Y',           # 01/09/1995
        '%Y/%m/%d',           # 1995/09/01
        '%d-%m-%Y',           # 01-09-1995
        '%m-%d-%Y',           # 09-01-1995
    ]
    
    # Try each format
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # Try using dateutil as fallback
    try:
        from dateutil import parser
        parsed = parser.parse(date_str, fuzzy=True)
        return parsed.strftime('%Y-%m-%d')
    except:
        pass
    
    # Last resort: extract digits
    digits = re.sub(r'\D', '', date_str)
    if len(digits) == 8 and (digits.startswith('19') or digits.startswith('20')):
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    
    return date_str  # Return original if can't parse
