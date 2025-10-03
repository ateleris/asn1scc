from typing import List, Optional

from .codec import Codec, DecodeResult, ERROR_INSUFFICIENT_DATA, DECODE_OK, BitStreamError, ERROR_INVALID_VALUE, ERROR_CONSTRAINT_VIOLATION


class Decoder(Codec):

    def __init__(self, buffer: bytearray) -> None:
        super().__init__(buffer=buffer)

    def decode_integer(self,
                      min_val: int,
                      max_val: int,
                      size_in_bits: Optional[int] = None) -> DecodeResult[int]:
        """
        Decode a constrained integer value using offset decoding.

        This method implements ASN.1 PER constrained integer decoding:
        - Requires both min_val and max_val (range-based decoding)
        - Uses offset decoding: decodes unsigned value and adds min_val
        - Calculates bits needed from range size

        For unsigned integers without a range, use decode_unsigned_integer().
        For signed integers with two's complement, use dec_int_twos_complement_*().

        Args:
            min_val: Minimum allowed value (required)
            max_val: Maximum allowed value (required)
            size_in_bits: Optional hint for bits needed (must match range calculation)
        """
        try:
            # Calculate bits needed from range
            range_size = max_val - min_val + 1
            bits_needed = (range_size - 1).bit_length()

            # If size_in_bits is provided, validate it matches
            if size_in_bits is not None and size_in_bits != bits_needed:
                # Note: In practice, callers should ensure size_in_bits matches the range
                # If they don't match, use the range-calculated size (safer)
                pass

            if self._bitstream.bits_remaining() < bits_needed:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message=f"Insufficient data: need {bits_needed} bits, have {self._bitstream.bits_remaining()}"
                )

            # Decode the offset value as unsigned
            offset_value = self._bitstream.read_bits(bits_needed)

            print(f"READ VALUE {offset_value}")

            # Apply offset decoding: add min_val to get actual value
            value = offset_value + min_val

            # Validate result is within range
            if value < min_val:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Decoded value {value} below minimum {min_val}"
                )

            if value > max_val:
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

    def bit_index(self) -> int:
        """
        Get the current bit position in the bitstream.

        Matches C: BitStream.currentBit + BitStream.currentByte * 8
        Matches Scala: BitStream.bitIndex
        Used by: ACN for tracking position, calculating sizes

        Returns:
            Current bit position (0-based index)
        """
        return self._bitstream.current_bit_position()

    def read_bit(self) -> DecodeResult[bool]:
        """
        Read a single bit from the bitstream.

        Matches C: BitStream_ReadBit(pBitStrm, pBit)
        Matches Scala: BitStream.readBit(): Boolean
        Used by: ACN for boolean decoding, optional field markers

        Returns:
            DecodeResult containing boolean value (True = 1, False = 0)
        """
        try:
            if self._bitstream.bits_remaining() < 1:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message="Insufficient data to read bit"
                )

            bit_value = self._bitstream.read_bit()
            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=bit_value,
                bits_consumed=1
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

    def read_bits(self, num_bits: int) -> DecodeResult[bytes]:
        """
        Read arbitrary bits from the bitstream into a buffer.

        Matches Scala: BitStream.readBits(nBits: Long): Array[UByte]
        Matches C: BitStream_ReadBits(pBitStrm, BuffToWrite, nbits)
        Used by: ACN for bit patterns and partial byte reads

        Args:
            num_bits: Number of bits to read

        Returns:
            DecodeResult containing bytes with the read bits
            (MSB-first, last byte may be partial)
        """
        try:
            if num_bits < 0:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"num_bits must be non-negative, got {num_bits}"
                )

            if num_bits == 0:
                return DecodeResult(
                    success=True,
                    error_code=DECODE_OK,
                    decoded_value=b'',
                    bits_consumed=0
                )

            if self._bitstream.bits_remaining() < num_bits:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message=f"Insufficient data: need {num_bits} bits, have {self._bitstream.bits_remaining()}"
                )

            # Calculate required buffer size
            num_bytes = (num_bits + 7) // 8
            result = bytearray(num_bytes)
            bits_consumed = 0

            # Read complete bytes
            complete_bytes = num_bits // 8
            for i in range(complete_bytes):
                result[i] = self._bitstream.read_bits(8)
                bits_consumed += 8

            # Read remaining bits into partial byte
            remaining_bits = num_bits % 8
            if remaining_bits > 0:
                # Read the remaining bits
                partial_byte = self._bitstream.read_bits(remaining_bits)
                # Shift to align to MSB (high-order bits)
                result[complete_bytes] = partial_byte << (8 - remaining_bits)
                bits_consumed += remaining_bits

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

    def decode_octet_string_no_length(self, num_bytes: int) -> DecodeResult[bytes]:
        """
        Decode octet string without length prefix.

        Matches C: BitStream_DecodeOctetString_no_length(pBitStrm, arr, nCount)
        Matches Scala: BitStream.readByteArray without length decoding
        Used by: ACN for fixed-size or externally-determined length octet strings

        Args:
            num_bytes: Number of bytes to decode

        Returns:
            DecodeResult containing decoded bytes
        """
        try:
            if num_bytes < 0:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"num_bytes must be non-negative, got {num_bytes}"
                )

            if num_bytes == 0:
                return DecodeResult(
                    success=True,
                    error_code=DECODE_OK,
                    decoded_value=b'',
                    bits_consumed=0
                )

            if self._bitstream.bits_remaining() < num_bytes * 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INSUFFICIENT_DATA,
                    error_message=f"Insufficient data: need {num_bytes * 8} bits, have {self._bitstream.bits_remaining()}"
                )

            # Check if we're byte-aligned
            if self._bitstream.current_bit == 0:
                # Optimized path: byte-aligned, can read directly
                result = bytearray()
                for _ in range(num_bytes):
                    byte_val = self._bitstream.read_bits(8)
                    result.append(byte_val)

                return DecodeResult(
                    success=True,
                    error_code=DECODE_OK,
                    decoded_value=bytes(result),
                    bits_consumed=num_bytes * 8
                )
            else:
                # Not byte-aligned, use read_byte_array which handles bit offset
                return self.read_byte_array(num_bytes)

        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_octet_string_no_length_vec(self, num_bytes: int) -> DecodeResult[list]:
        """
        Decode octet string without length prefix, returning as list.

        Matches Scala: BitStream.readByteArrayVec without length decoding
        Used by: ACN for fixed-size or externally-determined length octet strings

        Args:
            num_bytes: Number of bytes to decode

        Returns:
            DecodeResult containing list of byte values
        """
        result = self.decode_octet_string_no_length(num_bytes)
        if result.success:
            # Convert bytes to list
            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=list(result.decoded_value),
                bits_consumed=result.bits_consumed
            )
        else:
            return DecodeResult(
                success=False,
                error_code=result.error_code,
                error_message=result.error_message
            )

    def check_bit_pattern_present(self, pattern: bytes, num_bits: int) -> DecodeResult[int]:
        """
        Check if a bit pattern is present at the current position.

        Matches C: BitStream_checkBitPatternPresent(pBitStrm, pattern, num_bits)
        Used by: ACN for null-terminated strings and bit patterns

        Args:
            pattern: Bit pattern to check for
            num_bits: Number of bits in the pattern

        Returns:
            DecodeResult containing:
                0 - Insufficient data (cannot check pattern)
                1 - Pattern not present (can continue reading)
                2 - Pattern present (found terminator)

        Note: This method does not advance the bitstream position
        """
        try:
            # Check if we have enough bits to read the pattern
            if self._bitstream.bits_remaining() < num_bits:
                return DecodeResult(
                    success=True,
                    error_code=DECODE_OK,
                    decoded_value=0,  # Insufficient data
                    bits_consumed=0
                )

            # Save current position
            saved_byte = self._bitstream.current_byte
            saved_bit = self._bitstream.current_bit

            # Calculate required bytes for pattern
            num_pattern_bytes = (num_bits + 7) // 8
            complete_bytes = num_bits // 8
            remaining_bits = num_bits % 8

            # Read and compare pattern
            pattern_matches = True
            for i in range(complete_bytes):
                byte_val = self._bitstream.read_bits(8)
                if byte_val != pattern[i]:
                    pattern_matches = False
                    break

            # Check remaining bits if pattern still matches
            if pattern_matches and remaining_bits > 0:
                partial_byte = self._bitstream.read_bits(remaining_bits)
                # Compare high-order bits
                expected = pattern[complete_bytes] >> (8 - remaining_bits)
                if partial_byte != expected:
                    pattern_matches = False

            # Restore position (this is a check, not a consume)
            self._bitstream.current_byte = saved_byte
            self._bitstream.current_bit = saved_bit

            # Return result
            result_value = 2 if pattern_matches else 1
            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=result_value,
                bits_consumed=0
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

    def decode_semi_constrained_whole_number(self, min_val: int) -> DecodeResult[int]:
        """
        Decode semi-constrained whole number (signed, only lower bound).

        Matches Scala: Codec.decodeSemiConstrainedWholeNumber(min: Long)
        Used by: UPER, PER for integers with only minimum constraint

        Decodes as: length byte + value bytes (MSB first)
        - Reads length as single byte
        - Reads value in big-endian byte order
        - Adds min_val offset

        Args:
            min_val: Minimum allowed value
        """
        try:
            # Read length byte
            result = self.read_byte()
            if not result.success:
                return result
            num_bytes = result.decoded_value

            if num_bytes == 0 or num_bytes > 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Invalid length: {num_bytes} (must be 1-8)"
                )

            # Read value bytes
            result = self.read_byte_array(num_bytes)
            if not result.success:
                return result
            data_bytes = result.decoded_value

            # Convert from big-endian
            enc_value = 0
            for byte_val in data_bytes:
                enc_value = (enc_value << 8) | byte_val

            # Add offset
            value = enc_value + min_val

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=8 + num_bytes * 8
            )

        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_semi_constrained_pos_whole_number(self, min_val: int) -> DecodeResult[int]:
        """
        Decode semi-constrained positive whole number (unsigned, only lower bound).

        Matches Scala: Codec.decodeSemiConstrainedPosWholeNumber(min: ULong)
        Used by: UPER, PER for non-negative integers with only minimum constraint

        Args:
            min_val: Minimum allowed value (non-negative)
        """
        if min_val < 0:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message="Minimum value must be non-negative for positive whole numbers"
            )
        return self.decode_semi_constrained_whole_number(min_val)

    def decode_unconstrained_whole_number(self) -> DecodeResult[int]:
        """
        Decode unconstrained whole number (signed, no constraints).

        Matches Scala: Codec.decodeUnconstrainedWholeNumber()
        Used by: UPER, PER for integers without size constraints

        Decodes as: length byte + value bytes (MSB first, two's complement for negative)
        - Reads length as single byte
        - Reads value in big-endian byte order
        - Applies sign extension for negative numbers

        Returns:
            DecodeResult with decoded signed integer value
        """
        try:
            # Read length byte
            result = self.read_byte()
            if not result.success:
                return result
            num_bytes = result.decoded_value

            if num_bytes == 0 or num_bytes > 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Invalid length: {num_bytes} (must be 1-8)"
                )

            # Read value bytes
            result = self.read_byte_array(num_bytes)
            if not result.success:
                return result
            data_bytes = result.decoded_value

            # Convert from big-endian
            unsigned_value = 0
            for byte_val in data_bytes:
                unsigned_value = (unsigned_value << 8) | byte_val

            # Apply sign extension for two's complement
            num_bits = num_bytes * 8
            sign_bit = 1 << (num_bits - 1)
            if unsigned_value & sign_bit:
                # Negative number - sign extend
                value = unsigned_value - (1 << num_bits)
            else:
                # Positive number
                value = unsigned_value

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=8 + num_bytes * 8
            )

        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )
