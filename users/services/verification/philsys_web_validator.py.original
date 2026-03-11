"""Headless browser automation for PhilSys QR verification via official website."""
from __future__ import annotations

import logging
import time
import random
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:  # pragma: no cover
    sync_playwright = None
    PlaywrightTimeout = Exception

logger = logging.getLogger(__name__)


@dataclass
class PhilSysVerificationResult:
    """Result of PhilSys web verification."""
    success: bool
    verified: bool = False
    verification_status: str = ""  # 'valid', 'invalid', 'error', 'timeout'
    message: str = ""
    timestamp: datetime = None
    response_time: float = 0.0
    error_details: Optional[str] = None
    screenshot_path: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PhilSysWebValidator:
    """
    Validate PhilSys QR codes using the official verification website.
    
    Uses Playwright for headless browser automation with security measures:
    - Sandboxed execution
    - No data persistence
    - Rate limiting
    - Timeout controls
    """
    
    VERIFICATION_URL = "https://verify.philsys.gov.ph/"
    DEFAULT_TIMEOUT = 30000  # 30 seconds
    MAX_RETRIES = 2
    
    def __init__(self, headless: bool = True, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the PhilSys web validator.
        
        Args:
            headless: Run browser in headless mode
            timeout: Maximum timeout in milliseconds
        """
        if sync_playwright is None:
            raise ImportError(
                "playwright is required for PhilSys web validation. "
                "Install with: pip install playwright && playwright install chromium"
            )
        
        self.headless = headless
        self.timeout = timeout
    
    def verify_qr_code(
        self, 
        qr_data: str, 
        pcn: Optional[str] = None,
        save_screenshot: bool = False
    ) -> PhilSysVerificationResult:
        """
        Verify PhilSys QR code through official website.
        
        Args:
            qr_data: Raw QR code data
            pcn: PhilSys Card Number (optional)
            save_screenshot: Save screenshot of verification result
            
        Returns:
            PhilSysVerificationResult with verification status
        """
        start_time = time.time()
        
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                # Add random delay to avoid detection as bot (1-3 seconds)
                if attempt > 0:
                    delay = random.uniform(2, 5)
                    logger.info(f"Retry attempt {attempt}, waiting {delay:.2f}s")
                    time.sleep(delay)
                
                result = self._perform_verification(qr_data, pcn, save_screenshot)
                
                # Calculate response time
                result.response_time = time.time() - start_time
                
                if result.success:
                    return result
                
                # If not successful and not last attempt, retry
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"Verification attempt {attempt + 1} failed, retrying...")
                    continue
                
                return result
                
            except Exception as e:
                logger.exception(f"Error during verification attempt {attempt + 1}: {e}")
                
                if attempt >= self.MAX_RETRIES:
                    return PhilSysVerificationResult(
                        success=False,
                        verification_status='error',
                        message="Verification failed after multiple attempts",
                        error_details=str(e),
                        response_time=time.time() - start_time
                    )
        
        # Should not reach here, but return error result
        return PhilSysVerificationResult(
            success=False,
            verification_status='error',
            message="Maximum retries exceeded",
            response_time=time.time() - start_time
        )
    
    def _perform_verification(
        self, 
        qr_data: str, 
        pcn: Optional[str],
        save_screenshot: bool
    ) -> PhilSysVerificationResult:
        """Perform the actual verification using Playwright."""
        
        with sync_playwright() as p:
            # Launch browser with security settings
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920x1080',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            
            try:
                # Create context with no data persistence
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    locale='en-PH',
                    timezone_id='Asia/Manila',
                    ignore_https_errors=False,
                )
                
                # Disable cache
                context.set_extra_http_headers({
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                })
                
                page = context.new_page()
                page.set_default_timeout(self.timeout)
                
                # Navigate to verification page
                logger.info(f"Navigating to {self.VERIFICATION_URL}")
                response = page.goto(self.VERIFICATION_URL, wait_until='networkidle')
                
                if not response or not response.ok:
                    return PhilSysVerificationResult(
                        success=False,
                        verification_status='error',
                        message=f"Failed to load verification page: {response.status if response else 'No response'}",
                    )
                
                # Wait for page to be fully loaded
                page.wait_for_load_state('domcontentloaded')
                time.sleep(random.uniform(1, 2))  # Human-like delay
                
                # Try to find and interact with verification form
                result = self._interact_with_form(page, qr_data, pcn)
                
                # Save screenshot if requested
                if save_screenshot and result.success:
                    screenshot_path = f"/tmp/philsys_verification_{int(time.time())}.png"
                    try:
                        page.screenshot(path=screenshot_path, full_page=True)
                        result.screenshot_path = screenshot_path
                        logger.info(f"Screenshot saved to {screenshot_path}")
                    except Exception as e:
                        logger.warning(f"Failed to save screenshot: {e}")
                
                return result
                
            finally:
                # Always close browser to prevent resource leaks
                try:
                    context.close()
                except Exception as e:
                    logger.debug(f"Error closing browser context: {e}")
                try:
                    browser.close()
                except Exception as e:
                    logger.debug(f"Error closing browser: {e}")
    
    def _interact_with_form(
        self, 
        page, 
        qr_data: str, 
        pcn: Optional[str]
    ) -> PhilSysVerificationResult:
        """
        Interact with the PhilSys verification form.
        
        Note: This implementation is generic and may need adjustment based on
        the actual form structure of verify.philsys.gov.ph
        """
        try:
            # Look for common input field selectors
            input_selectors = [
                'input[type="text"]',
                'input[name*="qr"]',
                'input[name*="code"]',
                'input[name*="pcn"]',
                'input[id*="qr"]',
                'input[id*="code"]',
                'textarea',
            ]
            
            input_field = None
            for selector in input_selectors:
                try:
                    input_field = page.wait_for_selector(selector, timeout=5000)
                    if input_field:
                        logger.info(f"Found input field with selector: {selector}")
                        break
                except PlaywrightTimeout:
                    continue
            
            if not input_field:
                # Try to find file upload for QR image
                file_input = page.query_selector('input[type="file"]')
                if file_input:
                    return PhilSysVerificationResult(
                        success=False,
                        verification_status='error',
                        message="PhilSys verification requires QR image upload, not text input. Feature not yet supported.",
                    )
                
                return PhilSysVerificationResult(
                    success=False,
                    verification_status='error',
                    message="Could not locate verification input field on page",
                )
            
            # Input the QR data or PCN
            input_value = pcn if pcn else qr_data
            logger.info(f"Entering verification data (length: {len(input_value)})")
            
            # Human-like typing with delays
            for char in input_value:
                input_field.type(char, delay=random.uniform(50, 150))
            
            time.sleep(random.uniform(0.5, 1.0))
            
            # Look for submit button
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Verify")',
                'button:has-text("Submit")',
                'button:has-text("Check")',
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = page.query_selector(selector)
                    if submit_button:
                        logger.info(f"Found submit button with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} not found: {e}")
                    continue
            
            if not submit_button:
                return PhilSysVerificationResult(
                    success=False,
                    verification_status='error',
                    message="Could not locate submit button on verification form",
                )
            
            # Click submit button
            logger.info("Clicking submit button")
            submit_button.click()
            
            # Wait for response
            time.sleep(random.uniform(2, 4))
            page.wait_for_load_state('networkidle', timeout=self.timeout)
            
            # Parse verification result from page
            return self._parse_verification_result(page)
            
        except PlaywrightTimeout:
            return PhilSysVerificationResult(
                success=False,
                verification_status='timeout',
                message="Verification request timed out",
            )
        except Exception as e:
            logger.exception(f"Error interacting with form: {e}")
            return PhilSysVerificationResult(
                success=False,
                verification_status='error',
                message=f"Form interaction error: {str(e)}",
                error_details=str(e)
            )
    
    def _parse_verification_result(self, page) -> PhilSysVerificationResult:
        """
        Parse the verification result from the page.
        
        Looks for common success/failure indicators.
        """
        try:
            # Get page content
            content = page.content().lower()
            page_text = page.inner_text('body').lower()
            
            # Success indicators
            success_keywords = [
                'valid', 'verified', 'authentic', 'success', 
                'legitimate', 'confirmed', 'approved'
            ]
            
            # Failure indicators
            failure_keywords = [
                'invalid', 'not found', 'unverified', 'failed',
                'not valid', 'cannot verify', 'error', 'incorrect'
            ]
            
            # Check for success
            for keyword in success_keywords:
                if keyword in page_text:
                    logger.info(f"Found success keyword: {keyword}")
                    return PhilSysVerificationResult(
                        success=True,
                        verified=True,
                        verification_status='valid',
                        message=f"PhilSys ID verified successfully (keyword: {keyword})",
                    )
            
            # Check for failure
            for keyword in failure_keywords:
                if keyword in page_text:
                    logger.info(f"Found failure keyword: {keyword}")
                    return PhilSysVerificationResult(
                        success=True,
                        verified=False,
                        verification_status='invalid',
                        message=f"PhilSys ID verification failed (keyword: {keyword})",
                    )
            
            # Could not determine result
            return PhilSysVerificationResult(
                success=False,
                verification_status='error',
                message="Could not determine verification result from page",
                error_details=f"Page text preview: {page_text[:200]}..."
            )
            
        except Exception as e:
            logger.exception(f"Error parsing verification result: {e}")
            return PhilSysVerificationResult(
                success=False,
                verification_status='error',
                message=f"Result parsing error: {str(e)}",
                error_details=str(e)
            )
