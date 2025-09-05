"""
ASN.1 Python Runtime Library - ACN Decoder

This module provides ACN (ASN.1 Control Notation) decoding functionality.
ACN allows custom binary encodings for ASN.1 types to support legacy protocols.
"""

import struct
from .decoder import Decoder
from .codec import DecodeResult, DECODE_OK, ERROR_INVALID_VALUE
from .bitstream import BitStreamError


class ACNDecoder(Decoder):
    """
    ACN (ASN.1 Control Notation) decoder implementation.

    This decoder provides flexible binary decoding for ASN.1 types
    following custom ACN encoding rules to support legacy protocols.
    """

    def __init__(self, buffer_size: int = 8 * 1024 * 1024) -> None:        
        super().__init__(buffer_size)

    # ============================================================================
    # INTEGER DECODING - POSITIVE INTEGER
    # ============================================================================

    def dec_int_positive_integer_const_size(self, encoded_size_in_bits: int) -> DecodeResult:
        """Decode positive integer with constant size in bits."""
        return self.decode_integer(min_val=0, max_val=(1 << encoded_size_in_bits) - 1,
                                  size_in_bits=encoded_size_in_bits)

    def dec_int_positive_integer_const_size_8(self) -> DecodeResult:
        """Decode 8-bit positive integer."""
        return self.dec_int_positive_integer_const_size(8)

    def dec_int_positive_integer_const_size_big_endian_16(self) -> DecodeResult:
        """Decode 16-bit positive integer (big-endian)."""
        return self._decode_integer_big_endian(16, False)

    def dec_int_positive_integer_const_size_big_endian_32(self) -> DecodeResult:
        """Decode 32-bit positive integer (big-endian)."""
        return self._decode_integer_big_endian(32, False)

    def dec_int_positive_integer_const_size_big_endian_64(self) -> DecodeResult:
        """Decode 64-bit positive integer (big-endian)."""
        return self._decode_integer_big_endian(64, False)

    def dec_int_positive_integer_const_size_little_endian_16(self) -> DecodeResult:
        """Decode 16-bit positive integer (little-endian)."""
        return self._decode_integer_little_endian(16, False)

    def dec_int_positive_integer_const_size_little_endian_32(self) -> DecodeResult:
        """Decode 32-bit positive integer (little-endian)."""
        return self._decode_integer_little_endian(32, False)

    def dec_int_positive_integer_const_size_little_endian_64(self) -> DecodeResult:
        """Decode 64-bit positive integer (little-endian)."""
        return self._decode_integer_little_endian(64, False)

    def dec_int_positive_integer_var_size_length_embedded(self) -> DecodeResult:
        """Decode positive integer with variable size (length embedded)."""
        try:
            length_result = self.dec_length(8)
            if not length_result.success:
                return length_result

            assert isinstance(length_result.decoded_value, int)
            bytes_count = length_result.decoded_value
            bits_consumed = length_result.bits_consumed

            if self._bitstream.bits_remaining() < bytes_count * 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data: need {bytes_count} bytes"
                )

            value = 0
            for i in range(bytes_count):
                byte_val = self._bitstream.read_bits(8)
                value = (value << 8) | byte_val
                bits_consumed += 8

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=bits_consumed
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # INTEGER DECODING - TWO'S COMPLEMENT
    # ============================================================================

    def dec_int_twos_complement_const_size(self, format_bit_length: int) -> DecodeResult:
        """Decode signed integer using two's complement with constant size."""
        try:
            if self._bitstream.bits_remaining() < format_bit_length:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data: need {format_bit_length} bits"
                )

            unsigned_val = self._bitstream.read_bits(format_bit_length)
            
            sign_bit = 1 << (format_bit_length - 1)
            if unsigned_val & sign_bit:
                signed_val = unsigned_val - (1 << format_bit_length)
            else:
                signed_val = unsigned_val

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=signed_val,
                bits_consumed=format_bit_length
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def dec_int_twos_complement_const_size_8(self) -> DecodeResult[int]:
        """Decode 8-bit signed integer."""
        return self.dec_int_twos_complement_const_size(8)

    def dec_int_twos_complement_const_size_big_endian_16(self) -> DecodeResult[int]:
        """Decode 16-bit signed integer (big-endian)."""
        return self._decode_integer_big_endian(16, True)

    def dec_int_twos_complement_const_size_big_endian_32(self) -> DecodeResult[int]:
        """Decode 32-bit signed integer (big-endian)."""
        return self._decode_integer_big_endian(32, True)

    def dec_int_twos_complement_const_size_big_endian_64(self) -> DecodeResult[int]:
        """Decode 64-bit signed integer (big-endian)."""
        return self._decode_integer_big_endian(64, True)

    def dec_int_twos_complement_const_size_little_endian_16(self) -> DecodeResult[int]:
        """Decode 16-bit signed integer (little-endian)."""
        return self._decode_integer_little_endian(16, True)

    def dec_int_twos_complement_const_size_little_endian_32(self) -> DecodeResult[int]:
        """Decode 32-bit signed integer (little-endian)."""
        return self._decode_integer_little_endian(32, True)

    def dec_int_twos_complement_const_size_little_endian_64(self) -> DecodeResult[int]:
        """Decode 64-bit signed integer (little-endian)."""
        return self._decode_integer_little_endian(64, True)

    def dec_int_twos_complement_var_size_length_embedded(self) -> DecodeResult[int]:
        """Decode signed integer with variable size (length embedded)."""
        try:
            length_result = self.dec_length(8)
            if not length_result.success:
                return length_result
            
            assert isinstance(length_result.decoded_value, int)
            bytes_count = length_result.decoded_value
            bits_consumed = length_result.bits_consumed

            if self._bitstream.bits_remaining() < bytes_count * 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data: need {bytes_count} bytes"
                )

            twos_complement = 0
            for i in range(bytes_count):
                byte_val = self._bitstream.read_bits(8)
                twos_complement = (twos_complement << 8) | byte_val
                bits_consumed += 8

            sign_bit = 1 << (bytes_count * 8 - 1)
            if twos_complement & sign_bit:
                value = twos_complement - (1 << (bytes_count * 8))
            else:
                value = twos_complement

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=bits_consumed
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # INTEGER DECODING - BCD (Binary Coded Decimal)
    # ============================================================================

    def dec_int_bcd_const_size(self, encoded_size_in_nibbles: int) -> DecodeResult[int]:
        """Decode integer from BCD format with constant size in nibbles."""
        try:
            if self._bitstream.bits_remaining() < encoded_size_in_nibbles * 4:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data: need {encoded_size_in_nibbles} nibbles"
                )

            value: int = 0
            bits_consumed = 0

            for i in range(encoded_size_in_nibbles):
                digit = self._bitstream.read_bits(4)
                if digit > 9:
                    return DecodeResult(
                        success=False,
                        error_code=ERROR_INVALID_VALUE,
                        error_message=f"Invalid BCD digit: {digit}"
                    )
                value = value * 10 + digit
                bits_consumed += 4

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=bits_consumed
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def dec_int_bcd_var_size_length_embedded(self) -> DecodeResult[int]:
        """Decode integer from BCD format with variable size (length embedded)."""
        try:
            length_result = self.dec_length(8)
            if not length_result.success:
                return length_result
            
            assert isinstance(length_result.decoded_value, int)
            nibbles_count = length_result.decoded_value

            bcd_result = self.dec_int_bcd_const_size(nibbles_count)
            if not bcd_result.success:
                return bcd_result

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=bcd_result.decoded_value,
                bits_consumed=length_result.bits_consumed + bcd_result.bits_consumed
            )
        except Exception as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def dec_int_bcd_var_size_null_terminated(self) -> DecodeResult[int]:
        """Decode integer from BCD format with null termination (0xF)."""
        try:
            value = 0
            bits_consumed = 0

            while True:
                if self._bitstream.bits_remaining() < 4:
                    return DecodeResult(
                        success=False,
                        error_code=ERROR_INVALID_VALUE,
                        error_message="Unexpected end of data while reading BCD"
                    )

                digit = self._bitstream.read_bits(4)
                bits_consumed += 4

                if digit == 0xF:
                    break

                if digit > 9:
                    return DecodeResult(
                        success=False,
                        error_code=ERROR_INVALID_VALUE,
                        error_message=f"Invalid BCD digit: {digit}"
                    )

                value = value * 10 + digit

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=bits_consumed
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # REAL DECODING - IEEE 754
    # ============================================================================

    def dec_real_ieee754_32_big_endian(self) -> DecodeResult[float]:
        """Decode 32-bit IEEE 754 float (big-endian)."""
        try:
            if self._bitstream.bits_remaining() < 32:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message="Insufficient data for IEEE 754 float"
                )

            bytes_data = bytearray()
            for i in range(4):
                bytes_data.append(self._bitstream.read_bits(8))

            value: float = struct.unpack('>f', bytes_data)[0]

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=32
            )
        except (BitStreamError, struct.error) as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def dec_real_ieee754_32_little_endian(self) -> DecodeResult[float]:
        """Decode 32-bit IEEE 754 float (little-endian)."""
        try:
            if self._bitstream.bits_remaining() < 32:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message="Insufficient data for IEEE 754 float"
                )

            bytes_data = bytearray()
            for i in range(4):
                bytes_data.append(self._bitstream.read_bits(8))

            value: float = struct.unpack('<f', bytes_data)[0]

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=32
            )
        except (BitStreamError, struct.error) as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def dec_real_ieee754_64_big_endian(self) -> DecodeResult[float]:
        """Decode 64-bit IEEE 754 double (big-endian)."""
        try:
            if self._bitstream.bits_remaining() < 64:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message="Insufficient data for IEEE 754 double"
                )

            bytes_data = bytearray()
            for i in range(8):
                bytes_data.append(self._bitstream.read_bits(8))

            value: float = struct.unpack('>d', bytes_data)[0]

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=64
            )
        except (BitStreamError, struct.error) as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def dec_real_ieee754_64_little_endian(self) -> DecodeResult[float]:
        """Decode 64-bit IEEE 754 double (little-endian)."""
        try:
            if self._bitstream.bits_remaining() < 64:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message="Insufficient data for IEEE 754 double"
                )

            bytes_data = bytearray()
            for i in range(8):
                bytes_data.append(self._bitstream.read_bits(8))

            value: float = struct.unpack('<d', bytes_data)[0]

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=64
            )
        except (BitStreamError, struct.error) as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # LENGTH DECODING
    # ============================================================================

    def dec_length(self, length_size_in_bits: int) -> DecodeResult[int]:
        """Decode length value with specified size in bits."""
        try:
            if self._bitstream.bits_remaining() < length_size_in_bits:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data for length: need {length_size_in_bits} bits"
                )

            length_val = self._bitstream.read_bits(length_size_in_bits)
            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=length_val,
                bits_consumed=length_size_in_bits
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # STRING DECODING
    # ============================================================================

    def dec_string_ascii_fix_size(self, max_len: int) -> DecodeResult:
        """Decode ASCII string with fixed size."""
        raise NotImplementedError("dec_string_ascii_fix_size not yet implemented")

    def dec_string_ascii_null_terminated(self, max_len: int, null_character: int) -> DecodeResult:
        """Decode ASCII string with null termination."""
        raise NotImplementedError("dec_string_ascii_null_terminated not yet implemented")

    def dec_string_ascii_null_terminated_mult(self, max_len: int, null_characters: bytes) -> DecodeResult:
        """Decode ASCII string with multiple null characters."""
        raise NotImplementedError("dec_string_ascii_null_terminated_mult not yet implemented")

    def dec_string_ascii_external_field_determinant(self, max_len: int, ext_size_determinant_fld: int) -> DecodeResult:
        """Decode ASCII string with external field determinant."""
        raise NotImplementedError("dec_string_ascii_external_field_determinant not yet implemented")

    def dec_string_ascii_internal_field_determinant(self, max_len: int, min_len: int) -> DecodeResult:
        """Decode ASCII string with internal field determinant."""
        raise NotImplementedError("dec_string_ascii_internal_field_determinant not yet implemented")

    def dec_string_char_index_fix_size(self, max_len: int, allowed_char_set: bytes) -> DecodeResult:
        """Decode string using character index with fixed size."""
        raise NotImplementedError("dec_string_char_index_fix_size not yet implemented")

    def dec_string_char_index_external_field_determinant(self, max_len: int, allowed_char_set: bytes, ext_size_determinant_fld: int) -> DecodeResult:
        """Decode string using character index with external field determinant."""
        raise NotImplementedError("dec_string_char_index_external_field_determinant not yet implemented")

    def dec_string_char_index_internal_field_determinant(self, max_len: int, allowed_char_set: bytes, min_len: int) -> DecodeResult:
        """Decode string using character index with internal field determinant."""
        raise NotImplementedError("dec_string_char_index_internal_field_determinant not yet implemented")

    def dec_ia5_string_char_index_external_field_determinant(self, max_len: int, ext_size_determinant_fld: int) -> DecodeResult:
        """Decode IA5 string using character index with external field determinant."""
        raise NotImplementedError("dec_ia5_string_char_index_external_field_determinant not yet implemented")

    def dec_ia5_string_char_index_internal_field_determinant(self, max_len: int, min_len: int) -> DecodeResult:
        """Decode IA5 string using character index with internal field determinant."""
        raise NotImplementedError("dec_ia5_string_char_index_internal_field_determinant not yet implemented")

    # ============================================================================
    # ASCII INTEGER DECODING - SIGNED
    # ============================================================================

    def dec_sint_ascii_const_size(self, encoded_size_in_bytes: int) -> DecodeResult:
        """Decode signed integer from ASCII with constant size."""
        raise NotImplementedError("dec_sint_ascii_const_size not yet implemented")

    def dec_sint_ascii_var_size_length_embedded(self) -> DecodeResult:
        """Decode signed integer from ASCII with variable size (length embedded)."""
        raise NotImplementedError("dec_sint_ascii_var_size_length_embedded not yet implemented")

    def dec_sint_ascii_var_size_null_terminated(self, null_characters: bytes) -> DecodeResult:
        """Decode signed integer from ASCII with null termination."""
        raise NotImplementedError("dec_sint_ascii_var_size_null_terminated not yet implemented")

    # ============================================================================
    # ASCII INTEGER DECODING - UNSIGNED
    # ============================================================================

    def dec_uint_ascii_const_size(self, encoded_size_in_bytes: int) -> DecodeResult:
        """Decode unsigned integer from ASCII with constant size."""
        raise NotImplementedError("dec_uint_ascii_const_size not yet implemented")

    def dec_uint_ascii_var_size_length_embedded(self) -> DecodeResult:
        """Decode unsigned integer from ASCII with variable size (length embedded)."""
        raise NotImplementedError("dec_uint_ascii_var_size_length_embedded not yet implemented")

    def dec_uint_ascii_var_size_null_terminated(self, null_characters: bytes) -> DecodeResult:
        """Decode unsigned integer from ASCII with null termination."""
        raise NotImplementedError("dec_uint_ascii_var_size_null_terminated not yet implemented")

    # ============================================================================
    # TYPED INTEGER DECODING FUNCTIONS (C Type Compatibility)
    # ============================================================================

    def dec_int_positive_integer_const_size_uint8(self, encoded_size_in_bits: int) -> DecodeResult:
        """Decode positive integer to uint8."""
        raise NotImplementedError("dec_int_positive_integer_const_size_uint8 not yet implemented")

    def dec_int_positive_integer_const_size_uint16(self, encoded_size_in_bits: int) -> DecodeResult:
        """Decode positive integer to uint16."""
        raise NotImplementedError("dec_int_positive_integer_const_size_uint16 not yet implemented")

    def dec_int_positive_integer_const_size_uint32(self, encoded_size_in_bits: int) -> DecodeResult:
        """Decode positive integer to uint32."""
        raise NotImplementedError("dec_int_positive_integer_const_size_uint32 not yet implemented")

    def dec_int_positive_integer_const_size_8_uint8(self) -> DecodeResult:
        """Decode 8-bit positive integer to uint8."""
        raise NotImplementedError("dec_int_positive_integer_const_size_8_uint8 not yet implemented")

    def dec_int_positive_integer_const_size_big_endian_16_uint16(self) -> DecodeResult:
        """Decode 16-bit big-endian positive integer to uint16."""
        raise NotImplementedError("dec_int_positive_integer_const_size_big_endian_16_uint16 not yet implemented")

    def dec_int_positive_integer_const_size_big_endian_16_uint8(self) -> DecodeResult:
        """Decode 16-bit big-endian positive integer to uint8."""
        raise NotImplementedError("dec_int_positive_integer_const_size_big_endian_16_uint8 not yet implemented")

    # ============================================================================
    # BOOLEAN DECODING
    # ============================================================================

    def read_bit_pattern(self, pattern_to_read: bytes, n_bits_to_read: int) -> DecodeResult:
        """Read bit pattern and return boolean value."""
        raise NotImplementedError("read_bit_pattern not yet implemented")

    def decode_true_false_boolean(self, true_pattern: bytes, false_pattern: bytes, n_bits_to_read: int) -> DecodeResult:
        """Decode boolean using true/false patterns."""
        raise NotImplementedError("decode_true_false_boolean not yet implemented")

    # ============================================================================
    # NULL TYPE FUNCTIONS
    # ============================================================================

    def read_bit_pattern_ignore_value(self, n_bits_to_read: int) -> DecodeResult:
        """Read bit pattern and ignore the value."""
        raise NotImplementedError("read_bit_pattern_ignore_value not yet implemented")

    # ============================================================================
    # IEEE 754 REAL DECODING WITH FLOAT PRECISION
    # ============================================================================

    def dec_real_ieee754_32_big_endian_fp32(self) -> DecodeResult:
        """Decode 32-bit IEEE 754 float (big-endian) with float precision."""
        raise NotImplementedError("dec_real_ieee754_32_big_endian_fp32 not yet implemented")

    def dec_real_ieee754_32_little_endian_fp32(self) -> DecodeResult:
        """Decode 32-bit IEEE 754 float (little-endian) with float precision."""
        raise NotImplementedError("dec_real_ieee754_32_little_endian_fp32 not yet implemented")

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _decode_integer_big_endian(self, bits: int, signed: bool) -> DecodeResult[int]:
        """Helper method to decode integer in big-endian format."""
        try:
            if self._bitstream.bits_remaining() < bits:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data: need {bits} bits"
                )

            unsigned_val = 0
            bytes_count = bits // 8
            for i in range(bytes_count):
                byte_val = self._bitstream.read_bits(8)
                unsigned_val = (unsigned_val << 8) | byte_val

            if signed:
                sign_bit = 1 << (bits - 1)
                if unsigned_val & sign_bit:
                    signed_val = unsigned_val - (1 << bits)
                else:
                    signed_val = unsigned_val
                value = signed_val
            else:
                value = unsigned_val

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=bits
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def _decode_integer_little_endian(self, bits: int, signed: bool) -> DecodeResult[int]:
        """Helper method to decode integer in little-endian format."""
        try:
            if self._bitstream.bits_remaining() < bits:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data: need {bits} bits"
                )

            unsigned_val = 0
            bytes_count = bits // 8
            for i in range(bytes_count):
                byte_val = self._bitstream.read_bits(8)
                unsigned_val |= (byte_val << (i * 8))

            if signed:
                sign_bit = 1 << (bits - 1)
                if unsigned_val & sign_bit:
                    signed_val = unsigned_val - (1 << bits)
                else:
                    signed_val = unsigned_val
                value = signed_val
            else:
                value = unsigned_val

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=bits
            )
        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # MILBUS FUNCTIONS
    # ============================================================================

    def milbus_decode(self, val: int) -> int:
        """Decode value using MILBUS encoding."""
        raise NotImplementedError("milbus_decode not yet implemented")