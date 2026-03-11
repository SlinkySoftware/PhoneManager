# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Dial plan utilities for phone number transformation."""
import re
from typing import Tuple, Optional


DIGIT_WILDCARD_REGEX = "[0-9]"


class StandardRegexConverter:
    """Converts user-friendly dial plan syntax to Python regex format.
    
    Supported syntax:
    - X/x = any single digit [0-9]
    - * = any number of digits (must be at end) → .+
    - [0-9] = digit range (passed through as-is)
    - [^0] = negation (passed through as-is)
    - () = capture groups (mapped to $1, $2, $3 in output)
    """

    @staticmethod
    def convert_input_pattern(pattern: str) -> Tuple[str, Optional[str]]:
        """Convert input pattern from standard format to Python regex.
        
        Args:
            pattern: Input pattern in standard format (e.g., "^0([23478]XXXXXXXX)$")
        
        Returns:
            Tuple of (converted_pattern, error_message)
            - If valid: (python_regex_string, None)
            - If invalid: (None, error_message)
        """
        try:
            # Replace X/x with [0-9]
            converted = pattern.replace("X", DIGIT_WILDCARD_REGEX).replace("x", DIGIT_WILDCARD_REGEX)
            
            # Replace * with .+ (any number of digits)
            # * can be at end of pattern or inside capture groups: (XXXX*) → ([0-9]{4}.+)
            if "*" in converted:
                # Check if * is in valid position:
                # 1. At end of pattern: ...* or ...*$
                # 2. Inside capture group: ...)*  or ...)*$
                if not re.search(r"\*\)?\$?$", converted):
                    return None, "Wildcard * must be at the end of pattern or inside a capture group"
                converted = converted.replace("*", ".+")
            
            # Attempt to compile regex to validate
            re.compile(converted)
            return converted, None
        except re.error as e:
            return None, f"Invalid regex: {str(e)}"
        except Exception as e:
            return None, f"Conversion error: {str(e)}"

    @staticmethod
    def convert_output_pattern(pattern: str) -> Tuple[str, Optional[str]]:
        """Convert output pattern from standard format to Python regex replacement.
        
        Standard format uses $1, $2, etc. for capture groups.
        Converts to Python's \1, \2 format for re.sub().
        
        Args:
            pattern: Output pattern (e.g., "+61$1" or "$1-$2")
        
        Returns:
            Tuple of (converted_pattern, error_message)
        """
        try:
            # Replace X/x with [0-9] if used in output
            converted = pattern.replace("X", DIGIT_WILDCARD_REGEX).replace("x", DIGIT_WILDCARD_REGEX)
            
            # Check for invalid double dollar sign
            if "$$" in converted:
                return None, "Invalid double dollar sign $$"
            
            # Convert $1, $2, etc. to \1, \2 for Python's re.sub()
            converted = re.sub(r'\$(\d+)', r'\\\1', converted)
            
            return converted, None
        except Exception as e:
            return None, f"Conversion error: {str(e)}"


def validate_dial_plan_rule(input_pattern: str, output_pattern: str) -> Tuple[bool, Optional[str]]:
    """Validate a dial plan rule for syntax errors.
    
    Args:
        input_pattern: Input pattern in standard format
        output_pattern: Output pattern with $1, $2, etc.
    
    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, None)
        - If invalid: (False, error_message)
    """
    # Validate input pattern
    converted_input, input_error = StandardRegexConverter.convert_input_pattern(input_pattern)
    if input_error:
        return False, f"Input pattern error: {input_error}"
    
    # Validate output pattern
    _, output_error = StandardRegexConverter.convert_output_pattern(output_pattern)
    if output_error:
        return False, f"Output pattern error: {output_error}"
    
    # Test that the patterns can work together
    try:
        # Try a simple substitution to ensure patterns are compatible
        test_string = "1234567890"
        re.match(converted_input, test_string)
        # We don't need a match, just verify the regex compiles
    except Exception as e:
        return False, f"Pattern compatibility error: {str(e)}"
    
    return True, None


def apply_dial_plan(phone_number: str, rules) -> Tuple[str, Optional[int]]:
    """Apply dial plan rules to transform phone number.
    
    Rules are processed in sequence. First matching rule is applied and processing stops.
    
    Args:
        phone_number: Input phone number to transform
        rules: Queryset or list of DialPlanRule objects
    
    Returns:
        Tuple of (transformed_number, matched_rule_index)
        - If match: (transformed_number, rule_sequence_order)
        - If no match: (original_phone_number, None)
    """
    if not rules:
        return phone_number, None
    
    for rule in rules:
        # Convert standard format to Python regex
        converted_input, input_error = StandardRegexConverter.convert_input_pattern(rule.input_regex)
        if input_error:
            # Skip rules with invalid input patterns
            continue
        
        try:
            # Try to match the input pattern
            match = re.match(converted_input, phone_number)
            if match:
                # Pattern matches, apply transformation
                converted_output, output_error = StandardRegexConverter.convert_output_pattern(rule.output_regex)
                if output_error:
                    # Skip this rule if output pattern is invalid
                    continue
                
                # Apply substitution
                try:
                    transformed = re.sub(converted_input, converted_output, phone_number)
                    return transformed, rule.sequence_order
                except Exception:
                    # If substitution fails, skip this rule
                    continue
        except Exception:
            # Skip rules with regex errors
            continue
    
    # No rules matched
    return phone_number, None
