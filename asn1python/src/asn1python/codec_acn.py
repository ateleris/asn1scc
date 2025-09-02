"""
ASN.1 Python Runtime Library - ACN Codec

This module provides ACN (ASN.1 Control Notation) encoding and decoding.
ACN allows custom binary encodings for ASN.1 types to support legacy protocols.
"""

import struct
from codec import Codec, EncodeResult, DecodeResult, ENCODE_OK, DECODE_OK, ERROR_INVALID_VALUE
from bitstream import BitStream, BitStreamError


class ACNCodec(Codec):
    """
    ACN (ASN.1 Control Notation) codec implementation.

    This codec provides flexible binary encoding/decoding for ASN.1 types
    following custom ACN encoding rules to support legacy protocols.
    """

    def __init__(self, buffer_size: int = 8 * 1024 * 1024) -> None:        
        super().__init__(buffer_size)

    def copy(self) -> 'ACNCodec':
        """Creates and returns a copy of this codec instance"""
        current_data = self._bitstream.get_data_copy()
        curret_position = self._bitstream.current_bit_position

        new_codec = ACNCodec(buffer_size=self._max_bits)
        new_codec._bitstream.reset()
        if len(current_data) > 0:
            new_codec._bitstream.write_bytes(current_data)
        new_codec._bitstream.set_bit_position(curret_position)

        return new_codec

    # ============================================================================
    # INTEGER ENCODING/DECODING - POSITIVE INTEGER
    # ============================================================================

    def enc_int_positive_integer_const_size(self, int_val: int,
                                            encoded_size_in_bits: int) -> EncodeResult:
        """Encode positive integer with constant size in bits."""
        return self.encode_integer(int_val, min_val=0, max_val=(1 << encoded_size_in_bits) - 1, 
                                  size_in_bits=encoded_size_in_bits)

    def dec_int_positive_integer_const_size(self, encoded_size_in_bits: int) -> DecodeResult:
        """Decode positive integer with constant size in bits."""
        return self.decode_integer(min_val=0, max_val=(1 << encoded_size_in_bits) - 1,
                                  size_in_bits=encoded_size_in_bits)

    def enc_int_positive_integer_const_size_8(self, int_val: int) -> EncodeResult:
        """Encode 8-bit positive integer."""
        return self.enc_int_positive_integer_const_size(int_val, 8)

    def dec_int_positive_integer_const_size_8(self) -> DecodeResult:
        """Decode 8-bit positive integer."""
        return self.dec_int_positive_integer_const_size(8)

    def enc_int_positive_integer_const_size_big_endian_16(self, int_val: int) -> EncodeResult:
        """Encode 16-bit positive integer (big-endian)."""
        return self._encode_integer_big_endian(int_val, 16, False)

    def dec_int_positive_integer_const_size_big_endian_16(self) -> DecodeResult:
        """Decode 16-bit positive integer (big-endian)."""
        return self._decode_integer_big_endian(16, False)

    def enc_int_positive_integer_const_size_big_endian_32(self, int_val: int) -> EncodeResult:
        """Encode 32-bit positive integer (big-endian)."""
        return self._encode_integer_big_endian(int_val, 32, False)

    def dec_int_positive_integer_const_size_big_endian_32(self) -> DecodeResult:
        """Decode 32-bit positive integer (big-endian)."""
        return self._decode_integer_big_endian(32, False)

    def enc_int_positive_integer_const_size_big_endian_64(self, int_val: int) -> EncodeResult:
        """Encode 64-bit positive integer (big-endian)."""
        return self._encode_integer_big_endian(int_val, 64, False)

    def dec_int_positive_integer_const_size_big_endian_64(self) -> DecodeResult:
        """Decode 64-bit positive integer (big-endian)."""
        return self._decode_integer_big_endian(64, False)

    def enc_int_positive_integer_const_size_little_endian_16(self, int_val: int) -> EncodeResult:
        """Encode 16-bit positive integer (little-endian)."""
        return self._encode_integer_little_endian(int_val, 16, False)

    def dec_int_positive_integer_const_size_little_endian_16(self) -> DecodeResult:
        """Decode 16-bit positive integer (little-endian)."""
        return self._decode_integer_little_endian(16, False)

    def enc_int_positive_integer_const_size_little_endian_32(self, int_val: int) -> EncodeResult:
        """Encode 32-bit positive integer (little-endian)."""
        return self._encode_integer_little_endian(int_val, 32, False)

    def dec_int_positive_integer_const_size_little_endian_32(self) -> DecodeResult:
        """Decode 32-bit positive integer (little-endian)."""
        return self._decode_integer_little_endian(32, False)

    def enc_int_positive_integer_const_size_little_endian_64(self, int_val: int) -> EncodeResult:
        """Encode 64-bit positive integer (little-endian)."""
        return self._encode_integer_little_endian(int_val, 64, False)

    def dec_int_positive_integer_const_size_little_endian_64(self) -> DecodeResult:
        """Decode 64-bit positive integer (little-endian)."""
        return self._decode_integer_little_endian(64, False)

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
    # INTEGER ENCODING/DECODING - TWO'S COMPLEMENT
    # ============================================================================

    def enc_int_twos_complement_const_size(self, int_val: int, format_bit_length: int) -> EncodeResult:
        """Encode signed integer using two's complement with constant size."""
        min_val = -(1 << (format_bit_length - 1))
        max_val = (1 << (format_bit_length - 1)) - 1
        return self.encode_integer(int_val, min_val=min_val, max_val=max_val, 
                                  size_in_bits=format_bit_length)

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

    def enc_int_twos_complement_const_size_8(self, int_val: int) -> EncodeResult:
        """Encode 8-bit signed integer."""
        return self.enc_int_twos_complement_const_size(int_val, 8)

    def dec_int_twos_complement_const_size_8(self) -> DecodeResult[int]:
        """Decode 8-bit signed integer."""
        return self.dec_int_twos_complement_const_size(8)

    def enc_int_twos_complement_const_size_big_endian_16(self, int_val: int) -> EncodeResult:
        """Encode 16-bit signed integer (big-endian)."""
        return self._encode_integer_big_endian(int_val, 16, True)

    def dec_int_twos_complement_const_size_big_endian_16(self) -> DecodeResult[int]:
        """Decode 16-bit signed integer (big-endian)."""
        return self._decode_integer_big_endian(16, True)

    def enc_int_twos_complement_const_size_big_endian_32(self, int_val: int) -> EncodeResult:
        """Encode 32-bit signed integer (big-endian)."""
        return self._encode_integer_big_endian(int_val, 32, True)

    def dec_int_twos_complement_const_size_big_endian_32(self) -> DecodeResult[int]:
        """Decode 32-bit signed integer (big-endian)."""
        return self._decode_integer_big_endian(32, True)

    def enc_int_twos_complement_const_size_big_endian_64(self, int_val: int) -> EncodeResult:
        """Encode 64-bit signed integer (big-endian)."""
        return self._encode_integer_big_endian(int_val, 64, True)

    def dec_int_twos_complement_const_size_big_endian_64(self) -> DecodeResult[int]:
        """Decode 64-bit signed integer (big-endian)."""
        return self._decode_integer_big_endian(64, True)

    def enc_int_twos_complement_const_size_little_endian_16(self, int_val: int) -> EncodeResult:
        """Encode 16-bit signed integer (little-endian)."""
        return self._encode_integer_little_endian(int_val, 16, True)

    def dec_int_twos_complement_const_size_little_endian_16(self) -> DecodeResult[int]:
        """Decode 16-bit signed integer (little-endian)."""
        return self._decode_integer_little_endian(16, True)

    def enc_int_twos_complement_const_size_little_endian_32(self, int_val: int) -> EncodeResult:
        """Encode 32-bit signed integer (little-endian)."""
        return self._encode_integer_little_endian(int_val, 32, True)

    def dec_int_twos_complement_const_size_little_endian_32(self) -> DecodeResult[int]:
        """Decode 32-bit signed integer (little-endian)."""
        return self._decode_integer_little_endian(32, True)

    def enc_int_twos_complement_const_size_little_endian_64(self, int_val: int) -> EncodeResult:
        """Encode 64-bit signed integer (little-endian)."""
        return self._encode_integer_little_endian(int_val, 64, True)

    def dec_int_twos_complement_const_size_little_endian_64(self) -> DecodeResult[int]:
        """Decode 64-bit signed integer (little-endian)."""
        return self._decode_integer_little_endian(64, True)

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
    # INTEGER ENCODING/DECODING - BCD (Binary Coded Decimal)
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
    # REAL ENCODING/DECODING - IEEE 754
    # ============================================================================

    def enc_real_ieee754_32_big_endian(self, real_val: float) -> EncodeResult:
        """Encode 32-bit IEEE 754 float (big-endian)."""
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

    def enc_real_ieee754_32_little_endian(self, real_val: float) -> EncodeResult:
        """Encode 32-bit IEEE 754 float (little-endian)."""
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

    def enc_real_ieee754_64_big_endian(self, real_val: float) -> EncodeResult:
        """Encode 64-bit IEEE 754 double (big-endian)."""
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

    def enc_real_ieee754_64_little_endian(self, real_val: float) -> EncodeResult:
        """Encode 64-bit IEEE 754 double (little-endian)."""
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
    # LENGTH ENCODING/DECODING
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