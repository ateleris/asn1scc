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

# @Pure
# def int_eq_cutoff(a: int, b: int, cutoff_bit: int) -> bool:
#     Requires(0 <= a)
#     Requires(0 <= b)
#     Requires(0 <= cutoff_bit and cutoff_bit <= NO_OF_BITS_IN_BYTE)
#     mask = 1 << cutoff_bit
#     return a // mask == b // mask

# @Pure
# def byte_bounds(byte: int, length: int) -> bool:
#     Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
#     return 0 <= byte and byte < (1 << length)

#region Helpers

@Pure
def byteseq_eq_until(b1: PByteSeq, b2: PByteSeq, end: int) -> bool:
    """Compares if the two bytearrays b1 and b2 are equal in the range [start, end["""
    Requires(len(b1) <= len(b2))
    Requires(0 <= end and end <= len(b1))
    return b1.take(end) == b2.take(end)

#endregion
#region Read bits

@Pure
@Opaque
def byte_read_bit(byte: PInt, position: PInt) -> bool:
    """Read a single bit. Position starts from MSB"""
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    Decreases(None)
    return bool((byte >> (7 - position)) % 2)

@Pure
@Opaque
def byte_read_bits(byte: PInt, position: PInt, length: PInt) -> int:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(0 <= Result() and Result() < (1 << length))
    return (byte >> (NO_OF_BITS_IN_BYTE - position - length)) % (1 << length)

@Pure
@Opaque
def _lemma_byte_read_bit_equal(byte: int, position: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    Ensures(int(byte_read_bit(byte, position)) == byte_read_bits(byte, position, 1))
    Ensures(Result())
    
    single = Reveal(byte_read_bit(byte, position))
    multiple = Reveal(byte_read_bits(byte, position, 1))
    return int(single) == multiple

@Pure
@Opaque
def byte_read_bits_rec(byte: PInt, position: PInt, length: PInt) -> int:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
    Decreases(length)
    Ensures(0 <= Result() and Result() < (1 << length))
    
    if length <= 1:
        return byte_read_bits(byte, position, length)  
    
    rec = byte_read_bits_rec(byte, position, length - 1) << 1
    res = rec + byte_read_bits(byte, position + length - 1, 1)
    return res

@Pure
@Opaque
def _lemma_byte_read_bits_induction(byte: int, position: int, length: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= position and position <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= length and length + position <= NO_OF_BITS_IN_BYTE)
    Decreases(length)
    Ensures(Implies(length == 0, byte_read_bits(byte, position, length) == 0))
    Ensures(Implies(length >= 1, byte_read_bits(byte, position, length) == 
                    (byte_read_bits(byte, position, length - 1) << 1)
                    + byte_read_bits(byte, position + length - 1, 1)))
    Ensures(Result())

    if length == 0:
        return True

    full = Reveal(byte_read_bits(byte, position, length))
    prefix = Reveal(byte_read_bits(byte, position, length - 1)) << 1
    single = Reveal(byte_read_bits(byte, position + length - 1, 1))

    inner = _lemma_byte_read_bits_induction(byte, position, length - 1)
    return inner and full == prefix + single

# Probably not necessary
#
# @Pure
# @Opaque
# def _lemma_byte_read_bits_equal(byte: int, position: int, length: int) -> bool:
#     Requires(0 <= byte and byte <= 0xFF)
#     Requires(0 <= position and position <= NO_OF_BITS_IN_BYTE)
#     Requires(0 <= length and length + position <= NO_OF_BITS_IN_BYTE)
#     Decreases(length)
#     Ensures(byte_read_bits(byte, position, length) == byte_read_bits_rec(byte, position, length))
#     Ensures(Result())
    
#     direct = Reveal(byte_read_bits(byte, position, length))
#     rec = Reveal(byte_read_bits_rec(byte, position, length))
        
#     if length == 0:
#         return direct == rec
    
#     equal_lemma = _lemma_byte_read_bits_equal(byte, position, length - 1)
#     induction_lemma = _lemma_byte_read_bits_induction(byte, position, length)

#     return direct == rec and equal_lemma and induction_lemma

#endregion
#region Read Byteseq

@Pure
@Opaque
def byteseq_read_bit(byteseq: PByteSeq, position: PInt) -> bool:
    Requires(0 <= position and position < len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    byte_position = position // NO_OF_BITS_IN_BYTE
    bit_position = position % NO_OF_BITS_IN_BYTE
    return byte_read_bit(byteseq[byte_position], bit_position)

# Reads upper and lower parts separately
#
# position = 3
# length = 8
#
# bits on stream  x  x  b0 b1 b2 b3 b4 b5 b6 b7 x  x  x
# currentBit      0  1  2  3  4  5  6  7  0  1  2  3  4 ...
#                 |                       |
#            start of first_byte    start second_byte
#
@Pure
@Opaque
def byteseq_read_bits(byteseq: PByteSeq, position: PInt, length: PInt) -> int:
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(0 <= Result() and Result() < (1 << length))
    
    if length == 0:
        return 0
    
    byte_position = position // NO_OF_BITS_IN_BYTE
    bit_position = position % NO_OF_BITS_IN_BYTE
    
    if bit_position + length <= NO_OF_BITS_IN_BYTE:
        return byte_read_bits(byteseq[byte_position], bit_position, length)
    
    first_length = NO_OF_BITS_IN_BYTE - bit_position
    second_length = length - first_length
    
    upper = byte_read_bits(byteseq[byte_position], bit_position, first_length) << second_length
    lower = byte_read_bits(byteseq[byte_position + 1], 0, second_length)
    return upper + lower

@Pure
@Opaque
def lemma_byteseq_read_bits_induction(byteseq: PByteSeq, position: int, length: int) -> bool:
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(Implies(length == 0, byteseq_read_bits(byteseq, position, length) == 0))
    Ensures(Implies(length >= 1, byteseq_read_bits(byteseq, position, length) == 
                                (byteseq_read_bits(byteseq, position, length - 1) << 1) + 
                                (byteseq_read_bits(byteseq, position + length - 1, 1))))
    Ensures(Result())

    if length == 0:
        return True
    
    byte_position = position // NO_OF_BITS_IN_BYTE
    bit_position = position % NO_OF_BITS_IN_BYTE

    full = Reveal(byteseq_read_bits(byteseq, position, length))
    prefix = Reveal(byteseq_read_bits(byteseq, position, length - 1)) << 1
    single = Reveal(byteseq_read_bits(byteseq, position + length - 1, 1))

    if bit_position + length <= NO_OF_BITS_IN_BYTE:
        lemma = _lemma_byte_read_bits_induction(byteseq[byte_position], bit_position, length)
        return full == single + prefix and lemma
    
    first_length = NO_OF_BITS_IN_BYTE - bit_position
    second_length = length - first_length

    prefix_upper = byte_read_bits(byteseq[byte_position], bit_position, first_length) << second_length
    full_lower = byte_read_bits(byteseq[byte_position + 1], 0, second_length)
    prefix_lower = byte_read_bits(byteseq[byte_position + 1], 0, second_length - 1) << 1
    single_lower = byte_read_bits(byteseq[byte_position + 1], second_length - 1, 1)
    lemma_lower = _lemma_byte_read_bits_induction(byteseq[byte_position + 1], 0, second_length)

    lower = prefix_lower + single_lower
    sum = prefix_upper + prefix_lower + single

    return full_lower == lower and single == single_lower and full == sum and lemma_lower

@Pure
@Opaque
def _lemma_byteseq_read_bit_equal(byteseq: PByteSeq, position: int) -> bool:
    Requires(0 <= position and position < len(byteseq) * NO_OF_BITS_IN_BYTE)
    Ensures(int(byteseq_read_bit(byteseq, position)) == byteseq_read_bits(byteseq, position, 1))
    Ensures(Result())
    
    byte_position = position // NO_OF_BITS_IN_BYTE
    bit_position = position % NO_OF_BITS_IN_BYTE
    first_case = bit_position + 1 <= NO_OF_BITS_IN_BYTE
    inner = _lemma_byte_read_bit_equal(byteseq[byte_position], bit_position)
    
    single = Reveal(byteseq_read_bit(byteseq, position))
    multiple = Reveal(byteseq_read_bits(byteseq, position, 1))
    return first_case and inner and int(single) == multiple

#region Set bits

# @Pure
# @Opaque
# def byte_set_bit(byte: int, bit: bool, position: int) -> int:
#     Requires(0 <= byte and byte <= 0xFF)
#     Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
#     Decreases(None)
#     Ensures(0 <= Result() and Result() <= 0xFF)

#     if bit:
#         return byte | (1 << (7 - position))
#     else:
#         return byte & ~(1 << (7 - position))

#
# Splits the byte into three parts
#
# position = 2
# length = 3
#
# |x|x|b|b|b|?|?|?|
#  0 1 2 3 4 5 6 7
#
# @Pure
# @Opaque
# def byte_set_bits(byte: int, value: int, position: int, length: int) -> int:
#     Requires(0 <= byte and byte <= 0xFF)
#     Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
#     Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
#     Requires(0 <= value and value < (1 << length))
#     Ensures(0 <= Result() and Result() <= 0xFF)
    
#     upper = byte_read_bits(byte, 0, position) << (NO_OF_BITS_IN_BYTE - position)
#     middle = value << (NO_OF_BITS_IN_BYTE - position - length)
#     lower = byte % (1 << (NO_OF_BITS_IN_BYTE - position - length))
#     return upper + middle + lower

# @Pure
# @Opaque
# def _lemma_byte_set_bits(byte: int, value: int, position: int, length: int) -> bool:
#     Requires(0 <= byte and byte <= 0xFF)
#     Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
#     Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
#     Requires(0 <= value and value < (1 << length))
#     Ensures(byte_read_bits(byte_set_bits(byte, value, position, length), position, length) == value) # Written value
#     Ensures(byte_read_bits(byte_set_bits(byte, value, position, length), 0, position) == byte_read_bits(byte, 0, position)) # Previous bits
#     Ensures(byte_read_bits(byte_set_bits(byte, value, position, length), position+length, NO_OF_BITS_IN_BYTE - (position+length)) == byte_read_bits(byte, position+length, NO_OF_BITS_IN_BYTE - (position+length))) # Remaining bits
#     Ensures(Result())
    
#     new_byte = Reveal(byte_set_bits(byte, value, position, length))
#     written_value = Reveal(byte_read_bits(new_byte, position, length))
    
#     new_prefix = Reveal(byte_read_bits(new_byte, 0, position))
#     old_prefix = Reveal(byte_read_bits(byte, 0, position))
    
#     post_position = position+length
#     new_suffix = Reveal(byte_read_bits(new_byte, post_position, NO_OF_BITS_IN_BYTE - post_position))
#     old_suffix = Reveal(byte_read_bits(byte, post_position, NO_OF_BITS_IN_BYTE - post_position))
    
#     return value == written_value and new_prefix == old_prefix and new_suffix == old_suffix

# Would be nice, but not that important
# Similar then also for the byteseq variant
# @Pure
# @Opaque
# def _lemma_byte_set_bit_eq(byte: int, bit: bool, position: int) -> int:
#     Requires(0 <= byte and byte <= 0xFF)
#     Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
#     Ensures(byte_set_bit(byte, bit, position) == byte_set_bits(byte, int(bit), position, 1))
#     Ensures(Result())
#     single = Reveal(byte_set_bit(byte, bit, position))
#     multiple = Reveal(byte_set_bits(byte, int(bit), position, 1))
#     return single == multiple

#endregion
#region Set Byteseq

# @Pure
# @Opaque
# def byteseq_set_bit(byteseq: PByteSeq, bit: bool, position: int) -> PByteSeq:
#     Requires(0 <= position and position < len(byteseq) * NO_OF_BITS_IN_BYTE)
#     Decreases(None)
#     Ensures(len(byteseq) == len(Result()))
#     byte_position = position // NO_OF_BITS_IN_BYTE
#     bit_position = position % NO_OF_BITS_IN_BYTE
#     return byteseq.update(byte_position, byte_set_bit(byteseq[byte_position], bit, bit_position))

# @Pure
# @Opaque
# def byteseq_set_bits(byteseq: PByteSeq, value: int, position: int, length: int) -> PByteSeq:
#     Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
#     Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
#     Requires(0 <= value and value < (1 << length))
#     Decreases(None)
#     Ensures(len(byteseq) == len(Result()))

#     if length == 0:
#         return byteseq
    
#     byte_position = position // NO_OF_BITS_IN_BYTE
#     bit_position = position % NO_OF_BITS_IN_BYTE
    
#     if bit_position + length <= NO_OF_BITS_IN_BYTE:
#         return byteseq.update(byte_position, byte_set_bits(byteseq[byte_position], value, bit_position, length))
    
#     upper_length = NO_OF_BITS_IN_BYTE - bit_position
#     upper_value = byte_read_bits(value, NO_OF_BITS_IN_BYTE - length, upper_length)
#     new_upper_byte = byte_set_bits(byteseq[byte_position], upper_value, bit_position, upper_length)
    
#     lower_length = length - upper_length
#     lower_value = byte_read_bits(value, NO_OF_BITS_IN_BYTE - lower_length, lower_length)
#     new_lower_byte = byte_set_bits(byteseq[byte_position + 1], lower_value, 0, lower_length)
    
#     return byteseq.update(byte_position, new_upper_byte).update(byte_position + 1, new_lower_byte)

# WORKS
# TODO but improve performance
# @Pure
# @Opaque
# def _lemma_byteseq_set_bits(byteseq: PByteSeq, value: int, position: int, length: int) -> bool:
#     Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
#     Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
#     Requires(0 <= value and value < (1 << length))
#     Ensures(byteseq_read_bits(byteseq_set_bits(byteseq, value, position, length), position, length) == value) # Written value
#     Ensures(Implies(len(byteseq) > position // NO_OF_BITS_IN_BYTE, byte_read_bits(byteseq_set_bits(byteseq, value, position, length)[position // NO_OF_BITS_IN_BYTE], 0, position % NO_OF_BITS_IN_BYTE) 
#             == byte_read_bits(byteseq[position // NO_OF_BITS_IN_BYTE], 0, position % NO_OF_BITS_IN_BYTE))) # Previous bits in this byte
#     Ensures(byteseq_eq_until(byteseq, byteseq_set_bits(byteseq, value, position, length), position // NO_OF_BITS_IN_BYTE)) # Previous bytes
#     Ensures(Result())
    
#     byte_position = position // NO_OF_BITS_IN_BYTE
#     bit_position = position % NO_OF_BITS_IN_BYTE
    
#     if bit_position + length <= NO_OF_BITS_IN_BYTE:
#         new_seq = Reveal(byteseq_set_bits(byteseq, value, position, length))
#         written_value = Reveal(byteseq_read_bits(new_seq, position, length))
        
#         if length == 0:
#             return True
        
#         inner = Reveal(_lemma_byte_set_bits(byteseq[byte_position], value, bit_position, length))
#         return inner and value == written_value
    
#     new_seq = Reveal(byteseq_set_bits(byteseq, value, position, length))
#     written_value = Reveal(byteseq_read_bits(new_seq, position, length))
    
#     upper_length = NO_OF_BITS_IN_BYTE - bit_position
#     upper_value = Reveal(byte_read_bits(value, NO_OF_BITS_IN_BYTE - length, upper_length))
#     upper_inner = Reveal(_lemma_byte_set_bits(byteseq[byte_position], upper_value, bit_position, upper_length))
    
#     written_upper_value = Reveal(byte_read_bits(new_seq[byte_position], bit_position, upper_length))
    
#     lower_length = length - upper_length
#     lower_value = Reveal(byte_read_bits(value, NO_OF_BITS_IN_BYTE - lower_length, lower_length))
#     lower_inner = Reveal(_lemma_byte_set_bits(byteseq[byte_position + 1], lower_value, 0, lower_length))
    
#     written_lower_value = Reveal(byte_read_bits(new_seq[byte_position + 1], 0, lower_length))
    
#     return (upper_inner and upper_value == written_upper_value and 
#             lower_inner and lower_value == written_lower_value and 
#             written_value == value)

#endregion

# def test_set() -> None:
#     seq = PByteSeq(0)
#     value = 1
#     bit_index = 0
#     length = 1
#     seq = byteseq_set_bit_index(seq, byte_read_bit(value, NO_OF_BITS_IN_BYTE - length + 0), bit_index + 0)
#     read = byteseq_read_bits(seq, length, bit_index)

#     assert value == read

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