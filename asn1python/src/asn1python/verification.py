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
# def byte_bounds(byte: int, length: int) -> bool:
#     Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
#     return 0 <= byte and byte < (1 << length)

#region Helpers

@Pure
def floor_align_byte(position: PInt) -> int:
    return (position // NO_OF_BITS_IN_BYTE) * NO_OF_BITS_IN_BYTE

#endregion
#region Byteseq equality

@Pure
#@nagini @UsePrimitiveType
def byteseq_bytes_equal_until(b1: PByteSeq, b2: PByteSeq, end: PInt) -> bool:
    """Compares if the two bytearrays b1 and b2 are equal in the range [0, end["""
    Requires(0 <= end and end <= len(b1) and end <= len(b2))
    Decreases(None)
    return b1.take(end) == b2.take(end)

@Pure
@Opaque
def byteseq_equal_until(b1: PByteSeq, b2: PByteSeq, end: PInt) -> bool:
    """Compares if the two bytearrays b1 and b2 are equal in the bit range [0, end["""
    Requires(0 <= end and end <= len(b1) * NO_OF_BITS_IN_BYTE and end <= len(b2) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(Implies(b1 == b2, Result()))
    # Ensures(Result() == byteseq_equal_until(b2, b1, end))

    if end == 0:
        return True

    full_bytes = end // NO_OF_BITS_IN_BYTE
    bit_position = end % NO_OF_BITS_IN_BYTE

    full_bytes_eq = byteseq_bytes_equal_until(b1, b2, full_bytes)

    if bit_position > 0:
        byte1 = b1[full_bytes]
        byte2 = b2[full_bytes]
        return full_bytes_eq and byte_read_bits(byte1, 0, bit_position) == byte_read_bits(byte2, 0, bit_position)

    reverse = byteseq_equal_until(b2, b1, end)

    return full_bytes_eq

@Pure
@Opaque  
def __lemma_byteseq_equal_monotonic(b1: PByteSeq, b2: PByteSeq, end: int, prefix: int) -> bool:
    """Proof that byteseq equality is monotonic"""
    Requires(0 <= prefix and prefix <= end and end <= len(b1) * NO_OF_BITS_IN_BYTE and end <= len(b2) * NO_OF_BITS_IN_BYTE)
    Requires(byteseq_equal_until(b1, b2, end))
    Decreases(None)
    Ensures(byteseq_equal_until(b1, b2, prefix))
    Ensures(Result())
    
    if end == prefix:
        return True
    
    end_equal = Reveal(byteseq_equal_until(b1, b2, end))
    prefix_equal = Reveal(byteseq_equal_until(b1, b2, prefix))
    
    end_byte_position = end // NO_OF_BITS_IN_BYTE
    end_bit_position = end % NO_OF_BITS_IN_BYTE
    
    prefix_byte_position = prefix // NO_OF_BITS_IN_BYTE
    prefix_bit_position = prefix % NO_OF_BITS_IN_BYTE
    
    if end_byte_position == prefix_byte_position:
        byte1 = b1[end_byte_position]
        byte2 = b2[end_byte_position]
        bits_lemma = _lemma_byte_read_bits_equal_monotonic(byte1, byte2, end_bit_position, prefix_bit_position)
           
    return prefix_equal

# @Pure
# @Opaque  
# def lemma_byteseq_equal_monotonic(b1: PByteSeq, b2: PByteSeq, end: int) -> bool:
#     """Proof that byteseq equality is monotonic"""
#     Requires(len(b1) <= len(b2))
#     Requires(0 <= end and end <= len(b1) * NO_OF_BITS_IN_BYTE)
#     Requires(byteseq_equal_until(b1, b2, end))
#     Decreases(None)
#     Ensures(Forall(int, lambda i: (Implies(0 <= i and i <= end, byteseq_equal_until(b1, b2, i)), [[]])))
#     Ensures(Result())
    
#     Assert(Forall(int, lambda i: (Implies(0 <= i and i <= end, __lemma_byteseq_equal_monotonic(b1, b2, end, i)))))
#     return True

@Pure
@Opaque
def _lemma_byteseq_equal_until_transitiv(b1: PByteSeq, b2: PByteSeq, b3: PByteSeq, end: int) -> bool:
    Requires(len(b1) <= len(b2))
    Requires(len(b2) <= len(b3))
    Requires(0 <= end and end <= len(b1) * NO_OF_BITS_IN_BYTE)
    Requires(byteseq_equal_until(b1, b2, end))
    Requires(byteseq_equal_until(b2, b3, end))
    Decreases(None)
    Ensures(byteseq_equal_until(b1, b3, end))
    Ensures(Result())

    b1_to_b2 = Reveal(byteseq_equal_until(b1, b2, end))
    b2_to_b3 = Reveal(byteseq_equal_until(b2, b3, end))
    b1_to_b3 = Reveal(byteseq_equal_until(b1, b3, end))
    return b1_to_b3

#endregion
#region Read bits

@Pure
@Opaque
def byte_read_bit(byte: PInt, position: PInt) -> bool:
    """Read a single bit from a byte. Position starts from MSB."""
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    Decreases(None)
    return bool((byte >> (7 - position)) % 2)

@Pure
@Opaque
def byte_read_bits(byte: PInt, position: PInt, length: PInt) -> int:
    """Read up to 8 bits from a byte. Position starts from MSB."""
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(0 <= Result() and Result() < (1 << length))
    Ensures(Implies(byte < (1 << length) and position == NO_OF_BITS_IN_BYTE - length, Result() == byte))
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
def _lemma_byte_read_bits_induction_lsb(byte: int, position: int, length: int) -> bool:
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

    inner = _lemma_byte_read_bits_induction_lsb(byte, position, length - 1)
    return inner and full == prefix + single

@Pure
@Opaque
def _lemma_byte_read_bits_equal_monotonic(byte1: int, byte2: int, end: int, prefix: int) -> bool:
    """Proof that equality on byte_read_bits is monotonic"""
    Requires(0 <= byte1 and byte1 <= 0xFF)
    Requires(0 <= byte2 and byte2 <= 0xFF)
    Requires(0 <= prefix and prefix <= end and end <= NO_OF_BITS_IN_BYTE)
    Requires(byte_read_bits(byte1, 0, end) == byte_read_bits(byte2, 0, end))
    Decreases(end)
    Ensures(byte_read_bits(byte1, 0, prefix) == byte_read_bits(byte2, 0, prefix))
    Ensures(Result())

    if end == prefix:
        return True
    
    byte1_end = Reveal(byte_read_bits(byte1, 0, end))
    byte2_end = Reveal(byte_read_bits(byte2, 0, end))
    Assert(byte1_end == byte2_end)
    
    byte1_prefix = Reveal(byte_read_bits(byte1, 0, prefix))
    byte2_prefix = Reveal(byte_read_bits(byte2, 0, prefix))
    return byte1_prefix == byte2_prefix



#endregion
#region Read Byteseq

@Pure
@Opaque
def byteseq_read_bit(byteseq: PByteSeq, position: PInt) -> bool:
    """Read a single bit from the byte sequence."""
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
    """Read a number of bits from the byte sequence"""
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(length)
    Ensures(0 <= Result() and Result() < (1 << length))

    if length == 0:
        return 0

    prefix = byteseq_read_bits(byteseq, position, length - 1) << 1
    single = byteseq_read_bit(byteseq, position + length - 1)
    return prefix + single

@Pure
@Opaque
def _lemma_byteseq_read_bits_value(byteseq: PByteSeq, position: int, length: int, inner: int) -> bool:
    Requires(0 < length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= inner and inner < length)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(length)
    Ensures(byte_read_bit(byteseq_read_bits(byteseq, position, length), NO_OF_BITS_IN_BYTE - length + inner) 
         == byteseq_read_bit(byteseq, position + inner))
    Ensures(Result())
    
    full_read = Reveal(byteseq_read_bits(byteseq, position, length))
    single_bit = Reveal(byteseq_read_bit(byteseq, position + inner))
    
    # Requested bit is LSB
    if inner == length - 1:
        full_to_single = Reveal(byte_read_bit(full_read, NO_OF_BITS_IN_BYTE - length + inner))
        return single_bit == full_to_single
    
    
    lemma_inner = _lemma_byteseq_read_bits_value(byteseq, position, length - 1, inner)
    rec_full_read = byteseq_read_bits(byteseq, position, length - 1)
    Assert(rec_full_read == full_read >> 1)
    full_to_single_rec = Reveal(byte_read_bit(rec_full_read, NO_OF_BITS_IN_BYTE - (length - 1) + inner))
    Assert(full_to_single_rec == single_bit)
    
    full_to_single = Reveal(byte_read_bit(full_read, NO_OF_BITS_IN_BYTE - length + inner))
    return single_bit == full_to_single

@Pure
@Opaque
def lemma_byteseq_read_bits_equal(byteseq: PByteSeq, position: int) -> bool:
    """Proof that `byteseq_read_bits(byteseq, position, 1) == byteseq_read_bit(byteseq, position)`."""
    Requires(0 <= position and position + 1 <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(byteseq_read_bits(byteseq, position, 1) == int(byteseq_read_bit(byteseq, position)))
    Ensures(Result())

    repeated = Reveal(byteseq_read_bits(byteseq, position, 1))
    single = byteseq_read_bit(byteseq, position)
    return repeated == single

@Pure
@Opaque
def lemma_byteseq_read_bits_induction_lsb(byteseq: PByteSeq, position: int, length: int) -> bool:
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(length)
    Ensures(Implies(length >= 1, byteseq_read_bits(byteseq, position, length) == 
                                (byteseq_read_bits(byteseq, position, length - 1) << 1) + 
                                (byteseq_read_bits(byteseq, position + length - 1, 1))))
    Ensures(Result())
    
    if length == 0:
        return True

    full = Reveal(byteseq_read_bits(byteseq, position, length))
    prefix = Reveal(byteseq_read_bits(byteseq, position, length - 1)) << 1
    single = Reveal(byteseq_read_bits(byteseq, position + length - 1, 1))

    inner_lemma = lemma_byteseq_read_bits_induction_lsb(byteseq, position, length - 1)
    return inner_lemma and full == prefix + single

@Pure
@Opaque
def lemma_byteseq_equal_read_bits(b1: PByteSeq, b2: PByteSeq, equal_end: int, position: int, length: int) -> bool:
    """Proof that byteseq equality implies equality of byteseq_read_bits within that range. """
    Requires(0 <= equal_end and equal_end <= len(b1) * NO_OF_BITS_IN_BYTE and equal_end <= len(b2) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= equal_end)
    Requires(byteseq_equal_until(b1, b2, equal_end))
    Decreases(length)
    Ensures(byteseq_read_bits(b1, position, length) == byteseq_read_bits(b2, position, length))
    
    if length == 0:
        return True
    
    # Holds for length - 1
    lemma_rec = lemma_byteseq_equal_read_bits(b1, b2, equal_end, position, length -1)
    Assert(byteseq_read_bits(b1, position, length - 1) == byteseq_read_bits(b2, position, length - 1))
    
    # Show for new bit
    lemma_equal = Reveal(byteseq_equal_until(b1, b2, equal_end))
    
    end_byte_position = equal_end // NO_OF_BITS_IN_BYTE
    end_bit_position = equal_end % NO_OF_BITS_IN_BYTE
    
    read_position = position + length - 1
    read_byte_position = read_position // NO_OF_BITS_IN_BYTE
    read_bit_position = read_position % NO_OF_BITS_IN_BYTE
    
    if end_byte_position == read_byte_position:
        value_byte1 = Reveal(byte_read_bits(b1[end_byte_position], 0, end_bit_position))
        value_byte2 = Reveal(byte_read_bits(b2[end_byte_position], 0, end_bit_position))
        Assert(value_byte1 == value_byte2)
        
        read_bit_inner1 = Reveal(byte_read_bit(b1[end_byte_position], read_bit_position))
        read_bit_inner2 = Reveal(byte_read_bit(b2[end_byte_position], read_bit_position))
        Assert(read_bit_inner1 == read_bit_inner2)
    else:
        Assert(b1[read_byte_position] == b2[read_byte_position])
    
    read_bit1 = Reveal(byteseq_read_bit(b1, read_position))
    read_bit2 = Reveal(byteseq_read_bit(b2, read_position))
    Assert(read_bit1 == read_bit2)
    
    lemma_read_bits1 = lemma_byteseq_read_bits_equal(b1, read_position)
    lemma_read_bits2 = lemma_byteseq_read_bits_equal(b2, read_position)
    Assert(byteseq_read_bits(b1, read_position, 1) == byteseq_read_bits(b2, read_position, 1))
    
    lemma_read_induction1 = lemma_byteseq_read_bits_induction_lsb(b1, position, length)
    lemma_read_induction2 = lemma_byteseq_read_bits_induction_lsb(b2, position, length)
    return byteseq_read_bits(b1, position, length) == byteseq_read_bits(b2, position, length)

#region Set bits

@Pure
@Opaque
def byte_set_bit(byte: PInt, bit: bool, position: PInt) -> int:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(0 <= Result() and Result() <= 0xFF)

    if bit:
        return byte | (1 << (7 - position))
    else:
        return byte & ~(1 << (7 - position))

#
# Splits the byte into three parts
#
# position = 2
# length = 3
#
# |x|x|b|b|b|?|?|?|
#  0 1 2 3 4 5 6 7
#
@Pure
@Opaque
def byte_set_bits(byte: PInt, value: PInt, position: PInt, length: PInt) -> int:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Ensures(0 <= Result() and Result() <= 0xFF)
    
    upper = byte_read_bits(byte, 0, position) << (NO_OF_BITS_IN_BYTE - position)
    middle = value << (NO_OF_BITS_IN_BYTE - position - length)
    lower = byte % (1 << (NO_OF_BITS_IN_BYTE - position - length))
    return upper + middle + lower

@Pure
@Opaque
def __lemma_byte_set_bit_true_equal(byte: int, position: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    Ensures(byte_set_bit(byte, True, position) == byte_set_bits(byte, True, position, 1))
    Ensures(Result())
    
    new_byte_a = Reveal(byte_set_bit(byte, True, position))
    new_byte_b = Reveal(byte_set_bits(byte, True, position, 1))
    upper_b = Reveal(byte_read_bits(byte, 0, position))
    
    return new_byte_a == new_byte_b

@Pure
@Opaque
def __lemma_byte_set_bit_false_equal(byte: int, position: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    Ensures(byte_set_bit(byte, False, position) == byte_set_bits(byte, False, position, 1))
    Ensures(Result())
    
    new_byte_a = Reveal(byte_set_bit(byte, False, position))
    new_byte_b = Reveal(byte_set_bits(byte, False, position, 1))
    upper_b = Reveal(byte_read_bits(byte, 0, position))
    
    return new_byte_a == new_byte_b

# Splitting up the verification seems to improve performance
@Pure
@Opaque
def _lemma_byte_set_bit_equal(byte: int, bit: bool, position: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    Ensures(byte_set_bit(byte, bit, position) == byte_set_bits(byte, bit, position, 1))
    Ensures(Result())
    
    if bit:
        return __lemma_byte_set_bit_true_equal(byte, position)
    else:
        return __lemma_byte_set_bit_false_equal(byte, position)

@Pure
@Opaque
def __lemma_byte_set_bits_prefix(byte: int, value: int, position: int, length: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Ensures(byte_read_bits(byte_set_bits(byte, value, position, length), 0, position) == byte_read_bits(byte, 0, position))
    Ensures(Result())
    
    new_byte = Reveal(byte_set_bits(byte, value, position, length))
    new_upper = Reveal(byte_read_bits(new_byte, 0, position))
    upper = Reveal(byte_read_bits(byte, 0, position))
    
    return new_upper == upper

@Pure
@Opaque
def __lemma_byte_set_bits_value(byte: int, value: int, position: int, length: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Ensures(byte_read_bits(byte_set_bits(byte, value, position, length), position, length) == value)
    Ensures(Result())
    
    new_byte = Reveal(byte_set_bits(byte, value, position, length))
    written_value = Reveal(byte_read_bits(new_byte, position, length))
    return written_value == value

@Pure
@Opaque
def __lemma_byte_set_bits_suffix(byte: int, value: int, position: int, length: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Ensures(byte_read_bits(byte_set_bits(byte, value, position, length), position+length, NO_OF_BITS_IN_BYTE - (position+length)) == 
            byte_read_bits(byte, position+length, NO_OF_BITS_IN_BYTE - (position+length))) # Remaining bits
    Ensures(Result())
    
    lower_length = NO_OF_BITS_IN_BYTE - (position+length)
    new_byte = Reveal(byte_set_bits(byte, value, position, length))
    new_lower = Reveal(byte_read_bits(new_byte, position + length, lower_length))
    lower = Reveal(byte_read_bits(byte, position + length, lower_length))
    
    return new_lower == lower

@Pure
@Opaque
def _lemma_byte_set_bits(byte: int, value: int, position: int, length: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Ensures(byte_read_bits(byte_set_bits(byte, value, position, length), position, length) == value) # Written value
    Ensures(byte_read_bits(byte_set_bits(byte, value, position, length), 0, position) == byte_read_bits(byte, 0, position)) # Previous bits
    Ensures(byte_read_bits(byte_set_bits(byte, value, position, length), position+length, NO_OF_BITS_IN_BYTE - (position+length)) == byte_read_bits(byte, position+length, NO_OF_BITS_IN_BYTE - (position+length))) # Remaining bits
    Ensures(Result())
    
    lemma_prefix = __lemma_byte_set_bits_prefix(byte, value, position, length)
    lemma_value = __lemma_byte_set_bits_value(byte, value, position, length)
    lemma_suffix = __lemma_byte_set_bits_suffix(byte, value, position, length)
    return lemma_prefix and lemma_value and lemma_suffix

#endregion
#region Set Byteseq

@Pure
@Opaque
def byteseq_set_bit(byteseq: PByteSeq, bit: PBool, position: PInt) -> PByteSeq:
    Requires(0 <= position and position < len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(len(byteseq) == len(Result()))
    byte_position = position // NO_OF_BITS_IN_BYTE
    bit_position = position % NO_OF_BITS_IN_BYTE
    return byteseq.update(byte_position, byte_set_bit(byteseq[byte_position], bit, bit_position))

@Pure
@Opaque
def __lemma_byteseq_set_bit_value(byteseq: PByteSeq, bit: bool, position: int) -> bool:
    Requires(0 <= position and position < len(byteseq) * NO_OF_BITS_IN_BYTE)
    Ensures(byteseq_read_bit(byteseq_set_bit(byteseq, bit, position), position) == bit) # Written value
    Ensures(Result())
    
    byte_position = position // NO_OF_BITS_IN_BYTE
    bit_position = position % NO_OF_BITS_IN_BYTE
    byte = byteseq[byte_position]
    
    new_seq = Reveal(byteseq_set_bit(byteseq, bit, position))
    new_byte = new_seq[byte_position]
    lemma_byte_equal = _lemma_byte_set_bit_equal(byte, bit, bit_position)
    lemma_byte = __lemma_byte_set_bits_value(byte, bit, bit_position, 1)
    
    from_bits_read = bool(byte_read_bits(new_byte, bit_position, 1))
    lemma_byte_read = _lemma_byte_read_bit_equal(new_byte, bit_position)
    from_bit_read = byte_read_bit(new_byte, bit_position)
    
    from_seq_bit = Reveal(byteseq_read_bit(new_seq, position))
    
    return bit == from_bits_read and from_bits_read == from_bit_read and from_bit_read == from_seq_bit

@Pure
@Opaque
def __lemma_byteseq_set_bit_prefix(byteseq: PByteSeq, bit: bool, position: int) -> bool:
    """Prefix of PByteSeq remains the same when using byteseq_set_bit()."""
    Requires(0 <= position and position < len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(byteseq_equal_until(byteseq_set_bit(byteseq, bit, position), byteseq, position))
    Ensures(Result())
    
    byte_position = position // NO_OF_BITS_IN_BYTE
    bit_position = position % NO_OF_BITS_IN_BYTE
    floor_bit_position = floor_align_byte(position)
    Assert(bit_position == position - floor_bit_position)

    byte = byteseq[byte_position]
    
    new_seq = Reveal(byteseq_set_bit(byteseq, bit, position))
    new_byte = new_seq[byte_position]
    
    lemma_byte_equal = _lemma_byte_set_bit_equal(byte, bit, bit_position)
    lemma_byte = __lemma_byte_set_bits_prefix(byte, bit, bit_position, 1)
    byte_prefix = byte_read_bits(new_byte, 0, bit_position)
    old_byte_prefix = byte_read_bits(byte, 0, bit_position)

    equal = Reveal(byteseq_equal_until(new_seq, byteseq, position))

    return byte_prefix == old_byte_prefix and equal

@Pure
@Opaque
def _lemma_byteseq_set_bit(byteseq: PByteSeq, bit: bool, position: int) -> bool:
    Requires(0 <= position and position < len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(byteseq_read_bit(byteseq_set_bit(byteseq, bit, position), position) == bit)
    Ensures(byteseq_equal_until(byteseq_set_bit(byteseq, bit, position), byteseq, position))
    Ensures(Result())
    
    value = __lemma_byteseq_set_bit_value(byteseq, bit, position)
    prefix = __lemma_byteseq_set_bit_prefix(byteseq, bit, position)
    return value and prefix

@Pure
@Opaque
def byteseq_set_bits(byteseq: PByteSeq, value: PInt, position: PInt, length: PInt) -> PByteSeq:
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Decreases(length)
    Ensures(Implies(length == 0, Result() == byteseq))
    Ensures(len(byteseq) == len(Result()))

    if length == 0:
        return byteseq
    
    rec = byteseq_set_bits(byteseq, value >> 1, position, length - 1)
    bit = bool(value % 2)
    new_seq = byteseq_set_bit(rec, bit, position + length - 1)

    return new_seq

@Pure
@Opaque
def _lemma_byteseq_set_bits_equal(byteseq: PByteSeq, value: bool, position: int) -> bool:
    Requires(0 <= position and position + 1 <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(byteseq_set_bits(byteseq, value, position, 1) == byteseq_set_bit(byteseq, value, position))
    Ensures(Result())

    repeated = Reveal(byteseq_set_bits(byteseq, value, position, 1))
    single = byteseq_set_bit(byteseq, value, position)
    return repeated == single

@Pure
@Opaque
def __lemma_byteseq_set_bits_prefix(byteseq: PByteSeq, value: int, position: int, length: int) -> bool:
    """Proof that `byteseq_set_bits()` preserves previous bits in the sequence."""
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Decreases(length)
    Ensures(byteseq_equal_until(byteseq_set_bits(byteseq, value, position, length), byteseq, position))
    Ensures(Result())

    if length == 0:
        return byteseq_set_bits(byteseq, value, position, length) == byteseq
    
    full_seq = Reveal(byteseq_set_bits(byteseq, value, position, length))
    rec_seq = byteseq_set_bits(byteseq, value >> 1, position, length - 1)
    lemma_rec = __lemma_byteseq_set_bits_prefix(byteseq, value >> 1, position, length - 1)
    
    Assert(byteseq_equal_until(rec_seq, byteseq, position))
    
    bit = bool(value % 2)
    new_seq = byteseq_set_bit(rec_seq, bit, position + length - 1)
    lemma_set_bit = _lemma_byteseq_set_bit(rec_seq, bit, position + length - 1)
    lemma_equal_monotonic = __lemma_byteseq_equal_monotonic(new_seq, rec_seq, position + length - 1, position)
    Assert(byteseq_equal_until(new_seq, rec_seq, position))
    lemma_equal_transitiv = _lemma_byteseq_equal_until_transitiv(new_seq, rec_seq, byteseq, position)
    return byteseq_equal_until(new_seq, byteseq, position)

@Pure
@Opaque
def __lemma_byteseq_set_bits_value(byteseq: PByteSeq, value: int, position: int, length: int) -> bool:
    """Proof that `byteseq_set_bits()` writes the input value."""
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Decreases(length)
    Ensures(byteseq_read_bits(byteseq_set_bits(byteseq, value, position, length), position, length) == value)
    Ensures(Result())

    if length == 0:
        return True
    
    full_seq = Reveal(byteseq_set_bits(byteseq, value, position, length))   
    rec_seq = byteseq_set_bits(byteseq, value >> 1, position, length - 1)
    lemma_rec = __lemma_byteseq_set_bits_value(byteseq, value >> 1, position, length - 1)
    Assert(byteseq_read_bits(rec_seq, position, length - 1) == value >> 1)
    
    bit = bool(value % 2)
    set_position = position + length - 1
    new_seq = byteseq_set_bit(rec_seq, bit, set_position)
    
    lemma_set_bit = _lemma_byteseq_set_bit(rec_seq, bit, set_position)
    lemma_read_equal = lemma_byteseq_read_bits_equal(new_seq, set_position)
    Assert(byteseq_read_bits(new_seq, set_position, 1) == int(bit))
    
    lemma_read_equality = lemma_byteseq_equal_read_bits(new_seq, rec_seq, set_position, position, length - 1)
    Assert(byteseq_read_bits(new_seq, position, length - 1) == value >> 1)
    
    lemma_read_induction = lemma_byteseq_read_bits_induction_lsb(new_seq, position, length)
    return byteseq_read_bits(new_seq, position, length) == value
    
@Pure
@Opaque
def lemma_byteseq_set_bits(byteseq: PByteSeq, value: int, position: int, length: int) -> bool:
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Decreases(None)
    Ensures(byteseq_equal_until(byteseq_set_bits(byteseq, value, position, length), byteseq, position))
    Ensures(byteseq_read_bits(byteseq_set_bits(byteseq, value, position, length), position, length) == value)
    Ensures(Result())
    
    lemma_prefix = __lemma_byteseq_set_bits_prefix(byteseq, value, position, length)
    lemma_value = __lemma_byteseq_set_bits_value(byteseq, value, position, length)
    return lemma_prefix and lemma_value

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