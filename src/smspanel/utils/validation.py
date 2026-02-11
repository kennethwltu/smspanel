"""Validation utilities for SMS composition."""

import re
from typing import Tuple

from smspanel.constants.messages import (
    SMS_ENQUIRY_REQUIRED,
    SMS_ENQUIRY_INVALID,
    SMS_CONTENT_REQUIRED,
    SMS_PHONE_INVALID,
)

PHONE_REGEX = re.compile(r"^\+852\d{8}$")
ENQUIRY_REGEX = re.compile(r"^\d{4}\s?\d{4}$")


def validate_enquiry_number(enquiry_number: str) -> Tuple[bool, str]:
    """Validate enquiry number format.

    Args:
        enquiry_number: The enquiry number to validate.

    Returns:
        Tuple of (is_valid, error_message).
        is_valid: True if valid, False otherwise.
        error_message: Error description if invalid, empty string if valid.
    """
    if not enquiry_number:
        return False, SMS_ENQUIRY_REQUIRED
    if not ENQUIRY_REGEX.match(enquiry_number):
        return False, SMS_ENQUIRY_INVALID
    return True, ""


def validate_message_content(content: str) -> Tuple[bool, str]:
    """Validate message content.

    Args:
        content: The message content to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not content:
        return False, SMS_CONTENT_REQUIRED
    return True, ""


def validate_recipients(recipients_input: str) -> Tuple[list[str], list[str]]:
    """Validate and parse recipients.

    Args:
        recipients_input: Raw recipients input (one per line).

    Returns:
        Tuple of (valid_recipients, invalid_numbers).
        valid_recipients: List of 8-digit phone numbers (without +852 prefix).
        invalid_numbers: List of invalid phone numbers.
    """
    recipients = [r.strip() for r in recipients_input.split("\n") if r.strip()]

    valid_recipients = []
    invalid_numbers = []
    for r in recipients:
        if PHONE_REGEX.match(r):
            # Extract the 8-digit part after +852 prefix
            digit_part = r[4:]  # Remove "+852"
            valid_recipients.append(digit_part)
        else:
            invalid_numbers.append(r)

    return valid_recipients, invalid_numbers


def validate_recipient_list(recipients: list[str]) -> Tuple[list[str], list[str]]:
    """Validate a list of phone numbers.

    Args:
        recipients: List of phone numbers to validate.

    Returns:
        Tuple of (valid_recipients, invalid_numbers).
        valid_recipients: List of 8-digit phone numbers (without +852 prefix).
        invalid_numbers: List of invalid phone numbers.
    """
    valid_recipients = []
    invalid_numbers = []
    for r in recipients:
        if isinstance(r, str):
            r_clean = r.strip()
            if PHONE_REGEX.match(r_clean):
                # Extract the 8-digit part after +852 prefix
                digit_part = r_clean[4:]  # Remove "+852"
                valid_recipients.append(digit_part)
            else:
                invalid_numbers.append(r_clean)
        else:
            invalid_numbers.append(str(r))

    return valid_recipients, invalid_numbers


def format_phone_error(invalid_numbers: list[str]) -> str:
    """Format phone number validation error message.

    Args:
        invalid_numbers: List of invalid phone numbers.

    Returns:
        Formatted error message.
    """
    return SMS_PHONE_INVALID.format(invalid_numbers=", ".join(invalid_numbers))
