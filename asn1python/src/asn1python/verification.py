"""
ASN.1 Python Runtime Library - Constraint Verification

This module provides constraint validation functions for ASN.1 types.
"""

from nagini_contracts.contracts import *
from typing import Final, Tuple, Union, Optional, List, Any, Callable
NO_OF_BITS_IN_BYTE = 8
# import re
# from .asn1_types import Asn1Error


# class ConstraintError(Asn1Error):
#     """Raised when a constraint validation fails"""
#     pass

# @Pure
# def get_bitmask(start: int, end: int) -> int:
#     Requires(0 <= start and start <= end and end <= 8)
#     return 0xFF >> (8 - end + start) << (8 - end)

@Pure
def int_eq_cutoff(a: int, b: int, cutoff_bit: int) -> bool:
    Requires(0 <= a)
    Requires(0 <= b)
    Requires(0 <= cutoff_bit and cutoff_bit <= NO_OF_BITS_IN_BYTE)
    mask = 1 << cutoff_bit
    return a // mask == b // mask

@Pure
# @Opaque
def byte_read_bit(b: int, position: int) -> bool:
    """Read a single bit. Position starts from MSB"""
    Requires(0 <= b and b <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    # Ensures(Result() == PByteSeq.int_get_bit(b, 7- position))
    return bool((b >> (7 - position)) % 2)
    # return bool(b & (1 << (7 - pos)))

@Pure
@Opaque
def byte_read_bit_lsb(b: int, position: int) -> bool:
    """Read a single bit. Position starts from LSB"""
    Requires(0 <= b and b <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    Ensures(Result() == PByteSeq.int_get_bit(b, position))
    return bool((b >> position) % 2)

@Pure
@Opaque
def byte_set_bit(b: int, bit: bool, pos: int) -> int:
    #@nagini Requires(0 <= b and b <= 0xFF)
    #@nagini Requires(0 <= pos and pos < NO_OF_BITS_IN_BYTE)
    #@nagini Ensures(Result() == PByteSeq.int_set_bit(b, 7 - pos, bit))
    #@nagini Ensures(byte_read_bit(Result(), pos) == bit)
    if bit:
        return b | (1 << (7 - pos))
    else:
        return b & ~(1 << (7 - pos))

#region Byteseq read

@Pure
def byteseq_read_bit(seq: PByteSeq, bit_pos: int, byte_pos: int) -> bool:
    Requires(0 <= bit_pos and bit_pos < NO_OF_BITS_IN_BYTE)
    Requires(0 <= byte_pos and byte_pos < len(seq))
    return byte_read_bit(seq[byte_pos], bit_pos)

@Pure
def byteseq_read_bit_index(seq: PByteSeq, bit_index: int) -> bool:
    Requires(0 <= bit_index and bit_index < len(seq) * NO_OF_BITS_IN_BYTE)
    return byteseq_read_bit(seq, bit_index % NO_OF_BITS_IN_BYTE, bit_index // NO_OF_BITS_IN_BYTE)

@Pure
def byteseq_read_bits(seq: PByteSeq, length: int, bit_index: int) -> int:
    Requires(0 <= bit_index and bit_index + length <= len(seq) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)

    # Stupid but works
    val = 0
    if length >= 1:
        val += byteseq_read_bit_index(seq, bit_index + 0) << (length - 1)
    if length >= 2:
        val += byteseq_read_bit_index(seq, bit_index + 1) << (length - 2)
    if length >= 3:
        val += byteseq_read_bit_index(seq, bit_index + 2) << (length - 3)
    if length >= 4:
        val += byteseq_read_bit_index(seq, bit_index + 3) << (length - 4)
    if length >= 5:
        val += byteseq_read_bit_index(seq, bit_index + 4) << (length - 5)
    if length >= 6:
        val += byteseq_read_bit_index(seq, bit_index + 5) << (length - 6)
    if length >= 7:
        val += byteseq_read_bit_index(seq, bit_index + 6) << (length - 7)
    if length >= 8:
        val += byteseq_read_bit_index(seq, bit_index + 7) << (length - 8)
    return val

#endregion
#region Byteseq set

@Pure
def byteseq_set_bit(seq: PByteSeq, bit: bool, bit_pos: int, byte_pos: int) -> PByteSeq:
    Requires(0 <= bit_pos and bit_pos < NO_OF_BITS_IN_BYTE)
    Requires(0 <= byte_pos and byte_pos < len(seq))
    Ensures(len(seq) == len(Result()))
    Ensures(byteseq_read_bit(Result(), bit_pos, byte_pos) == bit)
    return seq.update(byte_pos, byte_set_bit(seq[byte_pos], bit, bit_pos))

@Pure
def byteseq_set_bit_index(seq: PByteSeq, bit: bool, bit_index: int) -> PByteSeq:
    Requires(0 <= bit_index and bit_index < len(seq) * NO_OF_BITS_IN_BYTE)
    Ensures(len(seq) == len(Result()))
    Ensures(byteseq_read_bit_index(Result(), bit_index) == bit)
    return byteseq_set_bit(seq, bit, bit_index % NO_OF_BITS_IN_BYTE, bit_index // NO_OF_BITS_IN_BYTE)

@Pure
def byteseq_set_bits(seq: PByteSeq, value: int, length: int, bit_index: int) -> PByteSeq:
    Requires(0 <= bit_index and bit_index + length <= len(seq) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= length and length <= 3)
    Requires(0 <= value and value < (1 << length))
    Ensures(len(seq) == len(Result()))
    Ensures(byteseq_eq_until(seq, Result(), bit_index // NO_OF_BITS_IN_BYTE)) # Previous bytes equal
    # Ensures(Let(bit_index % NO_OF_BITS_IN_BYTE, bool, lambda l:
    #         Let(bit_index // NO_OF_BITS_IN_BYTE * NO_OF_BITS_IN_BYTE, bool, lambda pos: 
    #             byteseq_read_bits(seq, l, pos) == byteseq_read_bits(Result(), l, pos)))) # Previous bits in current byte equal
    Ensures(byteseq_read_bits(Result(), length, bit_index) == value) # Written value equal

    new_seq = seq.range(0, len(seq))
    if length >= 1:
        new_seq = byteseq_set_bit_index(new_seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 0), bit_index + 0)
    if length >= 2:
        new_seq = byteseq_set_bit_index(new_seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 1), bit_index + 1)
    if length >= 3:
        new_seq = byteseq_set_bit_index(new_seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 2), bit_index + 2)
    if length >= 4:
        new_seq = byteseq_set_bit_index(new_seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 3), bit_index + 3)
    if length >= 5:
        new_seq = byteseq_set_bit_index(new_seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 4), bit_index + 4)
    if length >= 6:
        new_seq = byteseq_set_bit_index(new_seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 5), bit_index + 5)
    if length >= 7:
        new_seq = byteseq_set_bit_index(new_seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 6), bit_index + 6)
    if length >= 8:
        new_seq = byteseq_set_bit_index(new_seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 7), bit_index + 7)
    return new_seq

# def test_set() -> None:
#     seq = PByteSeq(0)
#     value = 1
#     bit_index = 0
#     length = 1
#     seq = byteseq_set_bit_index(seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 0), bit_index + 0)
#     read = byteseq_read_bits(seq, length, bit_index)

#     assert value == read

#endregion

@Pure
def byteseq_eq_until(b1: PByteSeq, b2: PByteSeq, end: int) -> bool:
    """Compares if the two bytearrays b1 and b2 are equal in the range [start, end["""
    Requires(len(b1) <= len(b2))
    Requires(0 <= end and end <= len(b1))
    return b1.take(end) == b2.take(end)

# def client(b: int, pos: int, val: bool) -> None:
#     Requires(0 <= b and b <= 0xFF)
#     Requires(0 <= pos and pos < NO_OF_BITS_IN_BYTE)
#     prev = b
#     b = byte_set_bit(b, val, pos)
#     assert byte_read_bit(b, pos) == val
    
#     i = 0
#     while i < NO_OF_BITS_IN_BYTE:
#         if i != pos:
#             assert byte_read_bit(b, i) == byte_read_bit(prev, i)
        

# @Pure
# def byteseq_eq_until(b1: PByteSeq, b2: PByteSeq, end_bit: int) -> bool:
#     Requires(len(b1) <= len(b2))
#     Requires(0 <= end_bit and end_bit <= len(b1) * 8)

#     if 0 == end_bit:
#         return True
    
#     end_byte = end_bit // 8
#     end_byte_bit = end_bit % 8
# 
#     return b1.take(end_byte) == b2.take(end_byte) and (end_byte_bit == 0 or byte_range_eq(b1[end_byte], b2[end_byte], 0, end_byte_bit))

# def validate_integer_constraints(value: int,
#                                 min_val: Optional[int] = None,
#                                 max_val: Optional[int] = None) -> bool:
#     """
#     Validate integer constraints.

#     Args:
#         value: Integer value to validate
#         min_val: Minimum allowed value (inclusive)
#         max_val: Maximum allowed value (inclusive)

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     if min_val is not None and value < min_val:
#         raise ConstraintError(f"Integer value {value} below minimum {min_val}")

#     if max_val is not None and value > max_val:
#         raise ConstraintError(f"Integer value {value} above maximum {max_val}")

#     return True


# def validate_real_constraints(value: float,
#                              min_val: Optional[float] = None,
#                              max_val: Optional[float] = None) -> bool:
#     """
#     Validate real number constraints.

#     Args:
#         value: Real value to validate
#         min_val: Minimum allowed value (inclusive)
#         max_val: Maximum allowed value (inclusive)

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     if min_val is not None and value < min_val:
#         raise ConstraintError(f"Real value {value} below minimum {min_val}")

#     if max_val is not None and value > max_val:
#         raise ConstraintError(f"Real value {value} above maximum {max_val}")

#     return True


# def validate_string_constraints(value: str,
#                                min_length: Optional[int] = None,
#                                max_length: Optional[int] = None,
#                                allowed_chars: Optional[str] = None,
#                                pattern: Optional[str] = None) -> bool:
#     """
#     Validate string constraints.

#     Args:
#         value: String value to validate
#         min_length: Minimum string length
#         max_length: Maximum string length
#         allowed_chars: String containing allowed characters
#         pattern: Regular expression pattern to match

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # Length constraints
#     if min_length is not None and len(value) < min_length:
#         raise ConstraintError(f"String length {len(value)} below minimum {min_length}")

#     if max_length is not None and len(value) > max_length:
#         raise ConstraintError(f"String length {len(value)} above maximum {max_length}")

#     # Character constraints
#     if allowed_chars is not None:
#         for char in value:
#             if char not in allowed_chars:
#                 raise ConstraintError(f"Character '{char}' not in allowed set")

#     # Pattern constraint
#     if pattern is not None:
#         if not re.match(pattern, value):
#             raise ConstraintError(f"String '{value}' does not match pattern '{pattern}'")

#     return True


# def validate_bit_string_constraints(value: str,
#                                    min_length: Optional[int] = None,
#                                    max_length: Optional[int] = None,
#                                    fixed_length: Optional[int] = None) -> bool:
#     """
#     Validate bit string constraints.

#     Args:
#         value: Bit string value (containing only '0' and '1')
#         min_length: Minimum bit string length
#         max_length: Maximum bit string length
#         fixed_length: Fixed bit string length

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # Validate bit string format
#     if not all(c in '01' for c in value):
#         raise ConstraintError("Bit string must contain only '0' and '1' characters")

#     # Fixed length constraint
#     if fixed_length is not None:
#         if len(value) != fixed_length:
#             raise ConstraintError(f"Bit string length {len(value)} != required {fixed_length}")
#         return True

#     # Length constraints
#     if min_length is not None and len(value) < min_length:
#         raise ConstraintError(f"Bit string length {len(value)} below minimum {min_length}")

#     if max_length is not None and len(value) > max_length:
#         raise ConstraintError(f"Bit string length {len(value)} above maximum {max_length}")

#     return True


# def validate_octet_string_constraints(value: Union[bytes, bytearray],
#                                      min_length: Optional[int] = None,
#                                      max_length: Optional[int] = None,
#                                      fixed_length: Optional[int] = None) -> bool:
#     """
#     Validate octet string constraints.

#     Args:
#         value: Octet string value
#         min_length: Minimum octet string length
#         max_length: Maximum octet string length
#         fixed_length: Fixed octet string length

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # Fixed length constraint
#     if fixed_length is not None:
#         if len(value) != fixed_length:
#             raise ConstraintError(f"Octet string length {len(value)} != required {fixed_length}")
#         return True

#     # Length constraints
#     if min_length is not None and len(value) < min_length:
#         raise ConstraintError(f"Octet string length {len(value)} below minimum {min_length}")

#     if max_length is not None and len(value) > max_length:
#         raise ConstraintError(f"Octet string length {len(value)} above maximum {max_length}")

#     return True


# def validate_sequence_constraints(value: Union[dict, object],
#                                  required_fields: Optional[List[str]] = None,
#                                  optional_fields: Optional[List[str]] = None) -> bool:
#     """
#     Validate SEQUENCE constraints.

#     Args:
#         value: Sequence value (dict or object with attributes)
#         required_fields: List of required field names
#         optional_fields: List of optional field names

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     if isinstance(value, dict):
#         fields = set(value.keys())
#     else:
#         fields = set(attr for attr in dir(value) if not attr.startswith('_'))

#     # Check required fields
#     if required_fields is not None:
#         for field in required_fields:
#             if field not in fields:
#                 raise ConstraintError(f"Required field '{field}' missing from sequence")

#     # Check that all fields are either required or optional
#     if required_fields is not None and optional_fields is not None:
#         allowed_fields = set(required_fields) | set(optional_fields)
#         for field in fields:
#             if field not in allowed_fields:
#                 raise ConstraintError(f"Unknown field '{field}' in sequence")

#     return True


# def validate_choice_constraints(value: Union[dict, object],
#                                allowed_alternatives: List[str]) -> bool:
#     """
#     Validate CHOICE constraints.

#     Args:
#         value: Choice value (dict or object)
#         allowed_alternatives: List of allowed alternative names

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     if isinstance(value, dict):
#         if len(value) != 1:
#             raise ConstraintError(f"Choice must have exactly one alternative, got {len(value)}")

#         chosen_alternative = next(iter(value.keys()))
#     else:
#         # For objects, look for the first non-None attribute
#         chosen_alternative = None
#         for attr in dir(value):
#             if not attr.startswith('_') and getattr(value, attr) is not None:
#                 if chosen_alternative is not None:
#                     raise ConstraintError("Choice must have exactly one alternative set")
#                 chosen_alternative = attr

#         if chosen_alternative is None:
#             raise ConstraintError("Choice must have one alternative set")

#     if chosen_alternative not in allowed_alternatives:
#         raise ConstraintError(f"Choice alternative '{chosen_alternative}' not in allowed set")

#     return True


# def validate_enumerated_constraints(value: Union[int, str],
#                                    allowed_values: Union[List[int], List[str]]) -> bool:
#     """
#     Validate ENUMERATED constraints.

#     Args:
#         value: Enumerated value
#         allowed_values: List of allowed values

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     if value not in allowed_values:
#         raise ConstraintError(f"Enumerated value '{value}' not in allowed set")

#     return True


# def validate_sequence_of_constraints(value: List[Any],
#                                     min_size: Optional[int] = None,
#                                     max_size: Optional[int] = None,
#                                     element_validator: Optional[Callable[[Any], bool]] = None) -> bool:
#     """
#     Validate SEQUENCE OF constraints.

#     Args:
#         value: Sequence of values
#         min_size: Minimum number of elements
#         max_size: Maximum number of elements
#         element_validator: Function to validate each element

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # Size constraints
#     if min_size is not None and len(value) < min_size:
#         raise ConstraintError(f"Sequence size {len(value)} below minimum {min_size}")

#     if max_size is not None and len(value) > max_size:
#         raise ConstraintError(f"Sequence size {len(value)} above maximum {max_size}")

#     # Element validation
#     if element_validator is not None:
#         for i, element in enumerate(value):
#             try:
#                 element_validator(element)
#             except Exception as e:
#                 raise ConstraintError(f"Element {i} validation failed: {e}")

#     return True


# def validate_set_of_constraints(value: List[Any],
#                                min_size: Optional[int] = None,
#                                max_size: Optional[int] = None,
#                                element_validator: Optional[Callable[[Any], bool]] = None) -> bool:
#     """
#     Validate SET OF constraints.

#     Args:
#         value: Set of values
#         min_size: Minimum number of elements
#         max_size: Maximum number of elements
#         element_validator: Function to validate each element

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # Check for duplicates (SET OF requires unique elements)
#     if len(value) != len(set(str(v) for v in value)):
#         raise ConstraintError("SET OF cannot contain duplicate elements")

#     # Use same validation as SEQUENCE OF
#     return validate_sequence_of_constraints(value, min_size, max_size, element_validator)


# def validate_object_identifier_constraints(value: List[int]) -> bool:
#     """
#     Validate OBJECT IDENTIFIER constraints.

#     Args:
#         value: List of integer arcs

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     if len(value) < 2:
#         raise ConstraintError("OBJECT IDENTIFIER must have at least 2 arcs")

#     # First arc must be 0, 1, or 2
#     if value[0] not in [0, 1, 2]:
#         raise ConstraintError(f"First arc must be 0, 1, or 2, got {value[0]}")

#     # Second arc constraints based on first arc
#     if value[0] in [0, 1] and value[1] >= 40:
#         raise ConstraintError(f"Second arc must be < 40 when first arc is {value[0]}")

#     # All arcs must be non-negative
#     for i, arc in enumerate(value):
#         if arc < 0:
#             raise ConstraintError(f"Arc {i} must be non-negative, got {arc}")

#     return True


# def validate_utf8_string_constraints(value: str,
#                                     min_length: Optional[int] = None,
#                                     max_length: Optional[int] = None) -> bool:
#     """
#     Validate UTF8String constraints.

#     Args:
#         value: UTF8 string value
#         min_length: Minimum string length in characters
#         max_length: Maximum string length in characters

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # Validate UTF-8 encoding
#     try:
#         value.encode('utf-8')
#     except UnicodeEncodeError as e:
#         raise ConstraintError(f"Invalid UTF-8 string: {e}")

#     # Length constraints
#     if min_length is not None and len(value) < min_length:
#         raise ConstraintError(f"UTF8String length {len(value)} below minimum {min_length}")

#     if max_length is not None and len(value) > max_length:
#         raise ConstraintError(f"UTF8String length {len(value)} above maximum {max_length}")

#     return True


# def validate_numeric_string_constraints(value: str,
#                                        min_length: Optional[int] = None,
#                                        max_length: Optional[int] = None) -> bool:
#     """
#     Validate NumericString constraints.

#     Args:
#         value: Numeric string value
#         min_length: Minimum string length
#         max_length: Maximum string length

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # NumericString can only contain digits and space
#     allowed_chars = "0123456789 "

#     return validate_string_constraints(
#         value,
#         min_length=min_length,
#         max_length=max_length,
#         allowed_chars=allowed_chars
#     )


# def validate_printable_string_constraints(value: str,
#                                          min_length: Optional[int] = None,
#                                          max_length: Optional[int] = None) -> bool:
#     """
#     Validate PrintableString constraints.

#     Args:
#         value: Printable string value
#         min_length: Minimum string length
#         max_length: Maximum string length

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # PrintableString allowed characters
#     allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 '()+,-./:=?"

#     return validate_string_constraints(
#         value,
#         min_length=min_length,
#         max_length=max_length,
#         allowed_chars=allowed_chars
#     )


# def validate_ia5_string_constraints(value: str,
#                                    min_length: Optional[int] = None,
#                                    max_length: Optional[int] = None) -> bool:
#     """
#     Validate IA5String constraints.

#     Args:
#         value: IA5 string value
#         min_length: Minimum string length
#         max_length: Maximum string length

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # IA5String can only contain ASCII characters (0-127)
#     for char in value:
#         if ord(char) > 127:
#             raise ConstraintError(f"IA5String contains non-ASCII character '{char}'")

#     return validate_string_constraints(
#         value,
#         min_length=min_length,
#         max_length=max_length
#     )


# def validate_visible_string_constraints(value: str,
#                                        min_length: Optional[int] = None,
#                                        max_length: Optional[int] = None) -> bool:
#     """
#     Validate VisibleString constraints.

#     Args:
#         value: Visible string value
#         min_length: Minimum string length
#         max_length: Maximum string length

#     Returns:
#         True if valid

#     Raises:
#         ConstraintError: If validation fails
#     """
#     # VisibleString can only contain visible ASCII characters (32-126)
#     for char in value:
#         if not (32 <= ord(char) <= 126):
#             raise ConstraintError(f"VisibleString contains non-visible character '{char}'")

#     return validate_string_constraints(
#         value,
#         min_length=min_length,
#         max_length=max_length
#     )