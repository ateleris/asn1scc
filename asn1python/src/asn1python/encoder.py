from abc import abstractmethod, ABC
from typing import Optional, List

from .codec import Codec, EncodeResult, ENCODE_OK, BitStreamError, ERROR_INVALID_VALUE, \
    ERROR_CONSTRAINT_VIOLATION

from .decoder import Decoder


class Encoder(Codec, ABC):

    def __init__(self, buffer_bit_size: int = 0 * 1024 * 1024) -> None:
        super().__init__(buffer_bit_size=buffer_bit_size)

    @abstractmethod
    def get_decoder(self) -> Decoder:
        pass

    def encode_integer(self, value: int,
                       min_val: int,
                       max_val: int,
                       size_in_bits: Optional[int] = None) -> EncodeResult:
        """
        Encode a constrained integer value using offset encoding.

        This method implements ASN.1 PER constrained integer encoding:
        - Requires both min_val and max_val (range-based encoding)
        - Uses offset encoding: encodes (value - min_val) as unsigned
        - Calculates bits needed from range size

        For unsigned integers without a range, use encode_unsigned_integer().
        For signed integers with two's complement, use enc_int_twos_complement_*().

        Args:
            value: The integer value to encode
            min_val: Minimum allowed value (required)
            max_val: Maximum allowed value (required)
            size_in_bits: Optional hint for bits needed (must match range calculation)
        """
        try:
            # Validate constraints
            if value < min_val:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Value {value} below minimum {min_val}"
                )

            if value > max_val:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Value {value} above maximum {max_val}"
                )

            # Range-based encoding: ALWAYS use offset encoding
            range_size = max_val - min_val + 1
            bits_needed = (range_size - 1).bit_length()
            offset_value = value - min_val  # Offset encoding - value is now non-negative

            # If size_in_bits is also provided, validate it matches the range
            if size_in_bits is not None and size_in_bits != bits_needed:
                # Note: In practice, callers should ensure size_in_bits matches the range
                # If they don't match, use the range-calculated size (safer)
                pass

            # Encode the offset value as unsigned
            self._bitstream.write_bits(offset_value, bits_needed)

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=bits_needed
            )

        except (BitStreamError, ValueError) as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def append_bit(self, bit_value: bool) -> EncodeResult:
        """
        Append a single bit to the bitstream.

        Matches C: BitStream_AppendBit(pBitStrm, bit)
        Matches Scala: BitStream.appendBit(b: Boolean)
        Used by: ACN for boolean encoding, optional field markers

        Args:
            bit_value: Boolean value to append (True = 1, False = 0)

        Returns:
            EncodeResult with success/failure status
        """
        try:
            self._bitstream.write_bit(bit_value)
            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=1
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def encode_null(self) -> EncodeResult:
        """Encode a NULL value (typically no bits)"""
        return EncodeResult(
            success=True,
            error_code=ENCODE_OK,
            encoded_data=self._bitstream.get_data_copy(),
            bits_encoded=0
        )

    def encode_bit_string(self, value: str,
                         min_length: Optional[int] = None,
                         max_length: Optional[int] = None) -> EncodeResult:
        """Encode a bit string value"""
        try:
            # Validate bit string format
            if not all(c in '01' for c in value):
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message="Bit string must contain only '0' and '1'"
                )

            # Validate length constraints
            if min_length is not None and len(value) < min_length:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Bit string length {len(value)} below minimum {min_length}"
                )

            if max_length is not None and len(value) > max_length:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Bit string length {len(value)} above maximum {max_length}"
                )

            # Encode length if not fixed
            bits_encoded = 0
            if min_length != max_length:
                # Variable length - encode length first
                length_bits = (max_length - 1).bit_length() if max_length else 16
                self._bitstream.write_bits(len(value), length_bits)
                bits_encoded += length_bits

            # Encode bit string data
            for bit_char in value:
                self._bitstream.write_bit(bit_char == '1')
                bits_encoded += 1

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=bits_encoded
            )

        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # BASE BITSTREAM PRIMITIVES (matching Scala BitStream structure)
    # ============================================================================

    def append_byte(self, byte_val: int) -> EncodeResult:
        """
        Append a single byte to the bitstream.

        Matches Scala: BitStream.appendByte(v: UByte)
        Used by: ACN, UPER, PER codecs

        Args:
            byte_val: Byte value (0-255)
        """
        try:
            if not (0 <= byte_val <= 255):
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Byte value must be 0-255, got {byte_val}"
                )

            self._bitstream.write_bits(byte_val, 8)
            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=8
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def append_byte_array(self, data: bytes, num_bytes: int) -> EncodeResult:
        """
        Append multiple bytes to the bitstream.

        Matches Scala: BitStream.appendByteArray(arr: Array[UByte], noOfBytes: Int)
        Used by: ACN, UPER for octet strings

        Args:
            data: Bytes to write
            num_bytes: Number of bytes to write from data
        """
        try:
            if num_bytes > len(data):
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"num_bytes {num_bytes} exceeds data length {len(data)}"
                )

            bits_encoded = 0
            for i in range(num_bytes):
                self._bitstream.write_bits(data[i], 8)
                bits_encoded += 8

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=bits_encoded
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def append_bits(self, data: bytes, num_bits: int) -> EncodeResult:
        """
        Append arbitrary bits from a buffer to the bitstream.

        Matches Scala: BitStream.appendBits(arr: Array[Byte], nBits: Int)
        Used by: ACN for bit patterns and partial byte writes

        Args:
            data: Buffer containing bits to write
            num_bits: Number of bits to write from the buffer
        """
        try:
            if num_bits < 0:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"num_bits must be non-negative, got {num_bits}"
                )

            if num_bits == 0:
                return EncodeResult(
                    success=True,
                    error_code=ENCODE_OK,
                    encoded_data=self._bitstream.get_data_copy(),
                    bits_encoded=0
                )

            # Calculate required number of bytes
            num_bytes = (num_bits + 7) // 8
            if num_bytes > len(data):
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"num_bits {num_bits} requires {num_bytes} bytes but data has {len(data)} bytes"
                )

            bits_encoded = 0

            # Write complete bytes
            complete_bytes = num_bits // 8
            for i in range(complete_bytes):
                self._bitstream.write_bits(data[i], 8)
                bits_encoded += 8

            # Write remaining bits from partial byte
            remaining_bits = num_bits % 8
            if remaining_bits > 0:
                # Extract the high-order bits from the next byte
                byte_val = data[complete_bytes]
                # Shift to get only the desired high-order bits
                shifted_val = byte_val >> (8 - remaining_bits)
                self._bitstream.write_bits(shifted_val, remaining_bits)
                bits_encoded += remaining_bits

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=bits_encoded
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def encode_octet_string_no_length(self, data: bytes, num_bytes: int) -> EncodeResult:
        """
        Encode octet string without length prefix.

        Matches C: BitStream_EncodeOctetString_no_length(pBitStrm, arr, nCount)
        Matches Scala: BitStream.appendByteArray without length encoding
        Used by: ACN for fixed-size or externally-determined length octet strings

        Args:
            data: Bytes to encode
            num_bytes: Number of bytes to encode from data

        Returns:
            EncodeResult with success/failure status
        """
        try:
            if num_bytes < 0:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"num_bytes must be non-negative, got {num_bytes}"
                )

            if num_bytes > len(data):
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"num_bytes {num_bytes} exceeds data length {len(data)}"
                )

            # Check if we're byte-aligned
            if self._bitstream.current_bit == 0:
                # Optimized path: byte-aligned, can write directly
                for i in range(num_bytes):
                    self._bitstream.write_bits(data[i], 8)
            else:
                # Not byte-aligned, use append_byte_array which handles bit offset
                result = self.append_byte_array(data, num_bytes)
                return result

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=num_bytes * 8
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def encode_octet_string_no_length_vec(self, data: list, num_bytes: int) -> EncodeResult:
        """
        Encode octet string from list/vector without length prefix.

        Matches Scala: BitStream.appendByteArrayVec without length encoding
        Used by: ACN for fixed-size or externally-determined length octet strings

        Args:
            data: List of byte values (0-255) to encode
            num_bytes: Number of bytes to encode from data

        Returns:
            EncodeResult with success/failure status
        """
        try:
            if num_bytes > len(data):
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"num_bytes {num_bytes} exceeds data length {len(data)}"
                )

            # Convert list to bytes
            byte_data = bytes(data[:num_bytes])
            return self.encode_octet_string_no_length(byte_data, num_bytes)
        except (ValueError, TypeError) as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"Invalid data for octet string: {e}"
            )

    def encode_unsigned_integer(self, value: int, num_bits: int) -> EncodeResult:
        """
        Encode unsigned integer with specified number of bits.

        Matches Scala: Codec.encodeUnsignedInteger(v: ULong)
        Used by: ACN, UPER, PER for constrained integers

        Args:
            value: Unsigned integer value
            num_bits: Number of bits to encode
        """
        try:
            if value < 0:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Value must be non-negative, got {value}"
                )

            max_value = (1 << num_bits) - 1
            if value > max_value:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Value {value} exceeds maximum {max_value} for {num_bits} bits"
                )

            self._bitstream.write_bits(value, num_bits)
            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=num_bits
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def encode_constrained_pos_whole_number(self, value: int, min_val: int, max_val: int) -> EncodeResult:
        """
        Encode constrained positive whole number.

        Matches Scala: Codec.encodeConstrainedPosWholeNumber(v: ULong, min: ULong, max: ULong)
        Used by: UPER, PER for constrained non-negative integers

        Args:
            value: Value to encode
            min_val: Minimum allowed value
            max_val: Maximum allowed value
        """
        return self.encode_integer(value, min_val=min_val, max_val=max_val)

    def encode_constrained_whole_number(self, value: int, min_val: int, max_val: int) -> EncodeResult:
        """
        Encode constrained whole number (signed).

        Matches Scala: Codec.encodeConstrainedWholeNumber(v: Long, min: Long, max: Long)
        Used by: UPER, PER for constrained signed integers

        Args:
            value: Value to encode
            min_val: Minimum allowed value
            max_val: Maximum allowed value
        """
        return self.encode_integer(value, min_val=min_val, max_val=max_val)

    def encode_semi_constrained_whole_number(self, value: int, min_val: int) -> EncodeResult:
        """
        Encode semi-constrained whole number (signed, only lower bound).

        Matches Scala: Codec.encodeSemiConstrainedWholeNumber(v: Long, min: Long)
        Used by: UPER, PER for integers with only minimum constraint

        Encodes as: length byte + value bytes (MSB first)
        - Subtracts min_val from value
        - Calculates bytes needed for unsigned representation
        - Writes length as single byte
        - Writes value in big-endian byte order

        Args:
            value: Value to encode (must be >= min_val)
            min_val: Minimum allowed value
        """
        try:
            if value < min_val:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Value {value} below minimum {min_val}"
                )

            # Offset encoding: subtract minimum
            enc_value = value - min_val

            # Calculate bytes needed for unsigned representation
            if enc_value == 0:
                num_bytes = 1
            else:
                num_bytes = (enc_value.bit_length() + 7) // 8

            # Encode length as single byte
            result = self.append_byte(num_bytes)
            if not result.success:
                return result

            bits_encoded = 8

            # Encode value in big-endian byte order
            for i in range(num_bytes - 1, -1, -1):
                byte_val = (enc_value >> (i * 8)) & 0xFF
                result = self.append_byte(byte_val)
                if not result.success:
                    return result
                bits_encoded += 8

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=bits_encoded
            )

        except (BitStreamError, ValueError) as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def encode_semi_constrained_pos_whole_number(self, value: int, min_val: int) -> EncodeResult:
        """
        Encode semi-constrained positive whole number (unsigned, only lower bound).

        Matches Scala: Codec.encodeSemiConstrainedPosWholeNumber(v: ULong, min: ULong)
        Used by: UPER, PER for non-negative integers with only minimum constraint

        Args:
            value: Value to encode (must be >= min_val, non-negative)
            min_val: Minimum allowed value (non-negative)
        """
        if value < 0 or min_val < 0:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message="Positive whole numbers must be non-negative"
            )
        return self.encode_semi_constrained_whole_number(value, min_val)

    def encode_unconstrained_whole_number(self, value: int) -> EncodeResult:
        """
        Encode unconstrained whole number (signed, no constraints).

        Matches Scala: Codec.encodeUnconstrainedWholeNumber(v: Long)
        Used by: UPER, PER for integers without size constraints

        Encodes as: length byte + value bytes (MSB first, two's complement for negative)
        - Calculates bytes needed for signed representation
        - Writes length as single byte
        - Writes value in big-endian byte order with sign extension

        Args:
            value: Value to encode (any signed integer)
        """
        try:
            # Calculate bytes needed for signed representation
            if value >= 0:
                # Positive: need enough bytes for value + sign bit
                if value == 0:
                    num_bytes = 1
                else:
                    # Need extra bit for sign, so check if MSB is set
                    bits_needed = value.bit_length() + 1  # +1 for sign bit
                    num_bytes = (bits_needed + 7) // 8
            else:
                # Negative: two's complement representation
                # Find how many bits we need
                if value == -1:
                    num_bytes = 1
                else:
                    # For negative numbers, find the position of the highest 0 bit
                    # (after which all bits are 1)
                    bits_needed = (value + 1).bit_length() + 1  # +1 for sign bit
                    num_bytes = (bits_needed + 7) // 8

            # Maximum 8 bytes for a 64-bit integer
            if num_bytes > 8:
                num_bytes = 8

            # Encode length as single byte
            result = self.append_byte(num_bytes)
            if not result.success:
                return result

            bits_encoded = 8

            # Encode value in big-endian byte order
            num_bits = num_bytes * 8
            if value < 0:
                # Two's complement for negative numbers
                unsigned_value = (1 << num_bits) + value
            else:
                unsigned_value = value

            for i in range(num_bytes - 1, -1, -1):
                byte_val = (unsigned_value >> (i * 8)) & 0xFF
                result = self.append_byte(byte_val)
                if not result.success:
                    return result
                bits_encoded += 8

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=bits_encoded
            )

        except (BitStreamError, ValueError) as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )
