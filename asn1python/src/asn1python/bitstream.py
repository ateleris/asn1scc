"""
ASN.1 Python Runtime Library - BitStream Operations

This module provides bit-level reading and writing operations
that match the behavior of the C and Scala bitstream implementations.
"""

from typing import List
from .helper import *
from .asn1_constants import NO_OF_BITS_IN_BYTE

from nagini_contracts.contracts import *
from .verification import *
from .segment import *

class BitStreamError(Exception):
    """Base class for bitstream errors"""
    pass

class BitStream:
    """
    Bit-level reading and writing operations for ASN.1 encoding/decoding.

    This class provides precise bit manipulation capabilities required for
    ASN.1 encoding rules like UPER and ACN.
    """
    #region Ghost Functions

    @Pure
    @staticmethod
    def position_invariant(bit_position: int, byte_position: int, buf_length: int) -> bool:
       return (bit_position >= 0 and bit_position < NO_OF_BITS_IN_BYTE and
               byte_position >= 0 and ((byte_position < buf_length) or (bit_position == 0 and byte_position == buf_length)))
    
    @Pure
    @staticmethod
    def to_bit_index(bit: int, byte: int) -> int:
        return byte * NO_OF_BITS_IN_BYTE + bit
    
    @Pure
    @staticmethod
    def _remaining_bits(bit_position: int, byte_position: int, buf_length: int) -> int:
        Requires(0 <= bit_position and 0 <= byte_position and 0 <= buf_length)
        Requires(BitStream.position_invariant(bit_position, byte_position, buf_length))
        return (buf_length * NO_OF_BITS_IN_BYTE) - BitStream.to_bit_index(bit_position, byte_position)

    @Pure
    def validate_offset(self, bits: int) -> bool:
        Requires(Rd(self.bitstream_invariant()))
        Requires(0 <= bits)
        Ensures(Implies(Result(), bits <= self.remaining_bits))
        Unfold(Rd(self.bitstream_invariant()))
        return BitStream._remaining_bits(self._current_bit, self._current_byte, len(self._buffer)) >= bits

    @Predicate
    def bitstream_invariant(self) -> bool:
        return (Acc(self._current_bit) and Acc(self._current_byte) and 
                Acc(self._buffer) and Acc(bytearray_pred(self._buffer)) and
                BitStream.position_invariant(self._current_bit, self._current_byte, len(self._buffer)))

    @Predicate
    def segments_predicate(self, byteseq: PByteSeq) -> bool:
        return (Acc(self._segments) and segments_invariant(byteseq, self._segments) and 
                Acc(self._segments_read_index) and 0 <= self._segments_read_index and self._segments_read_index <= len(self._segments))
    
    @Pure
    def segments_read_aligned(self, read_length: int) -> bool:
        Requires(self.bitstream_invariant())
        Requires(self.segments_predicate(self.buffer()))
        Decreases(None)
        return (self.remaining_bits >= read_length and # Should be implicit by the remaining conditions
                segments_total_length(segments_take(self.segments, self.segments_read_index)) == self.current_used_bits and
                self.segments_read_index < len(self.segments) and 
                self.segments[self.segments_read_index].length == read_length)

    #endregion

    def __init__(self, data: bytearray):
        Requires(Acc(bytearray_pred(data), 1/20))
        """
        Initialize a BitStream.

        Args:
            data: Initial data buffer
        """
        self._buffer = bytearray(data)
        self._current_bit = 0  # Current bit within byte (0-7)
        self._current_byte = 0  # Current byte position (0-based)
        self._segments: PSeq[Segment] = PSeq()
        self._segments_read_index = 0
        Fold(self.bitstream_invariant())
        Fold(self.segments_predicate(self.buffer()))
        
        Ensures(Acc(bytearray_pred(data), 1/20))
        Ensures(ToByteSeq(data) is Old(ToByteSeq(data)))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_bit_position == 0)
        Ensures(self.current_byte_position == 0)
        Ensures(self.buffer() is ToByteSeq(data))
        Ensures(self.segments_predicate(self.buffer()))
        Ensures(len(self.segments) == 0)
        Ensures(self.segments_read_index == 0)
    
    @classmethod
    def from_bitstream(cls, other: 'BitStream') -> 'BitStream':
        """Ghost method to create a BitStream from an existing BitStream. Copies buffer and segments"""
        Requires(Acc(other.bitstream_invariant(), 1/20) and Acc(other.segments_predicate(other.buffer()), 1/20))
        Ensures(Acc(other.bitstream_invariant(), 1/20) and Acc(other.segments_predicate(other.buffer()), 1/20))
        Ensures(Result().bitstream_invariant())
        Ensures(Result().current_bit_position == 0)
        Ensures(Result().current_byte_position == 0)
        Ensures(Result().buffer() is other.buffer())
        Ensures(Result().segments_predicate(Result().buffer()))
        Ensures(Result().segments is other.segments)
        Ensures(Result().segments_read_index == 0)
        
        Unfold(Acc(other.bitstream_invariant(), 1/20))
        result = cls(other._buffer)
        Fold(Acc(other.bitstream_invariant(), 1/20))
        
        Unfold(result.segments_predicate(result.buffer()))
        result._segments = other.segments
        Fold(result.segments_predicate(result.buffer()))
        return result
    
    def get_data(self) -> bytearray:
        """Get the used data buffer"""
        Requires(Acc(self.bitstream_invariant(), 1/100))
        Ensures(Acc(self.bitstream_invariant(), 1/100))
        Ensures(Acc(bytearray_pred(Result())))

        used_bytes = self.current_used_bytes
        Unfold(Acc(self.bitstream_invariant(), 1/100))
        data = self._buffer[:used_bytes]
        Fold(Acc(self.bitstream_invariant(), 1/100))
        return data
    
    def to_hex_string(self) -> str:
        """Convert the bitstream data to a hex string"""
        Requires(Acc(self.bitstream_invariant(), 1/100))
        Ensures(Acc(self.bitstream_invariant(), 1/100))
        return self.get_data().hex()

    # @Pure
    # def __str__(self) -> str:
    #     """String representation for debugging"""
    #     Requires(Rd(self.bitstream_invariant()))
    #     return f"BitStream(size={self.buffer_size_bits} bits, pos={self._current_bit}, data={self.to_hex_string()})"

    #region Properties

    @property
    def current_bit_position(self) -> int:
        """Get the current bit position"""
        Requires(Rd(self.bitstream_invariant()))
        Ensures(0 <= Result() and Result() <= NO_OF_BITS_IN_BYTE)
        Ensures(Result() == self.current_used_bits % NO_OF_BITS_IN_BYTE)
        Unfold(Rd(self.bitstream_invariant()))
        return self._current_bit

    @property
    def current_byte_position(self) -> int:
        """Get the current byte position"""
        Requires(Rd(self.bitstream_invariant()))
        Ensures(0 <= Result() and Result() <= self.buffer_size)
        Ensures(Result() == self.current_used_bits // NO_OF_BITS_IN_BYTE)
        Unfold(Rd(self.bitstream_invariant()))
        return self._current_byte

    @property
    def buffer_size(self) -> int:
        """Get the buffer size in bytes"""
        Requires(Rd(self.bitstream_invariant()))
        Unfold(Rd(self.bitstream_invariant()))
        return len(self._buffer)
    
    @property
    def buffer_size_bits(self) -> int:
        """Get the buffer size in bits"""
        Requires(Rd(self.bitstream_invariant()))
        return self.buffer_size * NO_OF_BITS_IN_BYTE

    @property
    def current_used_bits(self) -> int:
        """Get the number of bits currently used"""
        Requires(Rd(self.bitstream_invariant()))
        Ensures(0 <= Result() and Result() <= self.buffer_size_bits)
        Unfold(Rd(self.bitstream_invariant()))
        return self._current_byte * NO_OF_BITS_IN_BYTE + self._current_bit

    @property
    def current_used_bytes(self) -> int:
        Requires(Rd(self.bitstream_invariant()))
        return self.current_byte_position + (1 if self.current_bit_position > 0 else 0)

    @property
    def remaining_bits(self) -> int:
        """Get the number of bits remaining to be read"""
        Requires(Rd(self.bitstream_invariant()))
        Ensures(Result() == Unfolding(Rd(self.bitstream_invariant()), BitStream._remaining_bits(self._current_bit, self._current_byte, len(self._buffer))))
        Ensures(Result() == self.buffer_size_bits - self.current_used_bits)
        return self.buffer_size * NO_OF_BITS_IN_BYTE - self.current_used_bits

    @Pure
    def buffer(self) -> PByteSeq:
        Requires(Rd(self.bitstream_invariant()))
        Ensures(len(Result()) == self.buffer_size)
        return Unfolding(Rd(self.bitstream_invariant()), ToByteSeq(self._buffer))

    @property
    def segments(self) -> PSeq[Segment]:
        Requires(Rd(self.bitstream_invariant()))
        Requires(Rd(self.segments_predicate(self.buffer())))
        Ensures(segments_invariant(Unfolding(Rd(self.segments_predicate(self.buffer())), self.buffer()), Result()))
        Unfold(Rd(self.segments_predicate(self.buffer())))
        return self._segments
    
    @property
    def segments_read_index(self) -> int:
        Requires(Rd(self.bitstream_invariant()))
        Requires(Rd(self.segments_predicate(self.buffer())))
        Ensures(0 <= Result() and Result() <= len(self.segments))
        Unfold(Rd(self.segments_predicate(self.buffer())))
        return self._segments_read_index

    #endregion    

    def set_position(self, bit_position: int, byte_position: int) -> None:
        """Set the current bit and byte position"""
        Requires(self.bitstream_invariant())
        Requires(BitStream.position_invariant(bit_position, byte_position, self.buffer_size))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_bit_position == bit_position)
        Ensures(self.current_byte_position == byte_position)
        Ensures(self.buffer() is Old(self.buffer()))

        if not BitStream.position_invariant(bit_position, byte_position, self.buffer_size):
            raise BitStreamError(f"Position {byte_position}.{bit_position} out of range for buffer of size {self.buffer_size}")

        Unfold(self.bitstream_invariant())
        self._current_bit = bit_position
        self._current_byte = byte_position
        Fold(self.bitstream_invariant())

    def reset(self) -> None:
        """Reset the bit position to the beginning"""
        Requires(self.bitstream_invariant())
        Requires(self.segments_predicate(self.buffer()))
        Ensures(self.bitstream_invariant())
        Ensures(self.segments_predicate(self.buffer()))
        Ensures(self.current_bit_position == 0)
        Ensures(self.current_byte_position == 0)
        Ensures(self.buffer() is Old(self.buffer()))
        Ensures(self.segments is Old(self.segments))
        Ensures(self.segments_read_index == 0)

        self.set_position(0, 0)
        Unfold(self.segments_predicate(self.buffer()))     
        self._segments_read_index = 0
        Fold(self.segments_predicate(self.buffer()))

    def set_bit_index(self, bit_index: int) -> None:
        """Set the current bit index"""
        Requires(self.bitstream_invariant())
        Requires(0 <= bit_index and bit_index <= self.buffer_size_bits)
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == bit_index)
        Ensures(self.buffer() is Old(self.buffer()))

        bit_position = bit_index % NO_OF_BITS_IN_BYTE
        byte_position = bit_index // NO_OF_BITS_IN_BYTE
        self.set_position(bit_position, byte_position)

    def _shift_bit_index(self, amount: int = 1) -> None:
        """Shift the current bit index by given amount"""
        Requires(self.bitstream_invariant())
        Requires(0 <= amount)
        Requires(self.validate_offset(amount))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits + amount))
        Ensures(self.buffer() is Old(self.buffer()))

        new_index = self.current_used_bits + amount
        self.set_bit_index(new_index)

    def _increment_segment_read_index(self) -> None:
        Requires(Acc(self.bitstream_invariant(), 1/20))
        Requires(self.segments_predicate(self.buffer()))
        Requires(self.segments_read_index < len(self.segments))
        Ensures(Acc(self.bitstream_invariant(), 1/20))
        Ensures(self.segments_predicate(self.buffer()))
        Ensures(self.segments == Old(self.segments))
        Ensures(self.segments_read_index == Old(self.segments_read_index + 1))
        Ensures(segments_take(self.segments, self.segments_read_index) ==
            segments_take(self.segments, Old(self.segments_read_index)) + PSeq(self.segments[Old(self.segments_read_index)]))

        Unfold(self.segments_predicate(self.buffer()))
        self._segments_read_index += 1
        Fold(self.segments_predicate(self.buffer()))

    def write_align_to_byte(self) -> int:
        Requires(self.bitstream_invariant())
        Requires(self.segments_predicate(self.buffer()))
        Requires(segments_total_length(self.segments) == self.current_used_bits)
        
        Ensures(self.bitstream_invariant())
        Ensures(self.segments_predicate(self.buffer()))
        Ensures(self.buffer() is Old(self.buffer()))
        Ensures(Result() == Old((NO_OF_BITS_IN_BYTE - self.current_bit_position) % NO_OF_BITS_IN_BYTE))
        Ensures(self.current_used_bits == Old(self.current_used_bits) + Result())
        Ensures(segments_total_length(self.segments) == self.current_used_bits)
        Ensures(Let(Old((NO_OF_BITS_IN_BYTE - self.current_bit_position) % NO_OF_BITS_IN_BYTE), bool, lambda length:
            self.segments == Old(self.segments) + PSeq(Segment(length, byteseq_read_bits(self.buffer(), Old(self.current_used_bits), length)))))
        
        length = (NO_OF_BITS_IN_BYTE - self.current_bit_position) % NO_OF_BITS_IN_BYTE
        self._shift_bit_index(length)
        
        value = byteseq_read_bits(self.buffer(), Old(self.current_used_bits), length)
        Unfold(self.segments_predicate(self.buffer()))
        
        rec_segments = self._segments
        self._segments = self._segments + PSeq(Segment(length, value))
        
        Assert(segments_take(self._segments, len(self._segments) - 1) == rec_segments)        
        Fold(self.segments_predicate(self.buffer()))
        return length

    def read_align_to_byte(self) -> int:
        Requires(self.bitstream_invariant())
        Requires(self.segments_predicate(self.buffer()))
        Requires(self.segments_read_index < len(self.segments))
        
        Ensures(self.bitstream_invariant())
        Ensures(self.segments_predicate(self.buffer()))
        
        Ensures(self.buffer() is Old(self.buffer()))
        Ensures(self.segments is Old(self.segments))
        Ensures(Result() == Old((NO_OF_BITS_IN_BYTE - self.current_bit_position) % NO_OF_BITS_IN_BYTE))
        Ensures(self.current_used_bits == Old(self.current_used_bits) + Result())
        Ensures(self.segments_read_index == Old(self.segments_read_index + 1))
        
        length = (NO_OF_BITS_IN_BYTE - self.current_bit_position) % NO_OF_BITS_IN_BYTE
        self._shift_bit_index(length)   
        self._increment_segment_read_index()
        return length

    #region Read
        
    @Pure
    @Opaque
    def __read_current_bit_pure(self) -> bool:
        Requires(Rd(self.bitstream_invariant()))
        Requires(1 <= self.remaining_bits)
        Unfold(Rd(self.bitstream_invariant()))
        return bool((self._buffer[self._current_byte] >> (7 - self._current_bit)) % 2)

    @Pure
    @Opaque
    def _lemma_read_current_bit_pure(self) -> bool:
        Requires(Rd(self.bitstream_invariant()))
        Requires(1 <= self.remaining_bits)
        Ensures(self.__read_current_bit_pure() == byteseq_read_bit(self.buffer(), self.current_used_bits))
        Ensures(Result())
    
        ghost_buf = self.buffer()
        ghost_index = self.current_used_bits
        ghost_byte_pos = ghost_index // NO_OF_BITS_IN_BYTE
        ghost_bit_pos = ghost_index % NO_OF_BITS_IN_BYTE
        ghost_byte = ghost_buf[ghost_byte_pos]
    
        ghost_bit = Reveal(byteseq_read_bit(ghost_buf, ghost_index))
        read_bit = Reveal(self.__read_current_bit_pure())
    
        Unfold(Rd(self.bitstream_invariant()))
        bit_pos_eq = self._current_bit == ghost_bit_pos
        byte_eq = self._buffer[self._current_byte] == ghost_byte
    
        return bit_pos_eq and byte_eq and ghost_bit == read_bit 


    def __read_bit(self) -> bool:
        """Read a single bit"""
        Requires(self.bitstream_invariant())
        Requires(1 <= self.remaining_bits)
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits + 1))
        Ensures(self.buffer() is Old(self.buffer()))
        Ensures(Result() == Old(byteseq_read_bit(self.buffer(), self.current_used_bits)))
        Ensures(int(Result()) == byteseq_read_bits(self.buffer(), Old(self.current_used_bits), 1))

        ghost = self._lemma_read_current_bit_pure()
        ghost = lemma_byteseq_read_bits_equal(self.buffer(), self.current_used_bits)

        res = self.__read_current_bit_pure()
        self._shift_bit_index(1)
        return res
    
    def read_bit(self) -> bool:
        """Read a single bit"""
        return self.__read_bit()

    def read_bits(self, bit_count: int) -> int:
        """Read up to 32 bits"""
        Requires(self.bitstream_invariant())
        Requires(self.segments_predicate(self.buffer()))
        Requires(0 <= bit_count and bit_count <= MAX_BITOP_LENGTH)
        Requires(self.validate_offset(bit_count))
        Ensures(self.bitstream_invariant())
        Ensures(self.segments_predicate(self.buffer()))
        Ensures(self.current_used_bits == Old(self.current_used_bits + bit_count))
        Ensures(self.buffer() is Old(self.buffer()))
        Ensures(Result() == byteseq_read_bits(self.buffer(), Old(self.current_used_bits), bit_count))
        Ensures(self.segments is Old(self.segments))
        Ensures(Implies(Old(self.segments_read_aligned(bit_count)), (
            Result() == self.segments[Old(self.segments_read_index)].value and
            self.segments_read_index == Old(self.segments_read_index + 1) and
            segments_total_length(segments_take(self.segments, self.segments_read_index)) == self.current_used_bits)))
       
        value = 0
        i = 0
        while i < bit_count:
            Invariant(self.bitstream_invariant())
            Invariant(0 <= i and i <= bit_count)
            Invariant(self.validate_offset(bit_count - i))
            Invariant(self.current_used_bits == Old(self.current_used_bits + i))
            Invariant(self.buffer() is Old(self.buffer()))
            Invariant(value == byteseq_read_bits(self.buffer(), Old(self.current_used_bits), i))

            next_bit = int(self.__read_bit())
            value = (value << 1) + next_bit
            
            Assert(next_bit == byteseq_read_bits(self.buffer(), Old(self.current_used_bits) + i, 1))
            ghost = lemma_byteseq_read_bits_induction_lsb(self.buffer(), Old(self.current_used_bits), i + 1)
            i = i + 1

        if Old(self.segments_read_aligned(bit_count)):
            Unfold(self.segments_predicate(self.buffer()))
            Fold(self.segments_predicate(self.buffer()))
            lemma_segments_contained_read(self.buffer(), self.segments, self.segments_read_index)
            
            self._increment_segment_read_index()

        return value

    #endregion

    #region Write

    @Pure
    @Opaque
    def __byte_set_bit(self, byte: int, bit: bool, position: int) -> int:
        Requires(0 <= byte and byte <= 0xFF)
        Requires(0 <= position and position < NO_OF_BITS_IN_BYTE)
        Decreases(None)
        Ensures(0 <= Result() and Result() <= 0xFF)
        Ensures(Result() == byte_set_bit(byte, bit, position))
        equivalent = Reveal(byte_set_bit(byte, bit, position))

        if bit:
            return byte | (1 << (7 - position))
        else:
            return byte & ~(1 << (7 - position))

    # cur bit = 3
    #
    # |x|x|x|b|?|?|?|?|
    #  0 1 2 3 4 5 6 7
    def __write_bit(self, bit: bool) -> None:
        """Write a single bit"""
        Requires(self.bitstream_invariant())
        Requires(self.validate_offset(1))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits) + 1)
        Ensures(self.buffer_size == Old(self.buffer_size))
        Ensures(self.buffer() == Old(byteseq_set_bit(self.buffer(), bit, self.current_used_bits)))
        
        ghost_buf = self.buffer()
        ghost_index = self.current_used_bits
        ghost = Reveal(byteseq_set_bit(ghost_buf, bit, ghost_index))

        Unfold(self.bitstream_invariant())
        val = self._buffer[self._current_byte]
        self._buffer[self._current_byte] = self.__byte_set_bit(val, bit, self._current_bit)
        
        Fold(self.bitstream_invariant())
        self._shift_bit_index(1)

    def write_bit(self, bit: bool) -> None:
        Requires(self.bitstream_invariant())
        Requires(self.segments_predicate(self.buffer()))
        Requires(self.validate_offset(1))
        # self.current_used_bits could theoretically be less than segments_total_length, because of reads and resets
        Requires(segments_total_length(self.segments) == self.current_used_bits)

        Ensures(self.bitstream_invariant())
        Ensures(self.segments_predicate(self.buffer()))
        Ensures(self.current_used_bits == Old(self.current_used_bits + 1))
        Ensures(self.buffer_size == Old(self.buffer_size))
        Ensures(self.buffer() is byteseq_set_bit(Old(self.buffer()), bit, Old(self.current_used_bits)))
        Ensures(self.segments is Old(self.segments) + PSeq(Segment(1, int(bit))))
        Ensures(segments_total_length(self.segments) == self.current_used_bits)
        
        if self.remaining_bits < 1:
            raise BitStreamError("Cannot write beyond end of bitstream")
        
        Unfold(self.segments_predicate(self.buffer()))
        
        self.__write_bit(bit)
        
        eq_lemma = lemma_byteseq_set_bits_eq(Old(self.buffer()), bit, Old(self.current_used_bits))
        lemma = lemma_byteseq_set_bits(Old(self.buffer()), bit, Old(self.current_used_bits), 1)
        
        # Establish new segment
        lemma_byteseq_equal_segments_contained(self.buffer(), Old(self.buffer()), Old(self.current_used_bits), self._segments)
        self._segments = segments_add(self._segments, 1, bit)    
        Fold(self.segments_predicate(self.buffer()))

    def write_bits(self, value: int, bit_count: int) -> None:
        """Write up to 32 bits"""
        Requires(self.bitstream_invariant())
        Requires(self.segments_predicate(self.buffer()))
        Requires(0 <= bit_count and bit_count <= MAX_BITOP_LENGTH) 
        Requires(0 <= value and value < (1 << (bit_count)))
        Requires(self.validate_offset(bit_count))
        # self.current_used_bits could theoretically be less than segments_total_length, because of reads and resets
        Requires(segments_total_length(self.segments) == self.current_used_bits)

        Ensures(self.bitstream_invariant())
        Ensures(self.segments_predicate(self.buffer()))
        Ensures(self.current_used_bits == Old(self.current_used_bits + bit_count))
        Ensures(self.buffer_size == Old(self.buffer_size))
        Ensures(self.buffer() is byteseq_set_bits(Old(self.buffer()), value, Old(self.current_used_bits), bit_count))
        Ensures(self.segments is Old(self.segments) + PSeq(Segment(bit_count, value)))
        Ensures(segments_total_length(self.segments) == self.current_used_bits)
        
        # Check if value fits in bit_count bits
        if value < 0 or value >= (1 << bit_count):
            raise BitStreamError(f"Value {value} does not fit in {bit_count} bits")
        
        ghost_current_value = 0
        i: int = 0
        
        Unfold(self.segments_predicate(self.buffer()))
        Assert(segments_contained(self.buffer(), self._segments))

        while i < bit_count:
            Invariant(self.bitstream_invariant())
            Invariant(0 <= i and i <= bit_count)
            Invariant(self.validate_offset(bit_count - i))
            Invariant(self.current_used_bits == Old(self.current_used_bits + i))
            Invariant(ghost_current_value == value >> (bit_count - i))
            Invariant(self.buffer() is byteseq_set_bits(Old(self.buffer()), ghost_current_value, Old(self.current_used_bits), i))

            bit = bool((value >> (bit_count - 1 - i)) % 2)
            self.__write_bit(bit)
            
            ghost_current_value = (ghost_current_value << 1) + bit
            updated_seq = Reveal(byteseq_set_bits(Old(self.buffer()), ghost_current_value, Old(self.current_used_bits), i + 1))
            i = i + 1
            
        Assert(ghost_current_value == value)
        lemma = lemma_byteseq_set_bits(Old(self.buffer()), value, Old(self.current_used_bits), bit_count)

        # Establish new segments
        lemma_byteseq_equal_segments_contained(self.buffer(), Old(self.buffer()), Old(self.current_used_bits), self._segments)
        self._segments = segments_add(self._segments, bit_count, value)    
        Fold(self.segments_predicate(self.buffer()))
        
    #endregion