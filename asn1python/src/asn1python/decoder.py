from typing import List, Optional

from .codec import Codec, DecodeResult, ERROR_INSUFFICIENT_DATA, DECODE_OK, BitStreamError, ERROR_INVALID_VALUE, ERROR_CONSTRAINT_VIOLATION


class Decoder(Codec):

    def __init__(self, buffer: bytearray) -> None:
        super().__init__(buffer=buffer)

    def decode_boolean(self) -> DecodeResult[bool]:
        """Decode a boolean value"""
        try:
            if self._bitstream.bits_remaining() < 1:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message="Insufficient data to decode boolean"
                )

            value = self._bitstream.read_bit()
            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=1
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_integer(self,
                      min_val: Optional[int] = None,
                      max_val: Optional[int] = None,
                      size_in_bits: Optional[int] = None) -> DecodeResult[int]:
        """
        Decode an integer value with optional constraints.

        Args:
            min_val: Minimum allowed value (optional)
            max_val: Maximum allowed value (optional)
            size_in_bits: Fixed size in bits (optional)
        """
        try:
            # Determine decoding size
            if size_in_bits is not None:
                bits_needed = size_in_bits
            elif min_val is not None and max_val is not None:
                range_size = max_val - min_val + 1
                bits_needed = (range_size - 1).bit_length()
            else:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message="Cannot determine integer size without constraints"
                )

            if self._bitstream.bits_remaining() < bits_needed:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message=f"Insufficient data: need {bits_needed} bits, have {self._bitstream.bits_remaining()}"
                )

            # Decode the value
            value = self._bitstream.read_bits(bits_needed)

            # Apply offset decoding if range is specified
            if min_val is not None and max_val is not None:
                value = value + min_val

            # Validate result
            if min_val is not None and value < min_val:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Decoded value {value} below minimum {min_val}"
                )

            if max_val is not None and value > max_val:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Decoded value {value} above maximum {max_val}"
                )

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=bits_needed
            )

        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_enumerated(self, enum_values: List[int]) -> DecodeResult:
        """Decode an enumerated value"""
        try:
            bits_needed = (len(enum_values) - 1).bit_length()

            if self._bitstream.bits_remaining() < bits_needed:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message=f"Insufficient data for enumerated value"
                )

            index = self._bitstream.read_bits(bits_needed)

            if index >= len(enum_values):
                return DecodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Enumerated index {index} out of range"
                )

            value = enum_values[index]

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=bits_needed
            )

        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_null(self) -> DecodeResult[None]:
        """Decode a NULL value (typically no bits)"""
        return DecodeResult(
            success=True,
            error_code=DECODE_OK,
            decoded_value=None,
            bits_consumed=0
        )

    def decode_bit_string(self,
                         min_length: int,
                         max_length: int) -> DecodeResult[str]:
        """Decode a bit string value"""
        try:
            bits_consumed = 0

            # Decode length if not fixed
            if min_length == max_length:
                length = min_length
            else:
                length_bits = (max_length - 1).bit_length() if max_length else 16
                if self._bitstream.bits_remaining() < length_bits:
                    return DecodeResult(
                        success=False,
                        error_code=ERROR_INSUFFICIENT_DATA,
                        error_message="Insufficient data for bit string length"
                    )
                length = self._bitstream.read_bits(length_bits)
                bits_consumed += length_bits

            # Validate length constraints
            if min_length is not None and length < min_length:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Bit string length {length} below minimum {min_length}"
                )

            if max_length is not None and length > max_length:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Bit string length {length} above maximum {max_length}"
                )

            # Decode bit string data
            if self._bitstream.bits_remaining() < length:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message=f"Insufficient data for bit string: need {length} bits"
                )

            bit_string = ""
            for _ in range(length):
                bit = self._bitstream.read_bit()
                bit_string += '1' if bit else '0'
                bits_consumed += 1

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=bit_string,
                bits_consumed=bits_consumed
            )

        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # BASE BITSTREAM PRIMITIVES (matching Scala BitStream structure)
    # ============================================================================

    def read_byte(self) -> DecodeResult[int]:
        """
        Read a single byte from the bitstream.

        Matches Scala: BitStream.readByte(): UByte
        Used by: ACN, UPER, PER codecs

        Returns:
            DecodeResult containing byte value (0-255)
        """
        try:
            if self._bitstream.bits_remaining() < 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message="Insufficient data to read byte"
                )

            value = self._bitstream.read_bits(8)
            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=8
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def read_byte_array(self, num_bytes: int) -> DecodeResult[bytes]:
        """
        Read multiple bytes from the bitstream.

        Matches Scala: BitStream.readByteArray(nBytes: Int): Array[UByte]
        Used by: ACN, UPER for octet strings

        Args:
            num_bytes: Number of bytes to read

        Returns:
            DecodeResult containing bytes
        """
        try:
            if self._bitstream.bits_remaining() < num_bytes * 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message=f"Insufficient data: need {num_bytes * 8} bits, have {self._bitstream.bits_remaining()}"
                )

            result = bytearray()
            bits_consumed = 0
            for _ in range(num_bytes):
                byte_val = self._bitstream.read_bits(8)
                result.append(byte_val)
                bits_consumed += 8

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=bytes(result),
                bits_consumed=bits_consumed
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_unsigned_integer(self, num_bits: int) -> DecodeResult[int]:
        """
        Decode unsigned integer with specified number of bits.

        Matches Scala: Codec.decodeUnsignedInteger(nBits: Int): ULong
        Used by: ACN, UPER, PER for constrained integers

        Args:
            num_bits: Number of bits to decode

        Returns:
            DecodeResult containing unsigned integer value
        """
        try:
            if self._bitstream.bits_remaining() < num_bits:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message=f"Insufficient data: need {num_bits} bits, have {self._bitstream.bits_remaining()}"
                )

            value = self._bitstream.read_bits(num_bits)
            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=num_bits
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_constrained_pos_whole_number(self, min_val: int, max_val: int) -> DecodeResult[int]:
        """
        Decode constrained positive whole number.

        Matches Scala: Codec.decodeConstrainedPosWholeNumber(min: ULong, max: ULong): ULong
        Used by: UPER, PER for constrained non-negative integers

        Args:
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            DecodeResult containing decoded value
        """
        return self.decode_integer(min_val=min_val, max_val=max_val)

    def decode_constrained_whole_number(self, min_val: int, max_val: int) -> DecodeResult[int]:
        """
        Decode constrained whole number (signed).

        Matches Scala: Codec.decodeConstrainedWholeNumber(min: Long, max: Long): Long
        Used by: UPER, PER for constrained signed integers

        Args:
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            DecodeResult containing decoded value
        """
        return self.decode_integer(min_val=min_val, max_val=max_val)
