"""
ASN.1 Python Runtime Library - BitStream Operations

This module provides bit-level reading and writing operations
that match the behavior of the C and Scala bitstream implementations.
"""

from nagini_contracts.contracts import *
from typing import Optional, List
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

    @Pure
    @staticmethod
    def position_invariant(bit_position: int, byte_position: int, buff_length: int) -> bool:
        return (bit_position >= 0 and bit_position < NO_OF_BITS_IN_BYTE and
                byte_position >= 0 and ((byte_position < buff_length) or (bit_position == 0 and byte_position == buff_length)))

    @Predicate
    def bitstream_invariant(self) -> bool:
        return (Acc(self._buffer) and Acc(self._current_bit) and Acc(self._current_byte) and
                bytearray_pred(self._buffer) and
                BitStream.position_invariant(self._current_bit, self._current_byte, len(self._buffer)))

    def __init__(self, data: Optional[bytearray] = None, size_in_bytes: Optional[int] = None):
        Requires(Implies(data is not None, bytearray_pred(data)))
        Requires(Implies(size_in_bytes is not None, 0 <= size_in_bytes))
        Requires(Implies((data is not None) and (size_in_bytes is not None), size_in_bytes >= len(data)))
        Ensures(self.bitstream_invariant())
        """
        Initialize a BitStream.

        Args:
            data: Initial data buffer (optional)
            size_in_bytes: Size of the buffer in bytes (optional)
        """
        if data is None:
            self._buffer = bytearray()
        else:
            self._buffer = bytearray(data)

        self._current_bit = 0  # Current bit within byte (0-7)
        self._current_byte = 0  # Current byte position (0-based)
        Fold(self.bitstream_invariant())
        Unfold(self.bitstream_invariant())
        Fold(self.bitstream_invariant())

    @property
    def current_bit_position(self) -> int:
        """Get the current bit position"""
        Requires(self.bitstream_invariant())
        Ensures(0 <= Result() and Result() < NO_OF_BITS_IN_BYTE)
        # Unfold(self.bitstream_invariant())
        # return self._current_bit
        return Unfolding(self.bitstream_invariant(), self._current_bit)

    @property
    def current_byte_position(self) -> int:
        """Get the current bit position"""
        Requires(self.bitstream_invariant())
        Ensures(Unfolding(self.bitstream_invariant(), 0 <= Result() and ((Result() < len(self._buffer)) or (self._current_bit == 0 and Result() == len(self._buffer)))))
        # Unfold(self.bitstream_invariant())
        # return self._current_byte
        return Unfolding(self.bitstream_invariant(), self._current_byte)
    
    @property
    def buffer_size(self) -> int:
        """Get the buffer size in bytes"""
        Requires(self.bitstream_invariant())
        return Unfolding(self.bitstream_invariant(), len(self._buffer))

    @property
    def buffer(self) -> bytearray:
        """Get the internal buffer"""
        Requires(self.bitstream_invariant())
        return Unfolding(self.bitstream_invariant(), self._buffer)
    
    @property
    def current_used_bytes(self) -> int:
        """ Get the count of bytes that got already fully or partially written """
        Requires(self.bitstream_invariant())
        ret = self.current_byte_position
        if self.current_bit_position > 0:
            ret += 1
        return ret
    
    def reset(self) -> None:
        """Reset the bit position to the beginning"""
        Requires(self.bitstream_invariant())
        Ensures(self.bitstream_invariant())
             
        Unfold(self.bitstream_invariant())
        self._current_bit = 0
        self._current_byte = 0
        Fold(self.bitstream_invariant())

    def set_position(self, byte_position: int, bit_position: int) -> None:
        """Set the current bit and byte position"""
        Requires(self.bitstream_invariant())
        Requires(BitStream.position_invariant(bit_position, byte_position, self.buffer_size))
        Ensures(self.bitstream_invariant())
        
        if not BitStream.position_invariant(bit_position, byte_position, self.buffer_size):
            raise BitStreamError(f"Position {byte_position}.{bit_position} out of range for buffer of size {self.buffer_size}")
        
        Unfold(self.bitstream_invariant())
        self._current_bit = bit_position
        self._current_byte = byte_position
        
        Fold(self.bitstream_invariant())

    # def _ensure_capacity(self, required_bits: int) -> None:
    #     """Ensure the buffer has enough capacity for the required bits"""
    #     required_size = (required_bits + 7) // 8
    #     if len(self._buffer) < required_size:
    #         self._buffer.extend(bytearray(required_size - len(self._buffer)))

    #     if self._size_in_bits < required_bits:
    #         self._size_in_bits = required_bits

    # def write_bit(self, bit: bool) -> None:
    #     """Write a single bit"""
    #     if self._current_bit >= self._size_in_bits:
    #         self._ensure_capacity(self._current_bit + 1)

    #     if self._current_byte >= len(self._buffer):
    #         self._buffer.extend(bytearray(self._current_byte - len(self._buffer) + 1))

    #     if bit:
    #         self._buffer[self._current_byte] |= (1 << (7 - self._bit_in_byte))
    #     else:
    #         self._buffer[self._current_byte] &= ~(1 << (7 - self._bit_in_byte))

    #     self._current_bit += 1
    #     self._bit_in_byte += 1

    #     if self._bit_in_byte >= 8:
    #         self._bit_in_byte = 0
    #         self._current_byte += 1

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

    # def read_bit(self) -> bool:
    #     """Read a single bit"""
    #     if self._current_bit >= self._size_in_bits:
    #         raise BitStreamError("Cannot read beyond end of bitstream")

    #     if self._current_byte >= len(self._buffer):
    #         raise BitStreamError("Cannot read beyond buffer size")

    #     bit = bool(self._buffer[self._current_byte] & (1 << (7 - self._bit_in_byte)))

    #     self._current_bit += 1
    #     self._bit_in_byte += 1

    #     if self._bit_in_byte >= 8:
    #         self._bit_in_byte = 0
    #         self._current_byte += 1

    #     return bit

    # def read_bits(self, bit_count: int) -> int:
    #     """Read multiple bits and return as integer"""
    #     if bit_count < 0 or bit_count > 64:
    #         raise BitStreamError(f"Bit count {bit_count} out of range [0, 64]")

    #     if bit_count == 0:
    #         return 0

    #     if self._current_bit + bit_count > self._size_in_bits:
    #         raise BitStreamError("Cannot read beyond end of bitstream")

    #     value = 0
    #     for i in range(bit_count):
    #         if self.read_bit():
    #             value |= (1 << (bit_count - 1 - i))

    #     return value

    # def read_byte(self) -> int:
    #     """Read a complete byte"""
    #     return self.read_bits(8)

    # def read_bytes(self, byte_count: int) -> bytearray:
    #     """Read multiple bytes"""
    #     result = bytearray()
    #     for _ in range(byte_count):
    #         result.append(self.read_byte())
    #     return result

    # def peek_bit(self) -> bool:
    #     """Peek at the next bit without advancing position"""
    #     if self._current_bit >= self._size_in_bits:
    #         raise BitStreamError("Cannot peek beyond end of bitstream")

    #     if self._current_byte >= len(self._buffer):
    #         raise BitStreamError("Cannot peek beyond buffer size")

    #     return bool(self._buffer[self._current_byte] & (1 << (7 - self._bit_in_byte)))

    # def peek_bits(self, bit_count: int) -> int:
    #     """Peek at multiple bits without advancing position"""
    #     current_bit = self._current_bit
    #     current_byte = self._current_byte
    #     bit_in_byte = self._bit_in_byte

    #     try:
    #         value = self.read_bits(bit_count)
    #         return value
    #     finally:
    #         # Restore position
    #         self._current_bit = current_bit
    #         self._current_byte = current_byte
    #         self._bit_in_byte = bit_in_byte

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