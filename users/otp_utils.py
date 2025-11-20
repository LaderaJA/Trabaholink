"""
Utility functions for OTP generation, validation, and email sending.
Uses hashing for secure OTP storage.
"""
import random
import string
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password, check_password
from .models import EmailOTP


def generate_otp():
    """Generate a 6-digit OTP code"""
    return ''.join(random.choices(string.digits, k=settings.OTP_LENGTH))


def hash_otp(otp_code):
    """Hash OTP code for secure storage"""
    return make_password(otp_code)


def verify_otp_hash(otp_code, hashed_otp):
    """Verify OTP code against hashed value"""
    return check_password(otp_code, hashed_otp)


def send_otp_email(email, otp_code, username):
    """
    Send OTP verification email to the user.
    This is the ONLY email sent during registration.
    """
    subject = 'TrabahoLink - Email Verification Code'
    
    # Create HTML email content
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .header {{
                background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: white;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .otp-code {{
                font-size: 32px;
                font-weight: bold;
                color: #2563eb;
                text-align: center;
                padding: 20px;
                background: #eff6ff;
                border-radius: 8px;
                letter-spacing: 8px;
                margin: 20px 0;
            }}
            .warning {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .footer {{
                text-align: center;
                color: #666;
                font-size: 12px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Email Verification</h1>
                <p>TrabahoLink Account Registration</p>
            </div>
            <div class="content">
                <h2>Hello {username}!</h2>
                <p>Thank you for registering with TrabahoLink. To complete your registration, please verify your email address using the code below:</p>
                
                <div class="otp-code">
                    {otp_code}
                </div>
                
                <p style="text-align: center; color: #666;">
                    <strong>This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.</strong>
                </p>
                
                <div class="warning">
                    <strong>⚠️ Security Notice:</strong>
                    <ul style="margin: 10px 0;">
                        <li>Never share this code with anyone</li>
                        <li>TrabahoLink staff will never ask for your verification code</li>
                        <li>If you didn't request this code, please ignore this email</li>
                    </ul>
                </div>
                
                <p>If you have any questions, feel free to contact our support team.</p>
                
                <p>Best regards,<br>
                <strong>The TrabahoLink Team</strong></p>
            </div>
            <div class="footer">
                <p>This is an automated email. Please do not reply to this message.</p>
                <p>&copy; 2025 TrabahoLink. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    plain_message = f"""
    Hello {username}!
    
    Thank you for registering with TrabahoLink. To complete your registration, please verify your email address using the code below:
    
    Verification Code: {otp_code}
    
    This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.
    
    Security Notice:
    - Never share this code with anyone
    - TrabahoLink staff will never ask for your verification code
    - If you didn't request this code, please ignore this email
    
    Best regards,
    The TrabahoLink Team
    """
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Log error but don't expose details to user
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False


def create_otp_record(email, username, password_hash, role='client'):
    """
    Create or update OTP record for email verification.
    Stores hashed OTP for security.
    """
    # Normalize email to lowercase
    email = email.lower().strip()
    
    # Invalidate any existing unverified OTPs for this email (case-insensitive)
    EmailOTP.objects.filter(email__iexact=email, is_verified=False).delete()
    
    # Generate new OTP (plain text for email)
    otp_code = generate_otp()
    
    # Hash the OTP before storing
    hashed_otp = hash_otp(otp_code)
    
    # Create new OTP record with hashed OTP
    otp_record = EmailOTP.objects.create(
        email=email,
        otp_code=hashed_otp,  # Store hashed version
        username=username,
        password_hash=password_hash,
        role=role,
        is_verified=False,
        attempts=0
    )
    
    # Return the plain OTP for sending via email
    # The record stores the hashed version
    otp_record._plain_otp = otp_code  # Temporary attribute for email sending
    return otp_record


def verify_otp(email, otp_code):
    """
    Verify OTP code for the given email using secure hash comparison.
    Returns (success: bool, message: str, otp_record: EmailOTP or None)
    """
    try:
        # Normalize email to lowercase for case-insensitive matching
        email = email.lower().strip()
        otp_code = otp_code.strip()
        
        # Get the latest unverified OTP for this email (case-insensitive)
        otp_record = EmailOTP.objects.filter(
            email__iexact=email,
            is_verified=False
        ).order_by('-created_at').first()
        
        if not otp_record:
            # Check if there are verified records
            verified_count = EmailOTP.objects.filter(email__iexact=email, is_verified=True).count()
            if verified_count > 0:
                return False, "This email has already been verified. Please login instead.", None
            return False, "No verification code found. Please register again.", None
        
        # Check if OTP has expired
        if otp_record.is_expired():
            return False, "Verification code has expired. Please register again.", None
        
        # Check if too many attempts
        if otp_record.attempts >= 5:
            return False, "Too many failed attempts. Please register again.", None
        
        # Verify OTP code using secure hash comparison
        if verify_otp_hash(otp_code, otp_record.otp_code):
            otp_record.is_verified = True
            otp_record.save()
            return True, "Email verified successfully!", otp_record
        else:
            otp_record.increment_attempts()
            remaining_attempts = 5 - otp_record.attempts
            return False, f"Invalid verification code. {remaining_attempts} attempts remaining.", None
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error verifying OTP for {email}: {str(e)}")
        return False, "An error occurred during verification. Please try again.", None


def resend_otp(email):
    """
    Resend OTP code to the email with new hashed OTP.
    Returns (success: bool, message: str)
    """
    from django.utils import timezone
    
    try:
        # Normalize email
        email = email.lower().strip()
        
        # Get the latest unverified OTP for this email (case-insensitive)
        otp_record = EmailOTP.objects.filter(
            email__iexact=email,
            is_verified=False
        ).order_by('-created_at').first()
        
        if not otp_record:
            return False, "No pending verification found. Please register again."
        
        # Generate new OTP (plain text for email)
        new_otp = generate_otp()
        
        # Hash and store the new OTP
        otp_record.otp_code = hash_otp(new_otp)
        otp_record.attempts = 0  # Reset attempts
        otp_record.created_at = timezone.now()  # Reset expiry time
        otp_record.save()
        
        # Send new OTP email (plain text)
        if send_otp_email(email, new_otp, otp_record.username):
            return True, "A new verification code has been sent to your email."
        else:
            return False, "Failed to send verification code. Please try again."
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error resending OTP for {email}: {str(e)}")
        return False, "An error occurred. Please try again."
