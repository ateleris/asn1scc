"""
ASN.1 Python Verification

This module provides verification helper functions
"""

from nagini_contracts.contracts import *

from .asn1_constants import NO_OF_BITS_IN_BYTE
MAX_BITOP_LENGTH = 64

#region Helpers

@Pure
def floor_align_byte(position: PInt) -> int:
    return (position // NO_OF_BITS_IN_BYTE) * NO_OF_BITS_IN_BYTE

#endregion
#region Byteseq equality

@Pure
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

@Pure
@Opaque
def __lemma_byteseq_equal_until_transitiv(b1: PByteSeq, b2: PByteSeq, b3: PByteSeq, end: int) -> bool:
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
def __lemma_byte_read_bit_equal(byte: int, position: int) -> bool:
    Requires(0 <= byte and byte <= 0xFF)
    Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
    Decreases(None)
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
    Requires(0 <= length and length <= MAX_BITOP_LENGTH)
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
    Requires(0 <= length and length <= MAX_BITOP_LENGTH)
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
    Requires(0 <= length and length <= MAX_BITOP_LENGTH)
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

@Pure
@Opaque
def lemma_byteseq_read_bits_aligned(byteseq: PByteSeq, position: int, length: int) -> bool:
    """Proof that reading from an aligned position is equal to reading directly from that byte"""
    Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE)
    Requires(0 <= position and position // NO_OF_BITS_IN_BYTE < len(byteseq))
    Requires(position % NO_OF_BITS_IN_BYTE == 0)
    Decreases(length)
    Ensures(byteseq_read_bits(byteseq, position, length) == byte_read_bits(byteseq[position // NO_OF_BITS_IN_BYTE], 0, length))
    Ensures(Result())

    if length == 0:
        return True

    byte_pos = position // NO_OF_BITS_IN_BYTE

    byteseq_prefix = byteseq_read_bits(byteseq, position, length - 1)
    byte_prefix = byte_read_bits(byteseq[byte_pos], 0, length - 1)
    induction = lemma_byteseq_read_bits_aligned(byteseq, position, length - 1)
    Assert(byteseq_prefix == byte_prefix)

    byteseq_single = Reveal(byteseq_read_bit(byteseq, position + length - 1))
    byte_single = int(byte_read_bit(byteseq[byte_pos], length - 1))
    Assert(byteseq_single == byte_single)


    byteseq_val = Reveal(byteseq_read_bits(byteseq, position, length))
    lemma_induction = lemma_byteseq_read_bits_induction_lsb(byteseq, position, length)
    Assert((byteseq_prefix << 1) + int(byteseq_single) == byteseq_val)

    byte_val = byte_read_bits(byteseq[byte_pos], 0, length)
    lemma_induction = _lemma_byte_read_bits_induction_lsb(byteseq[byte_pos], 0, length)
    lemma_single_eq = __lemma_byte_read_bit_equal(byteseq[byte_pos], length - 1)
    Assert((byte_prefix << 1) +  int(byte_single) == byte_val)

    return byteseq_val == byte_val

@Pure
@Opaque
def lemma_byteseq_read_full_byte(byteseq: PByteSeq, position: int) -> bool:
    Requires(0 <= position and position // NO_OF_BITS_IN_BYTE < len(byteseq))
    Requires(position % NO_OF_BITS_IN_BYTE == 0)
    Decreases(None)
    Ensures(byteseq_read_bits(byteseq, position, NO_OF_BITS_IN_BYTE) == byteseq[position // NO_OF_BITS_IN_BYTE])
    Ensures(Result())

    return lemma_byteseq_read_bits_aligned(byteseq, position, NO_OF_BITS_IN_BYTE)

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
    return lemma_prefix and lemma_value

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
    lemma_byte_read = __lemma_byte_read_bit_equal(new_byte, bit_position)
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
    Requires(0 <= length and length <= MAX_BITOP_LENGTH)
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
def lemma_byteseq_set_bits_eq(byteseq: PByteSeq, value: bool, position: int) -> bool:
    Requires(0 <= position and position + 1 <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Decreases(None)
    Ensures(byteseq_set_bits(byteseq, value, position, 1) == byteseq_set_bit(byteseq, value, position))
    Ensures(True)
    
    bits = Reveal(byteseq_set_bits(byteseq, value, position, 1))
    bit = byteseq_set_bit(byteseq, value, position)
    return bits == bit
    
@Pure
@Opaque
def __lemma_byteseq_set_bits_prefix(byteseq: PByteSeq, value: int, position: int, length: int) -> bool:
    """Proof that `byteseq_set_bits()` preserves previous bits in the sequence."""
    Requires(0 <= length and length <= MAX_BITOP_LENGTH)
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
    lemma_equal_transitiv = __lemma_byteseq_equal_until_transitiv(new_seq, rec_seq, byteseq, position)
    return byteseq_equal_until(new_seq, byteseq, position)

@Pure
@Opaque
def __lemma_byteseq_set_bits_value(byteseq: PByteSeq, value: int, position: int, length: int) -> bool:
    """Proof that `byteseq_set_bits()` writes the input value."""
    Requires(0 <= length and length <= MAX_BITOP_LENGTH)
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
    Requires(0 <= length and length <= MAX_BITOP_LENGTH)
    Requires(0 <= position and position + length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << length))
    Decreases(None)
    Ensures(byteseq_equal_until(byteseq_set_bits(byteseq, value, position, length), byteseq, position))
    Ensures(byteseq_read_bits(byteseq_set_bits(byteseq, value, position, length), position, length) == value)
    Ensures(Result())
    
    lemma_prefix = __lemma_byteseq_set_bits_prefix(byteseq, value, position, length)
    lemma_value = __lemma_byteseq_set_bits_value(byteseq, value, position, length)
    return lemma_prefix and lemma_value

@Pure
@Opaque
def lemma_byteseq_set_bits_combine(byteseq: PByteSeq, value: int, upper_length: int, lower_length: int, position: int) -> bool:
    """Proof that two consecutive byteseq_set_bits calls can be combined into one"""
    Requires(upper_length == 32)
    Requires(0 <= lower_length and lower_length <= 32)
    Requires(upper_length + lower_length <= MAX_BITOP_LENGTH)
    Requires(0 <= position and position + upper_length + lower_length <= len(byteseq) * NO_OF_BITS_IN_BYTE)
    Requires(0 <= value and value < (1 << (upper_length + lower_length)))
    Decreases(lower_length)
    Ensures(byteseq_set_bits(
                byteseq_set_bits(byteseq, value >> lower_length, position, upper_length),
                value % (1 << lower_length), position + upper_length, lower_length)
            == byteseq_set_bits(byteseq, value, position, upper_length + lower_length))
    Ensures(Result())

    combined_length = upper_length + lower_length
    upper_value = value >> lower_length
    lower_value = value % (1 << lower_length)
    intermediate = byteseq_set_bits(byteseq, upper_value, position, upper_length)

    if lower_length == 0:
        return True

    lhs_full = Reveal(byteseq_set_bits(intermediate, lower_value, position + upper_length, lower_length))
    rhs_full = Reveal(byteseq_set_bits(byteseq, value, position, combined_length))

    # Aids the verification
    Assert((value >> 1) >> (lower_length - 1) == upper_value)
    Assert((value >> 1) % (1 << (lower_length - 1)) == lower_value >> 1)
    Assert(lower_value % 2 == value % 2)

    rec_lemma = lemma_byteseq_set_bits_combine(byteseq, value >> 1, upper_length, lower_length - 1, position)

    lhs_rec = byteseq_set_bits(intermediate, lower_value >> 1, position + upper_length, lower_length - 1)
    rhs_rec = byteseq_set_bits(byteseq, value >> 1, position, combined_length - 1)
    Assert(lhs_rec == rhs_rec)
    return lhs_full == rhs_full

#endregion