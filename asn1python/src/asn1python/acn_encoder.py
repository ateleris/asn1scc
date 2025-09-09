"""
ASN.1 Python Runtime Library - ACN Encoder

This module provides ACN (ASN.1 Control Notation) encoding functionality.
ACN allows custom binary encodings for ASN.1 types to support legacy protocols.
"""

import struct

from .acn_decoder import ACNDecoder
from .bitstream import BitStreamError
from .codec import EncodeResult, ENCODE_OK, ERROR_INVALID_VALUE
from .encoder import Encoder


class ACNEncoder(Encoder):
    """
    ACN (ASN.1 Control Notation) encoder implementation.

    This encoder provides flexible binary encoding for ASN.1 types
    following custom ACN encoding rules to support legacy protocols.
    """

    def __init__(self, buffer_bit_size: int = 8 * 1024 * 1024) -> None:
        super().__init__(buffer_bit_size=buffer_bit_size)

    def get_decoder(self) -> ACNDecoder:
        return ACNDecoder(self.get_bitstream_buffer())

    # ============================================================================
    # INTEGER ENCODING - POSITIVE INTEGER
    # ============================================================================

    def enc_int_positive_integer_const_size(self, int_val: int,
                                            encoded_size_in_bits: int) -> EncodeResult:
        """Encode positive integer with constant size in bits."""
        return self.encode_integer(int_val, min_val=0, max_val=(1 << encoded_size_in_bits) - 1, 
                                  size_in_bits=encoded_size_in_bits)

    # def enc_int_positive_integer_const_size_8(self, int_val: int) -> EncodeResult:
    #     """Encode 8-bit positive integer."""
    #     return self.enc_int_positive_integer_const_size(int_val, 8)

    # def enc_int_positive_integer_const_size_big_endian_16(self, int_val: int) -> EncodeResult:
    #     """Encode 16-bit positive integer (big-endian)."""
    #     return self._encode_integer_big_endian(int_val, 16, False)
    #
    # def enc_int_positive_integer_const_size_big_endian_32(self, int_val: int) -> EncodeResult:
    #     """Encode 32-bit positive integer (big-endian)."""
    #     return self._encode_integer_big_endian(int_val, 32, False)
    #
    # def enc_int_positive_integer_const_size_big_endian_64(self, int_val: int) -> EncodeResult:
    #     """Encode 64-bit positive integer (big-endian)."""
    #     return self._encode_integer_big_endian(int_val, 64, False)

    # def enc_int_positive_integer_const_size_little_endian_16(self, int_val: int) -> EncodeResult:
    #     """Encode 16-bit positive integer (little-endian)."""
    #     return self._encode_integer_little_endian(int_val, 16, False)
    #
    # def enc_int_positive_integer_const_size_little_endian_32(self, int_val: int) -> EncodeResult:
    #     """Encode 32-bit positive integer (little-endian)."""
    #     return self._encode_integer_little_endian(int_val, 32, False)
    #
    # def enc_int_positive_integer_const_size_little_endian_64(self, int_val: int) -> EncodeResult:
    #     """Encode 64-bit positive integer (little-endian)."""
    #     return self._encode_integer_little_endian(int_val, 64, False)

    def enc_int_positive_integer_var_size_length_embedded(self, int_val: int) -> EncodeResult:
        """Encode positive integer with variable size (length embedded)."""
        if int_val < 0:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"Value {int_val} must be non-negative"
            )

        try:
            if int_val == 0:
                bytes_needed = 1
            else:
                bytes_needed = (int_val.bit_length() + 7) // 8


            length_result = self.enc_length(bytes_needed, 8)
            if not length_result.success:
                return length_result

            bits_encoded = length_result.bits_encoded

            for i in range(bytes_needed - 1, -1, -1):
                byte_val = (int_val >> (i * 8)) & 0xFF
                self._bitstream.write_bits(byte_val, 8)
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

    # ============================================================================
    # INTEGER ENCODING - TWO'S COMPLEMENT
    # ============================================================================

    def enc_int_twos_complement_const_size(self, int_val: int, format_bit_length: int) -> EncodeResult:
        """Encode signed integer using two's complement with constant size."""
        min_val = -(1 << (format_bit_length - 1))
        max_val = (1 << (format_bit_length - 1)) - 1
        return self.encode_integer(int_val, min_val=min_val, max_val=max_val, size_in_bits=format_bit_length)

    # def enc_int_twos_complement_const_size_8(self, int_val: int) -> EncodeResult:
    #     """Encode 8-bit signed integer."""
    #     return self.enc_int_twos_complement_const_size(int_val, 8)
    #
    # def enc_int_twos_complement_const_size_big_endian_16(self, int_val: int) -> EncodeResult:
    #     """Encode 16-bit signed integer (big-endian)."""
    #     return self._encode_integer_big_endian(int_val, 16, True)
    #
    # def enc_int_twos_complement_const_size_big_endian_32(self, int_val: int) -> EncodeResult:
    #     """Encode 32-bit signed integer (big-endian)."""
    #     return self._encode_integer_big_endian(int_val, 32, True)
    #
    # def enc_int_twos_complement_const_size_big_endian_64(self, int_val: int) -> EncodeResult:
    #     """Encode 64-bit signed integer (big-endian)."""
    #     return self._encode_integer_big_endian(int_val, 64, True)
    #
    # def enc_int_twos_complement_const_size_little_endian_16(self, int_val: int) -> EncodeResult:
    #     """Encode 16-bit signed integer (little-endian)."""
    #     return self._encode_integer_little_endian(int_val, 16, True)
    #
    # def enc_int_twos_complement_const_size_little_endian_32(self, int_val: int) -> EncodeResult:
    #     """Encode 32-bit signed integer (little-endian)."""
    #     return self._encode_integer_little_endian(int_val, 32, True)
    #
    # def enc_int_twos_complement_const_size_little_endian_64(self, int_val: int) -> EncodeResult:
    #     """Encode 64-bit signed integer (little-endian)."""
    #     return self._encode_integer_little_endian(int_val, 64, True)

    def enc_int_twos_complement_var_size_length_embedded(self, int_val: int) -> EncodeResult:
        """Encode signed integer with variable size (length embedded)."""
        try:
            if int_val >= 0:
                bit_length = int_val.bit_length()
                bytes_needed = (bit_length + 8) // 8
            else:
                bit_length = (abs(int_val) - 1).bit_length()
                bytes_needed = (bit_length + 8) // 8

            if bytes_needed == 0:
                bytes_needed = 1

            length_result = self.enc_length(bytes_needed, 8)
            if not length_result.success:
                return length_result

            bits_encoded = length_result.bits_encoded

            if int_val >= 0:
                twos_complement = int_val
            else:
                twos_complement = (1 << (bytes_needed * 8)) + int_val

            for i in range(bytes_needed - 1, -1, -1):
                byte_val = (twos_complement >> (i * 8)) & 0xFF
                self._bitstream.write_bits(byte_val, 8)
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

    # ============================================================================
    # INTEGER ENCODING - BCD (Binary Coded Decimal)
    # ============================================================================

    def enc_int_bcd_const_size(self, int_val: int, encoded_size_in_nibbles: int) -> EncodeResult:
        """Encode integer in BCD format with constant size in nibbles."""
        if int_val < 0:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"BCD encoding requires non-negative value, got {int_val}"
            )

        try:
            digits = []
            temp_val = int_val
            while temp_val > 0:
                digits.append(temp_val % 10)
                temp_val //= 10

            while len(digits) < encoded_size_in_nibbles:
                digits.append(0)

            if len(digits) > encoded_size_in_nibbles:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Value {int_val} requires more than {encoded_size_in_nibbles} BCD digits"
                )

            bits_encoded = 0
            for i in range(encoded_size_in_nibbles - 1, -1, -1):
                self._bitstream.write_bits(digits[i], 4)
                bits_encoded += 4

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

    def enc_int_bcd_var_size_length_embedded(self, int_val: int) -> EncodeResult:
        """Encode integer in BCD format with variable size (length embedded)."""
        if int_val < 0:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"BCD encoding requires non-negative value, got {int_val}"
            )

        try:
            if int_val == 0:
                nibbles_needed = 1
            else:
                nibbles_needed = 0
                temp_val = int_val
                while temp_val > 0:
                    nibbles_needed += 1
                    temp_val //= 10

            length_result = self.enc_length(nibbles_needed, 8)
            if not length_result.success:
                return length_result

            bcd_result = self.enc_int_bcd_const_size(int_val, nibbles_needed)
            if not bcd_result.success:
                return bcd_result

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=length_result.bits_encoded + bcd_result.bits_encoded
            )
        except Exception as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def enc_int_bcd_var_size_null_terminated(self, int_val: int) -> EncodeResult:
        """Encode integer in BCD format with null termination (0xF)."""
        if int_val < 0:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"BCD encoding requires non-negative value, got {int_val}"
            )

        try:
            if int_val == 0:
                nibbles_needed = 1
            else:
                nibbles_needed = 0
                temp_val = int_val
                while temp_val > 0:
                    nibbles_needed += 1
                    temp_val //= 10

            bcd_result = self.enc_int_bcd_const_size(int_val, nibbles_needed)
            if not bcd_result.success:
                return bcd_result

            self._bitstream.write_bits(0xF, 4)

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=bcd_result.bits_encoded + 4
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # REAL ENCODING - IEEE 754
    # ============================================================================

    def enc_real_ieee754_32_big_endian(self, real_val: float) -> EncodeResult:
        """Encode 32-bit IEEE 754 float (big-endian).
        
        Args:
            real_val: Single-precision float (32-bit) - Python will truncate from double precision
        """
        try:
            packed = struct.pack('>f', real_val)
            for byte in packed:
                self._bitstream.write_bits(byte, 8)

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=32
            )
        except (BitStreamError, struct.error) as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def enc_real_ieee754_32_little_endian(self, real_val: float) -> EncodeResult:
        """Encode 32-bit IEEE 754 float (little-endian).
        
        Args:
            real_val: Single-precision float (32-bit) - Python will truncate from double precision
        """
        try:
            packed = struct.pack('<f', real_val)
            for byte in packed:
                self._bitstream.write_bits(byte, 8)

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=32
            )
        except (BitStreamError, struct.error) as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def enc_real_ieee754_64_big_endian(self, real_val: float) -> EncodeResult:
        """Encode 64-bit IEEE 754 double (big-endian).
        
        Args:
            real_val: Double-precision float (64-bit) - Python's native float precision
        """
        try:
            packed = struct.pack('>d', real_val)
            for byte in packed:
                self._bitstream.write_bits(byte, 8)

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=64
            )
        except (BitStreamError, struct.error) as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def enc_real_ieee754_64_little_endian(self, real_val: float) -> EncodeResult:
        """Encode 64-bit IEEE 754 double (little-endian).
        
        Args:
            real_val: Double-precision float (64-bit) - Python's native float precision
        """
        try:
            packed = struct.pack('<d', real_val)
            for byte in packed:
                self._bitstream.write_bits(byte, 8)

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=64
            )
        except (BitStreamError, struct.error) as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # LENGTH ENCODING
    # ============================================================================

    def enc_length(self, length_val: int, length_size_in_bits: int) -> EncodeResult:
        """Encode length value with specified size in bits."""
        if length_val < 0:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"Length cannot be negative: {length_val}"
            )

        max_value = (1 << length_size_in_bits) - 1
        if length_val > max_value:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"Length {length_val} exceeds {length_size_in_bits} bits"
            )

        try:
            self._bitstream.write_bits(length_val, length_size_in_bits)
            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=length_size_in_bits
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # STRING ENCODING
    # ============================================================================

    def enc_string_ascii_fix_size(self, max_len: int, str_val: str) -> EncodeResult:
        """Encode ASCII string with fixed size."""
        raise NotImplementedError("enc_string_ascii_fix_size not yet implemented")

    def enc_string_ascii_null_terminated(self, max_len: int, null_character: int, str_val: str) -> EncodeResult:
        """Encode ASCII string with null termination."""
        raise NotImplementedError("enc_string_ascii_null_terminated not yet implemented")

    def enc_string_ascii_null_terminated_mult(self, max_len: int, null_characters: bytes, str_val: str) -> EncodeResult:
        """Encode ASCII string with multiple null characters."""
        raise NotImplementedError("enc_string_ascii_null_terminated_mult not yet implemented")

    def enc_string_ascii_external_field_determinant(self, max_len: int, str_val: str) -> EncodeResult:
        """Encode ASCII string with external field determinant."""
        raise NotImplementedError("enc_string_ascii_external_field_determinant not yet implemented")

    def enc_string_ascii_internal_field_determinant(self, max_len: int, min_len: int, str_val: str) -> EncodeResult:
        """Encode ASCII string with internal field determinant."""
        raise NotImplementedError("enc_string_ascii_internal_field_determinant not yet implemented")

    def enc_string_char_index_fix_size(self, max_len: int, allowed_char_set: bytes, str_val: str) -> EncodeResult:
        """Encode string using character index with fixed size."""
        raise NotImplementedError("enc_string_char_index_fix_size not yet implemented")

    def enc_string_char_index_external_field_determinant(self, max_len: int, allowed_char_set: bytes, str_val: str) -> EncodeResult:
        """Encode string using character index with external field determinant."""
        raise NotImplementedError("enc_string_char_index_external_field_determinant not yet implemented")

    def enc_string_char_index_internal_field_determinant(self, max_len: int, allowed_char_set: bytes, min_len: int, str_val: str) -> EncodeResult:
        """Encode string using character index with internal field determinant."""
        raise NotImplementedError("enc_string_char_index_internal_field_determinant not yet implemented")

    def enc_ia5_string_char_index_external_field_determinant(self, max_len: int, str_val: str) -> EncodeResult:
        """Encode IA5 string using character index with external field determinant."""
        raise NotImplementedError("enc_ia5_string_char_index_external_field_determinant not yet implemented")

    def enc_ia5_string_char_index_internal_field_determinant(self, max_len: int, min_len: int, str_val: str) -> EncodeResult:
        """Encode IA5 string using character index with internal field determinant."""
        raise NotImplementedError("enc_ia5_string_char_index_internal_field_determinant not yet implemented")

    # ============================================================================
    # ASCII INTEGER ENCODING - SIGNED
    # ============================================================================

    def enc_sint_ascii_const_size(self, int_val: int, encoded_size_in_bytes: int) -> EncodeResult:
        """Encode signed integer as ASCII with constant size."""
        raise NotImplementedError("enc_sint_ascii_const_size not yet implemented")

    def enc_sint_ascii_var_size_length_embedded(self, int_val: int) -> EncodeResult:
        """Encode signed integer as ASCII with variable size (length embedded)."""
        raise NotImplementedError("enc_sint_ascii_var_size_length_embedded not yet implemented")

    def enc_sint_ascii_var_size_null_terminated(self, int_val: int, null_characters: bytes) -> EncodeResult:
        """Encode signed integer as ASCII with null termination."""
        raise NotImplementedError("enc_sint_ascii_var_size_null_terminated not yet implemented")

    # ============================================================================
    # ASCII INTEGER ENCODING - UNSIGNED
    # ============================================================================

    def enc_uint_ascii_const_size(self, int_val: int, encoded_size_in_bytes: int) -> EncodeResult:
        """Encode unsigned integer as ASCII with constant size."""
        raise NotImplementedError("enc_uint_ascii_const_size not yet implemented")

    def enc_uint_ascii_var_size_length_embedded(self, int_val: int) -> EncodeResult:
        """Encode unsigned integer as ASCII with variable size (length embedded)."""
        raise NotImplementedError("enc_uint_ascii_var_size_length_embedded not yet implemented")

    def enc_uint_ascii_var_size_null_terminated(self, int_val: int, null_characters: bytes) -> EncodeResult:
        """Encode unsigned integer as ASCII with null termination."""
        raise NotImplementedError("enc_uint_ascii_var_size_null_terminated not yet implemented")

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _encode_integer_big_endian(self, int_val: int, bits: int, signed: bool) -> EncodeResult:
        """Helper method to encode integer in big-endian format."""
        if signed:
            min_val = -(1 << (bits - 1))
            max_val = (1 << (bits - 1)) - 1
        else:
            min_val = 0
            max_val = (1 << bits) - 1

        if int_val < min_val or int_val > max_val:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"Value {int_val} out of range [{min_val}, {max_val}]"
            )

        try:
            if signed and int_val < 0:
                unsigned_val = (1 << bits) + int_val
            else:
                unsigned_val = int_val

            bytes_count = bits // 8
            for i in range(bytes_count - 1, -1, -1):
                byte_val = (unsigned_val >> (i * 8)) & 0xFF
                self._bitstream.write_bits(byte_val, 8)

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=bits
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def _encode_integer_little_endian(self, int_val: int, bits: int, signed: bool) -> EncodeResult:
        """Helper method to encode integer in little-endian format."""
        if signed:
            min_val = -(1 << (bits - 1))
            max_val = (1 << (bits - 1)) - 1
        else:
            min_val = 0
            max_val = (1 << bits) - 1

        if int_val < min_val or int_val > max_val:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"Value {int_val} out of range [{min_val}, {max_val}]"
            )

        try:
            if signed and int_val < 0:
                unsigned_val = (1 << bits) + int_val
            else:
                unsigned_val = int_val

            bytes_count = bits // 8
            for i in range(bytes_count):
                byte_val = (unsigned_val >> (i * 8)) & 0xFF
                self._bitstream.write_bits(byte_val, 8)

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=self._bitstream.get_data_copy(),
                bits_encoded=bits
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    # ============================================================================
    # MILBUS FUNCTIONS
    # ============================================================================

    def milbus_encode(self, val: int) -> int:
        """Encode value using MILBUS encoding."""
        raise NotImplementedError("milbus_encode not yet implemented")