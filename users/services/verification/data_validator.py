"""Data validation module to compare extracted ID data with user profile."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    confidence_score: float  # 0.0 to 1.0
    mismatches: List[str]
    warnings: List[str]
    matched_fields: List[str]


class DataValidator:
    """Validates extracted ID data against user profile information."""
    
    # Minimum similarity threshold for name matching (0.0 to 1.0)
    NAME_SIMILARITY_THRESHOLD = 0.75
    
    # Minimum confidence score to pass validation
    MIN_CONFIDENCE_SCORE = 0.60
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, requires higher confidence and all fields to match
        """
        self.strict_mode = strict_mode
        if strict_mode:
            self.NAME_SIMILARITY_THRESHOLD = 0.85
            self.MIN_CONFIDENCE_SCORE = 0.75
    
    def validate(self, user, extracted_data: Dict[str, str]) -> ValidationResult:
        """
        Validate extracted ID data against user profile.
        
        LENIENT MODE: Only auto-rejects on name and date of birth mismatches.
        Address is treated as optional and only generates warnings.
        
        Args:
            user: CustomUser instance
            extracted_data: Dictionary of extracted data from ID
            
        Returns:
            ValidationResult with validation details
        """
        mismatches = []
        warnings = []
        matched_fields = []
        field_scores = []
        
        # CRITICAL VALIDATION: Name matching
        # Check if at least one name field matches
        name_matched = False
        
        # Validate First Name
        if 'first_name' in extracted_data:
            score = self._compare_names(
                user.first_name,
                extracted_data['first_name']
            )
            field_scores.append(score)
            
            if score >= self.NAME_SIMILARITY_THRESHOLD:
                matched_fields.append('first_name')
                name_matched = True
            else:
                mismatches.append(
                    f"First name mismatch: Profile '{user.first_name}' vs ID '{extracted_data['first_name']}' (similarity: {score:.2f})"
                )
        else:
            warnings.append("First name not extracted from ID")
        
        # Validate Last Name
        if 'last_name' in extracted_data:
            score = self._compare_names(
                user.last_name,
                extracted_data['last_name']
            )
            field_scores.append(score)
            
            if score >= self.NAME_SIMILARITY_THRESHOLD:
                matched_fields.append('last_name')
                name_matched = True
            else:
                mismatches.append(
                    f"Last name mismatch: Profile '{user.last_name}' vs ID '{extracted_data['last_name']}' (similarity: {score:.2f})"
                )
        else:
            warnings.append("Last name not extracted from ID")
        
        # Validate Full Name (if available) - can override individual name mismatches
        if 'full_name' in extracted_data:
            user_full_name = user.get_full_name()
            score = self._compare_names(
                user_full_name,
                extracted_data['full_name']
            )
            field_scores.append(score)
            
            if score >= self.NAME_SIMILARITY_THRESHOLD:
                matched_fields.append('full_name')
                name_matched = True
                # If full name matches, clear individual name mismatches
                mismatches = [m for m in mismatches if 'name mismatch' not in m.lower()]
            else:
                # Only add mismatch if no individual names matched
                if not name_matched:
                    mismatches.append(
                        f"Full name mismatch: Profile '{user_full_name}' vs ID '{extracted_data['full_name']}' (similarity: {score:.2f})"
                    )
        
        # CRITICAL VALIDATION: Date of Birth
        dob_matched = False
        if 'date_of_birth' in extracted_data and user.date_of_birth:
            if self._compare_dates(user.date_of_birth, extracted_data['date_of_birth']):
                matched_fields.append('date_of_birth')
                field_scores.append(1.0)
                dob_matched = True
            else:
                mismatches.append(
                    f"Date of birth mismatch: Profile '{user.date_of_birth}' vs ID '{extracted_data['date_of_birth']}'"
                )
                field_scores.append(0.0)
        elif 'date_of_birth' in extracted_data:
            warnings.append("Date of birth not set in profile - cannot verify")
        
        # OPTIONAL: Address (only warning, not auto-reject)
        if 'address' in extracted_data and user.address:
            score = self._compare_addresses(user.address, extracted_data['address'])
            # Don't include address in field_scores for auto-reject decision
            
            if score >= 0.60:
                matched_fields.append('address')
                warnings.append(f"Address matched (similarity: {score:.2f})")
            else:
                warnings.append(
                    f"Address similarity low: Profile '{user.address}' vs ID '{extracted_data['address']}' (similarity: {score:.2f})"
                )
        elif 'address' in extracted_data:
            warnings.append("Address not set in profile")
        
        # Calculate overall confidence score (only from critical fields)
        if field_scores:
            confidence_score = sum(field_scores) / len(field_scores)
        else:
            confidence_score = 0.0
            warnings.append("No critical fields could be validated - insufficient extracted data")
        
        # LENIENT VALIDATION LOGIC:
        # Only auto-reject if BOTH name AND date of birth have mismatches
        # If either matches, allow manual review
        critical_mismatches = [m for m in mismatches if 'name mismatch' in m.lower() or 'date of birth mismatch' in m.lower()]
        
        is_valid = True
        if not name_matched and critical_mismatches:
            # Name doesn't match at all
            is_valid = False
        elif 'date_of_birth' in extracted_data and user.date_of_birth and not dob_matched:
            # DOB extracted and doesn't match
            is_valid = False
        
        # In strict mode, require both name AND DOB to match
        if self.strict_mode:
            if not name_matched or not dob_matched:
                is_valid = False
                warnings.append("Strict mode: Both name and date of birth must match")
        
        logger.info(
            "Data validation for user %s: valid=%s, confidence=%.2f, matched=%d, critical_mismatches=%d",
            user.pk, is_valid, confidence_score, len(matched_fields), len(critical_mismatches)
        )
        
        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            mismatches=mismatches,
            warnings=warnings,
            matched_fields=matched_fields
        )
    
    def _compare_names(self, name1: str, name2: str) -> float:
        """
        Compare two names using fuzzy matching.
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not name1 or not name2:
            return 0.0
        
        # Normalize names
        name1 = self._normalize_name(name1)
        name2 = self._normalize_name(name2)
        
        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, name1, name2).ratio()
        
        return similarity
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison."""
        # Convert to lowercase, remove extra spaces, remove common suffixes
        name = name.lower().strip()
        name = ' '.join(name.split())  # Remove extra whitespace
        
        # Remove common suffixes
        suffixes = [' jr', ' jr.', ' sr', ' sr.', ' ii', ' iii', ' iv']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
        
        return name
    
    def _compare_dates(self, date1, date2: str) -> bool:
        """
        Compare dates.
        
        Args:
            date1: datetime.date object or string
            date2: string in various formats
            
        Returns:
            True if dates match
        """
        try:
            # Convert date1 to string if it's a date object
            if hasattr(date1, 'strftime'):
                date1_str = date1.strftime('%Y-%m-%d')
            else:
                date1_str = str(date1)
            
            # Try to parse date2 in various formats
            date2_normalized = self._normalize_date(date2)
            
            return date1_str == date2_normalized
        except Exception as e:
            logger.warning("Date comparison failed: %s", e)
            return False
    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize date string to YYYY-MM-DD format.
        
        Handles formats like:
        - MM/DD/YYYY
        - DD/MM/YYYY
        - YYYY-MM-DD
        - Month DD, YYYY
        """
        date_str = date_str.strip()
        
        # Try different date formats
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If no format matches, return original
        return date_str
    
    def _compare_addresses(self, addr1: str, addr2: str) -> float:
        """
        Compare two addresses using fuzzy matching.
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not addr1 or not addr2:
            return 0.0
        
        # Normalize addresses
        addr1 = self._normalize_address(addr1)
        addr2 = self._normalize_address(addr2)
        
        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, addr1, addr2).ratio()
        
        return similarity
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address for comparison."""
        # Convert to lowercase, remove extra spaces
        address = address.lower().strip()
        address = ' '.join(address.split())
        
        # Remove common abbreviations variations
        replacements = {
            ' street': ' st',
            ' avenue': ' ave',
            ' road': ' rd',
            ' boulevard': ' blvd',
            ' drive': ' dr',
            ' barangay': ' brgy',
        }
        
        for old, new in replacements.items():
            address = address.replace(old, new)
        
        return address
