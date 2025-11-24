"""
ASN.1 Python Runtime Library - BitStream Operations

This module provides bit-level reading and writing operations
that match the behavior of the C and Scala bitstream implementations.
"""

from nagini_contracts.contracts import *
from typing import Optional, List, Tuple
from verification import *
from segment import Segment, segments_contained, segment_invariant, segments_invariant

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

    #@nagini @Pure
    @staticmethod
    def position_invariant(bit_position: int, byte_position: int, buf_length: int) -> bool:
        return (bit_position >= 0 and bit_position < NO_OF_BITS_IN_BYTE and
                byte_position >= 0 and ((byte_position < buf_length) or (bit_position == 0 and byte_position == buf_length)))
    
    #@nagini @Pure
    @staticmethod
    def to_bit_index(bit: int, byte: int) -> int:
        return byte * NO_OF_BITS_IN_BYTE + bit
    
    #@nagini @Pure
    @staticmethod
    def _remaining_bits(bit_position: int, byte_position: int, buf_length: int) -> int:
        #@nagini Requires(0 <= bit_position and 0 <= byte_position and 0 <= buf_length)
        #@nagini Requires(BitStream.position_invariant(bit_position, byte_position, buf_length))
        return (buf_length * NO_OF_BITS_IN_BYTE) - BitStream.to_bit_index(bit_position, byte_position)
    
    #@nagini @Pure
    @staticmethod
    def _bit_index(bit_position: int, byte_position: int, buf_length: int) -> int:
        #@nagini Requires(BitStream.position_invariant(bit_position, byte_position, buf_length))
        #@nagini Ensures(0 <= Result() and Result() <= buf_length * NO_OF_BITS_IN_BYTE)
        #@nagini Ensures(Result() == buf_length * NO_OF_BITS_IN_BYTE - BitStream._remaining_bits(bit_position, byte_position, buf_length))
        return BitStream.to_bit_index(bit_position, byte_position)
    
    #@nagini @Pure
    @staticmethod
    def _validate_offset_bits(bit_position: int, byte_position: int, buf_length: int, bits: int) -> bool:
        #@nagini Requires(0 <= bit_position and 0 <= byte_position and 0 <= buf_length)
        #@nagini Requires(BitStream.position_invariant(bit_position, byte_position, buf_length))
        #@nagini Requires(0 <= bits)
        return BitStream._remaining_bits(bit_position, byte_position, buf_length) >= bits

    #@nagini @Pure
    def validate_offset(self, bits: int) -> bool:
        #@nagini Requires(Rd(self.bitstream_invariant()))
        #@nagini Requires(0 <= bits)
        Ensures(Implies(Result(), bits <= self.remaining_bits))
        #@nagini Unfold(Rd(self.bitstream_invariant()))
        return BitStream._validate_offset_bits(self._current_bit, self._current_byte, len(self._buffer), bits)
    
    @Predicate
    def bitstream_invariant(self) -> bool:
        return (Acc(self._current_bit) and Acc(self._current_byte) and 
                Acc(self._buffer) and Acc(bytearray_pred(self._buffer)) and
                BitStream.position_invariant(self._current_bit, self._current_byte, len(self._buffer)))

    @Predicate
    def segments_predicate(self) -> bool:
        return (self.bitstream_invariant() and Acc(self.segments) and segments_invariant(self.buffer(), self.segments))

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
        self.segments: PSeq[Segment] = PSeq()
        #@nagini Fold(self.bitstream_invariant())
        Fold(self.segments_predicate())
        
        #@nagini Ensures(Acc(bytearray_pred(data), 1/20))
        #@nagini Ensures(self.bitstream_invariant())
        #@nagini Ensures(self.current_bit_position == 0)
        #@nagini Ensures(self.current_byte_position == 0)
        #@nagini Ensures(self.buffer() == ToByteSeq(data))
        Ensures(self.segments_predicate())
    
    #region Properties

    @property
    def current_bit_position(self) -> int:
        """Get the current bit position"""
        #@nagini Requires(Rd(self.bitstream_invariant()))
        #@nagini Ensures(0 <= Result() and Result() <= NO_OF_BITS_IN_BYTE)
        #@nagini Ensures(Result() == self.current_used_bits % NO_OF_BITS_IN_BYTE)
        #@nagini Unfold(Rd(self.bitstream_invariant()))
        return self._current_bit

    @property
    def current_byte_position(self) -> int:
        """Get the current byte position"""
        #@nagini Requires(Rd(self.bitstream_invariant()))
        #@nagini Ensures(0 <= Result() and Result() <= self.buffer_size)
        #@nagini Ensures(Result() == self.current_used_bits // NO_OF_BITS_IN_BYTE)
        #@nagini Unfold(Rd(self.bitstream_invariant()))
        return self._current_byte

    @property
    def buffer_size(self) -> int:
        """Get the buffer size in bytes"""
        #@nagini Requires(Rd(self.bitstream_invariant()))
        #@nagini Unfold(Rd(self.bitstream_invariant()))
        return len(self._buffer)
    
    @property
    def buffer_size_bits(self) -> int:
        """Get the buffer size in bits"""
        #@nagini Requires(Rd(self.bitstream_invariant()))
        return self.buffer_size * NO_OF_BITS_IN_BYTE

    @property
    def current_used_bits(self) -> int:
        #@nagini Requires(Rd(self.bitstream_invariant()))
        #@nagini Ensures(0 <= Result() and Result() <= self.buffer_size_bits)
        #@nagini Unfold(Rd(self.bitstream_invariant()))
        return self._current_byte * NO_OF_BITS_IN_BYTE + self._current_bit

    @property
    def current_used_bytes(self) -> int:
        #@nagini Requires(Rd(self.bitstream_invariant()))
        return self.current_byte_position + (1 if self.current_bit_position > 0 else 0)

    @property
    def remaining_bits(self) -> int:
        #@nagini Requires(Rd(self.bitstream_invariant()))
        #@nagini Ensures(Result() == Unfolding(Rd(self.bitstream_invariant()), BitStream._remaining_bits(self._current_bit, self._current_byte, len(self._buffer))))
        #@nagini Ensures(Result() == self.buffer_size_bits - self.current_used_bits)
        return self.buffer_size * NO_OF_BITS_IN_BYTE - self.current_used_bits

    @Pure
    def buffer(self) -> PByteSeq:
        #@nagini Requires(Rd(self.bitstream_invariant()))
        Ensures(len(Result()) == self.buffer_size)
        return Unfolding(Rd(self.bitstream_invariant()), ToByteSeq(self._buffer))

    #endregion    

    def set_position(self, bit_position: int, byte_position: int) -> None:
        """Set the current bit and byte position"""
        #@nagini Requires(self.bitstream_invariant())
        #@nagini Requires(BitStream.position_invariant(bit_position, byte_position, self.buffer_size))
        #@nagini Ensures(self.bitstream_invariant())
        #@nagini Ensures(self.current_bit_position == bit_position)
        #@nagini Ensures(self.current_byte_position == byte_position)
        #@nagini Ensures(self.buffer() == Old(self.buffer()))

        if not BitStream.position_invariant(bit_position, byte_position, self.buffer_size):
            raise BitStreamError(f"Position {byte_position}.{bit_position} out of range for buffer of size {self.buffer_size}")
        
        #@nagini Unfold(self.bitstream_invariant())
        self._current_bit = bit_position
        self._current_byte = byte_position
        #@nagini Fold(self.bitstream_invariant())

    def reset(self) -> None:
        """Reset the bit position to the beginning"""
        #@nagini Requires(self.bitstream_invariant())
        #@nagini Ensures(self.bitstream_invariant())
        #@nagini Ensures(self.current_bit_position == 0)
        #@nagini Ensures(self.current_byte_position == 0)
        #@nagini Ensures(self.buffer() == Old(self.buffer()))

        self.set_position(0, 0)

    def set_bit_index(self, bit_index: int) -> None:
        """Set the current bit index"""
        #@nagini Requires(self.bitstream_invariant())
        #@nagini Requires(0 <= bit_index and bit_index <= self.buffer_size_bits)
        #@nagini Ensures(self.bitstream_invariant())
        #@nagini Ensures(self.current_used_bits == bit_index)
        #@nagini Ensures(self.buffer() == Old(self.buffer()))

        bit_position = bit_index % NO_OF_BITS_IN_BYTE
        byte_position = bit_index // NO_OF_BITS_IN_BYTE
        self.set_position(bit_position, byte_position)

    def _shift_bit_index(self, amount: int = 1) -> None:
        """Shift the current bit index by given amount"""
        #@nagini Requires(self.bitstream_invariant())
        #@nagini Requires(0 <= amount)
        #@nagini Requires(self.validate_offset(amount))
        #@nagini Ensures(self.bitstream_invariant())
        #@nagini Ensures(self.current_used_bits == Old(self.current_used_bits + amount))
        #@nagini Ensures(self.buffer() == Old(self.buffer()))

        new_index = self.current_used_bits + amount
        self.set_bit_index(new_index)
    
    #region Read                   
        
    @Pure
    @Opaque
    def _read_current_bit_pure(self) -> bool:
        Requires(Rd(self.bitstream_invariant()))
        Requires(1 <= self.remaining_bits)
        Unfold(Rd(self.bitstream_invariant()))
        return byte_read_bit(self._buffer[self._current_byte], self._current_bit)

    @Pure
    @Opaque
    def _lemma_read_current_bit_pure(self) -> bool:
        Requires(Rd(self.bitstream_invariant()))
        Requires(1 <= self.remaining_bits)
        Ensures(self._read_current_bit_pure() == byteseq_read_bit(self.buffer(), self.current_used_bits))
        Ensures(Result())

        ghost_buf = self.buffer()
        ghost_index = self.current_used_bits
        ghost_byte_pos = ghost_index // NO_OF_BITS_IN_BYTE
        ghost_bit_pos = ghost_index % NO_OF_BITS_IN_BYTE
        ghost_byte = ghost_buf[ghost_byte_pos]

        ghost_bit = Reveal(byteseq_read_bit(ghost_buf, ghost_index))
        read_bit = Reveal(self._read_current_bit_pure())

        Unfold(Rd(self.bitstream_invariant()))
        bit_pos_eq = self._current_bit == ghost_bit_pos
        byte_eq = self._buffer[self._current_byte] == ghost_byte

        return bit_pos_eq and byte_eq and ghost_bit == read_bit 


    def read_bit(self) -> bool:
        """Read a single bit"""
        Requires(self.bitstream_invariant())
        Requires(1 <= self.remaining_bits)
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits + 1))
        Ensures(self.buffer() == Old(self.buffer()))
        Ensures(Result() == Old(byteseq_read_bit(self.buffer(), self.current_used_bits)))
        Ensures(int(Result()) == byteseq_read_bits(self.buffer(), Old(self.current_used_bits), 1))

        ghost = self._lemma_read_current_bit_pure()
        ghost = lemma_byteseq_read_bits_equal(self.buffer(), self.current_used_bits)

        res = self._read_current_bit_pure()
        self._shift_bit_index(1)
        return res

    def read_bits(self, bit_count: PInt) -> int:
        """Read up to 8 bits"""
        #@nagini Requires(self.bitstream_invariant())
        #@nagini Requires(0 <= bit_count and bit_count <= NO_OF_BITS_IN_BYTE)
        #@nagini Requires(self.validate_offset(bit_count))
        #@nagini Ensures(self.bitstream_invariant())
        #@nagini Ensures(self.current_used_bits == Old(self.current_used_bits + bit_count))
        #@nagini Ensures(self.buffer() == Old(self.buffer()))
        #@nagini Ensures(Result() == byteseq_read_bits(self.buffer(), Old(self.current_used_bits), bit_count))

        if bit_count == 0:
            return 0
        
        value = 0
        i = 0
        while i < bit_count:
            Invariant(self.bitstream_invariant())
            Invariant(0 <= i and i <= bit_count)
            Invariant(self.validate_offset(bit_count - i))
            Invariant(self.current_used_bits == Old(self.current_used_bits + i))
            Invariant(self.buffer() == Old(self.buffer()))
            Invariant(value == byteseq_read_bits(self.buffer(), Old(self.current_used_bits), i))

            next_bit = int(self.read_bit())
            value = (value << 1) + next_bit
            
            Assert(next_bit == byteseq_read_bits(self.buffer(), Old(self.current_used_bits) + i, 1))
            ghost = lemma_byteseq_read_bits_induction_lsb(self.buffer(), Old(self.current_used_bits), i + 1)
            i = i + 1

        return value

    def read_byte(self) -> int:
        """Read a complete byte"""
        #@nagini Requires(self.bitstream_invariant())
        #@nagini Requires(self.validate_offset(NO_OF_BITS_IN_BYTE))
        #@nagini Ensures(self.bitstream_invariant())
        #@nagini Ensures(self.current_used_bits == Old(self.current_used_bits + NO_OF_BITS_IN_BYTE))
        #@nagini Ensures(self.buffer() == Old(self.buffer()))
        #@nagini Ensures(Result() == byteseq_read_bits(self.buffer(), Old(self.current_used_bits), NO_OF_BITS_IN_BYTE))
        return self.read_bits(NO_OF_BITS_IN_BYTE)

    # def read_segment(self, length: int) -> int:
        # Has to match length of current segment
        # Returns value of current segment
        # Advanced segment index

    #endregion

    #region Write

    # cur bit = 3
    #
    # |x|x|x|b|?|?|?|?|
    #  0 1 2 3 4 5 6 7
    def write_bit(self, bit: bool) -> None:
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
        self._buffer[self._current_byte] = byte_set_bit(val, bit, self._current_bit)
        
        Fold(self.bitstream_invariant())
        self._shift_bit_index(1)


    def write_bits(self, value: int, bit_count: int) -> None:
        """Write multiple bits from an integer value"""
        Requires(self.bitstream_invariant())
        Requires(0 <= bit_count and bit_count <= NO_OF_BITS_IN_BYTE) 
        Requires(0 <= value and value < (1 << (bit_count)))
        Requires(self.validate_offset(bit_count))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits + bit_count))
        Ensures(self.buffer_size == Old(self.buffer_size))
        Ensures(self.buffer() == byteseq_set_bits(Old(self.buffer()), value, Old(self.current_used_bits), bit_count))
        Ensures(byteseq_equal_until(self.buffer(), Old(self.buffer()), Old(self.current_used_bits)))
        Ensures(byteseq_read_bits(self.buffer(), Old(self.current_used_bits), bit_count) == value)
        
        if bit_count == 0:
            return
        
        ghost_current_value = 0
        i: int = 0
        
        while i < bit_count:
            Invariant(self.bitstream_invariant())
            Invariant(0 <= i and i <= bit_count)
            Invariant(self.validate_offset(bit_count - i))
            Invariant(self.current_used_bits == Old(self.current_used_bits + i))
            Invariant(ghost_current_value == value >> (bit_count - i))
            Invariant(self.buffer() == byteseq_set_bits(Old(self.buffer()), ghost_current_value, Old(self.current_used_bits), i))

            bit = bool((value >> (bit_count - 1 - i)) % 2)
            ghost_current_value = (ghost_current_value << 1) + bit
            
            self.write_bit(bit)
            
            updated_seq = Reveal(byteseq_set_bits(Old(self.buffer()), ghost_current_value, Old(self.current_used_bits), i + 1))
            i = i + 1
        Assert(ghost_current_value == value)
        lemma = lemma_byteseq_set_bits(Old(self.buffer()), value, Old(self.current_used_bits), bit_count)
    
    #     # if bit_count < 0 or bit_count > 64:
    #     #     raise BitStreamError(f"Bit count {bit_count} out of range [0, 64]")

    #     # Check if value fits in bit_count bits
    #     # max_value = (1 << bit_count) - 1
    #     # if value < 0 or value > max_value:
    #     #     raise BitStreamError(f"Value {value} does not fit in {bit_count} bits")
    

    def write_byte(self, value: int) -> None:
        """Writes a complete byte"""
        Requires(self.bitstream_invariant())
        Requires(0 <= value and value < (1 << (NO_OF_BITS_IN_BYTE)))
        Requires(self.validate_offset(NO_OF_BITS_IN_BYTE))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits + NO_OF_BITS_IN_BYTE))
        Ensures(self.buffer_size == Old(self.buffer_size))
        Ensures(self.buffer() == byteseq_set_bits(Old(self.buffer()), value, Old(self.current_used_bits), NO_OF_BITS_IN_BYTE))
        Ensures(byteseq_equal_until(self.buffer(), Old(self.buffer()), Old(self.current_used_bits)))
        Ensures(byteseq_read_bits(self.buffer(), Old(self.current_used_bits), NO_OF_BITS_IN_BYTE) == value)

        self.write_bits(value, 8)
        
    def write_segment(self, value: int, length: int) -> None:
        Requires(self.bitstream_invariant())
        Requires(0 <= length and length <= NO_OF_BITS_IN_BYTE) 
        Requires(0 <= value and value < (1 << (length)))
        Requires(self.validate_offset(length))
        Requires(self.segments_predicate())
        
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits + length))
        Ensures(self.buffer_size == Old(self.buffer_size))
        Ensures(self.segments_predicate())
        Ensures(Unfolding(self.segments_predicate(), self.segments == self.segments + PSeq(Segment(length, value))))
        
        # We want to show that the new value has been appended
        # We want to guarantee that all segments are in the PByteSeq respectively the bytearray
        
        self.write_bits(value, length)
        
        Unfold(self.segments_predicate())
        self.segments = self.segments + PSeq(Segment(length, value))
        Fold(self.segments_predicate())
        
        
        
    #endregion

def client() -> None:
    b = BitStream(bytearray([0,0,0,0]))
    b.write_bits(255, 8)
    buf = b.buffer()
    b.write_bits(7, 5)
    lemma_byteseq_equal_read_bits(b.buffer(), buf, 13, 0, 8)
    buf = b.buffer()
    b.write_bits(39, 6)
    lemma_byteseq_equal_read_bits(b.buffer(), buf, 19, 0, 8)
    lemma_byteseq_equal_read_bits(b.buffer(), buf, 19, 13, 5)
    
    b.reset()
    
    assert b.read_bits(8) == 255
    assert b.read_bits(5) == 7
    assert b.read_bits(6) == 39


# client()
   

    # def write_bytes(self, data: bytes) -> None:
    #     """Write multiple bytes"""
    #     for byte_value in data:
    #         self.write_byte(byte_value)

    # def read_bytes(self, byte_count: int) -> bytearray:
    #     """Read multiple bytes"""
    #     result = bytearray()
    #     for _ in range(byte_count):
    #         result.append(self.read_byte())
    #     return result

    # def bits_remaining(self) -> int:
    #     """Get the number of bits remaining to be read"""
    #     return max(0, self._size_in_bits - self._current_bit)

    # def is_at_end(self) -> bool:
    #     """Check if we're at the end of the bitstream"""
    #     return self._current_bit >= self._size_in_bits

    # def align_to_byte(self) -> None:
    #     """Align the current position to the next byte boundary"""
    #     if self._bit_in_byte != 0:
    #         self._current_bit += (8 - self._bit_in_byte)
    #         self._bit_in_byte = 0
    #         self._current_byte += 1

    # def get_data(self) -> bytearray:
    #     """Get the complete data buffer"""
    #     return self._buffer[:self.size_in_bytes]

    # def get_data_copy(self) -> bytearray:
    #     """Get a copy of the complete data buffer"""
    #     return bytearray(self._buffer[:self.size_in_bytes])

    # def __str__(self) -> str:
    #     """String representation for debugging"""
    #     return f"BitStream(size={self._size_in_bits} bits, pos={self._current_bit}, data={self._buffer[:self.size_in_bytes].hex()})"

    # def to_hex_string(self) -> str:
    #     """Convert the bitstream data to a hex string"""
    #     return self._buffer[:self.size_in_bytes].hex()

    # def to_binary_string(self) -> str:
    #     """Convert the bitstream data to a binary string"""
    #     result: List[str] = []
    #     for byte in self._buffer[:self.size_in_bytes]:
    #         result.append(f"{byte:08b}")
    #     return "".join(result)[:self._size_in_bits]