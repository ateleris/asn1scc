"""
ASN.1 Python Runtime Library - BitStream Operations

This module provides bit-level reading and writing operations
that match the behavior of the C and Scala bitstream implementations.
"""

from nagini_contracts.contracts import *
from typing import Optional, List, Tuple
from verification import byteseq_set_bit, byte_set_bit, byteseq_eq_until
# from asn1_types import NO_OF_BITS_IN_BYTE
NO_OF_BITS_IN_BYTE = 8

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
    @staticmethod
    def _bit_index(bit_position: int, byte_position: int, buf_length: int) -> int:
        Requires(BitStream.position_invariant(bit_position, byte_position, buf_length))
        Ensures(0 <= Result() and Result() <= buf_length * NO_OF_BITS_IN_BYTE)
        Ensures(Result() == buf_length * NO_OF_BITS_IN_BYTE - BitStream._remaining_bits(bit_position, byte_position, buf_length))
        return BitStream.to_bit_index(bit_position, byte_position)
    
    @Pure
    @staticmethod
    def _validate_offset_bits(bit_position: int, byte_position: int, buf_length: int, bits: int) -> bool:
        Requires(0 <= bit_position and 0 <= byte_position and 0 <= buf_length)
        Requires(BitStream.position_invariant(bit_position, byte_position, buf_length))
        Requires(0 <= bits)
        return BitStream._remaining_bits(bit_position, byte_position, buf_length) >= bits

    @Pure
    def validate_offset(self, bits: int) -> bool:
        Requires(Rd(self.bitstream_invariant()))
        Requires(0 <= bits)
        Unfold(Rd(self.bitstream_invariant()))
        return BitStream._validate_offset_bits(self._current_bit, self._current_byte, len(self._buffer), bits)
    
    @Predicate
    def bitstream_invariant(self) -> bool:
        return (Acc(self._current_bit) and Acc(self._current_byte) and 
                Acc(self._buffer) and Acc(bytearray_pred(self._buffer)) and
                BitStream.position_invariant(self._current_bit, self._current_byte, len(self._buffer)))

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
        Fold(self.bitstream_invariant())
        
        Ensures(Acc(bytearray_pred(data), 1/20))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_bit_position == 0)
        Ensures(self.current_byte_position == 0)
        Ensures(self.buffer() == ToByteSeq(data))
    
    #region Properties

    @property
    def current_bit_position(self) -> int:
        """Get the current bit position"""
        Requires(Rd(self.bitstream_invariant()))
        Unfold(Rd(self.bitstream_invariant()))
        return self._current_bit

    @property
    def current_byte_position(self) -> int:
        """Get the current byte position"""
        Requires(Rd(self.bitstream_invariant()))
        Unfold(Rd(self.bitstream_invariant()))
        return self._current_byte

    @property
    def buffer_size(self) -> int:
        """Get the buffer size in bytes"""
        Requires(Rd(self.bitstream_invariant()))
        Unfold(Rd(self.bitstream_invariant()))
        return len(self._buffer)

    @property
    def current_used_bits(self) -> int:
        Requires(Rd(self.bitstream_invariant()))
        Ensures(Result() == Unfolding(Rd(self.bitstream_invariant()), BitStream._bit_index(self._current_bit, self._current_byte, len(self._buffer))))
        return self.current_byte_position * NO_OF_BITS_IN_BYTE + self.current_bit_position

    @property
    def current_used_bytes(self) -> int:
        Requires(Rd(self.bitstream_invariant()))
        return self.current_byte_position + (1 if self.current_bit_position > 0 else 0)

    @property
    def remaining_bits(self) -> int:
        Requires(Rd(self.bitstream_invariant()))
        Ensures(Result() == self.buffer_size * NO_OF_BITS_IN_BYTE - self.current_used_bits)
        Ensures(Result() == Unfolding(Rd(self.bitstream_invariant()), BitStream._remaining_bits(self._current_bit, self._current_byte, len(self._buffer))))
        return self.buffer_size * NO_OF_BITS_IN_BYTE - self.current_used_bits

    @Pure
    def buffer(self) -> PByteSeq:
        Requires(Rd(self.bitstream_invariant()))
        return Unfolding(Rd(self.bitstream_invariant()), ToByteSeq(self._buffer))

    #endregion    
    
    def reset(self) -> None:
        """Reset the bit position to the beginning"""
        Requires(self.bitstream_invariant())
        Ensures(self.bitstream_invariant())
        Ensures(self.current_bit_position == 0)
        Ensures(self.current_byte_position == 0)
        Ensures(self.buffer() == Old(self.buffer()))

        Unfold(self.bitstream_invariant())
        self._current_bit = 0
        self._current_byte = 0
        Fold(self.bitstream_invariant())

    def set_position(self, bit_position: int, byte_position: int) -> None:
        """Set the current bit and byte position"""
        Requires(self.bitstream_invariant())
        Requires(BitStream.position_invariant(bit_position, byte_position, self.buffer_size))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_bit_position == bit_position)
        Ensures(self.current_byte_position == byte_position)
        Ensures(self.buffer() == Old(self.buffer()))

        if not BitStream.position_invariant(bit_position, byte_position, self.buffer_size):
            raise BitStreamError(f"Position {byte_position}.{bit_position} out of range for buffer of size {self.buffer_size}")
        
        Unfold(self.bitstream_invariant())
        self._current_bit = bit_position
        self._current_byte = byte_position
        Fold(self.bitstream_invariant())

    def _shift_bit_index(self, count: int = 1) -> None:
        Requires(self.bitstream_invariant())
        Requires(0 <= count)
        Requires(self.validate_offset(count))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits + count))
        Ensures(self.remaining_bits == Old(self.remaining_bits - count))
        Ensures(self.buffer() == Old(self.buffer()))

        new_index = self.current_used_bits + count
        Unfold(self.bitstream_invariant())
        self._current_bit = new_index % NO_OF_BITS_IN_BYTE
        self._current_byte = new_index // NO_OF_BITS_IN_BYTE
        Fold(self.bitstream_invariant())
    
    #region Read

    @Pure
    def _read_bit_pure(self, bit_position: int, byte_position: int) -> bool:
        Requires(Rd(self.bitstream_invariant()))
        Requires(0 <= bit_position and 0 <= byte_position)
        Requires(BitStream.position_invariant(bit_position, byte_position, self.buffer_size))
        Requires(BitStream._validate_offset_bits(bit_position, byte_position, self.buffer_size, 1))
        Unfold(self.bitstream_invariant())
        """Read a single bit"""     
        return bool(self._buffer[byte_position] & (1 << (7 - bit_position)))

    @Pure
    def _read_current_bit_pure(self) -> bool:
        Requires(Rd(self.bitstream_invariant()))
        Requires(Unfolding(self.bitstream_invariant(),
            BitStream._validate_offset_bits(self._current_bit, self._current_byte, len(self._buffer), 1)))
        return self._read_bit_pure(self.current_bit_position, self.current_byte_position)

    def read_bit(self) -> bool:
        Requires(self.bitstream_invariant())
        Requires(self.validate_offset(1))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits) + 1)
        Ensures(self.buffer() == Old(self.buffer()))

        Ensures(Result() == Old(self._read_current_bit_pure()))
        """Read a single bit"""
        
        res = self._read_current_bit_pure()
        self._shift_bit_index(1)
        return res


    # def read_bits(self, bit_count: int) -> int:
    #     Requires(self.bitstream_invariant())
    #     Requires(self.validate_offset(bit_count))
    #     Ensures(self.bitstream_invariant())
    #     Ensures(self.current_used_bits == Old(self.current_used_bits) + bit_count)
    #     Ensures(self.buffer() == Old(self.buffer()))
    #     """Read multiple bits and return as integer"""

    #     if bit_count == 0:
    #         return 0

    #     if self.remaining_bits < bit_count:
    #         raise BitStreamError("Cannot read beyond end of bitstream")

    #     value = 0
    #     for i in range(bit_count):
    #         if self.read_bit():
    #             value |= (1 << (bit_count - 1 - i))

    #     return value

    # def read_byte(self) -> int:
    #     """Read a complete byte"""
    #     return self.read_bits(8)

    #endregion

    #region Write

    # cur bit = 3
    #
    # |x|x|x|b|?|?|?|?|
    #  0 1 2 3 4 5 6 7
    def write_bit(self, bit: bool) -> None:
        Requires(self.bitstream_invariant())
        Requires(self.validate_offset(1))
        Ensures(self.bitstream_invariant())
        Ensures(self.current_used_bits == Old(self.current_used_bits) + 1)
        Ensures(self.buffer_size == Old(self.buffer_size))
        Ensures(byteseq_eq_until(self.buffer(), Old(self.buffer()), Old(Unfolding(self.bitstream_invariant(), self._current_byte))))
        Ensures(Let(Old(Unfolding(self.bitstream_invariant(), self._current_byte)), bool, lambda byte_pos:
                Let(Old(Unfolding(self.bitstream_invariant(), self._current_bit)), bool, lambda bit_pos: 
                self.buffer()[byte_pos] == Old(byte_set_bit(self.buffer()[byte_pos], bit, bit_pos)))))
        
        # SLOWER
        # Ensures(self.buffer() == Old(Unfolding(self.bitstream_invariant(), 
        #         byteseq_set_bit(ToByteSeq(self._buffer), bit, self._current_bit, self._current_byte))))
        """Write a single bit"""

        Unfold(self.bitstream_invariant())
        val = self._buffer[self._current_byte]
        self._buffer[self._current_byte] = byte_set_bit(val, bit, self._current_bit)
        Fold(self.bitstream_invariant())
        self._shift_bit_index(1)


# def client() -> None:
#     b1 = bytearray([128,2,3])
#     bs = BitStream(b1)
    
#     assert bs.remaining_bits == 24
#     bs.set_position(1, 0)
#     assert bs.current_bit_position == 1
#     assert bs.current_byte_position == 0
#     assert bs.current_used_bits == 1
#     assert bs.buffer_size == 3
#     assert bs.remaining_bits == bs.buffer_size * NO_OF_BITS_IN_BYTE - bs.current_used_bits
#     assert bs.remaining_bits == 23
    
#     Unfold(bs.bitstream_invariant())
#     assert bs._buffer[0] == 128
    
# def client2() -> None:
#     bs = BitStream(bytearray([0,0,0]))
#     bs.write_bit(True)
#     bs.write_bit(False)
#     bs.set_position(0, 0)
#     res = bs.read_bit()
#     assert res == True
#     res = bs.read_bit()
#     assert res == False
    
# def client3() -> None:
#     bs = BitStream(bytearray([0,0,0]))
#     bs.write_bit(True)
#     bs.set_position(0, 0)
#     res = bs.read_bit()
#     assert res == True
    

# Prover does not finish
# def client4() -> None:
#     bs = BitStream(bytearray(8))
#     bs.write_bit(True)
#     bs.write_bit(False)
#     bs.write_bit(True)
#     bs.write_bit(False)    
#     bs.set_position(0, 0)
    
#     assert bs.read_bit() == True
#     assert bs.read_bit() == False
#     assert bs.read_bit() == True
#     assert bs.read_bit() == False

def client_write() -> None:
    bs = BitStream(bytearray([0]))
    bs.write_bit(True)
    bs.write_bit(False)
    bs.write_bit(True)
    bs.write_bit(False)
    
    assert bs.buffer() == PByteSeq(160)

# client()

# b2 = BitStream(bytearray([1,2,3]))

# # b1.reset()

# # assert b1.current_bit_position == 0

# Unfold(b1.bitstream_invariant())
# assert len(b1._buffer) == l
# assert b1._buffer[0] == 1

# b1.set_position(0, 3)
# b2.set_position(0, 3)
# Assert(b1.is_prefix_of(b2))

    #endregion

    # def write_bits(self, value: int, bit_count: int) -> None:
    #     """Write multiple bits from an integer value"""
    #     if bit_count < 0 or bit_count > 64:
    #         raise BitStreamError(f"Bit count {bit_count} out of range [0, 64]")

    #     if bit_count == 0:
    #         return

    #     # Check if value fits in bit_count bits
    #     max_value = (1 << bit_count) - 1
    #     if value < 0 or value > max_value:
    #         raise BitStreamError(f"Value {value} does not fit in {bit_count} bits")

    #     # Write bits from most significant to least significant
    #     for i in range(bit_count - 1, -1, -1):
    #         bit = (value >> i) & 1
    #         self.write_bit(bool(bit))

    # def write_byte(self, byte_value: int) -> None:
    #     """Write a complete byte"""
    #     if byte_value < 0 or byte_value > 255:
    #         raise BitStreamError(f"Byte value {byte_value} out of range [0, 255]")

    #     self.write_bits(byte_value, 8)

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