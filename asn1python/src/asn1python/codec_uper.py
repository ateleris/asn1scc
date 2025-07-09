"""
ASN.1 Python Runtime Library - UPER Codec

This module provides UPER (Unaligned Packed Encoding Rules) encoding and decoding.
"""

from typing import Optional, Union, List, Any
from .codec import Codec, EncodeResult, DecodeResult, ENCODE_OK, DECODE_OK, ERROR_INVALID_VALUE
from .bitstream import BitStream, BitStreamError
from .types import Asn1Real


class UPERCodec(Codec):
    """
    UPER (Unaligned Packed Encoding Rules) codec implementation.

    This codec provides efficient bit-packed encoding/decoding for ASN.1 types
    following the UPER standard.
    """

    def __init__(self):
        super().__init__()

    def encode_constrained_integer(self, value: int, stream: BitStream,
                                  min_val: int, max_val: int) -> EncodeResult:
        """
        Encode a constrained integer using UPER rules.

        For constrained integers, UPER uses the minimum number of bits
        needed to represent the range.
        """
        if value < min_val or value > max_val:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"Value {value} out of range [{min_val}, {max_val}]"
            )

        # Calculate bits needed for the range
        range_size = max_val - min_val + 1
        if range_size == 1:
            # Single value - no bits needed
            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=stream.get_data_copy(),
                bits_encoded=0
            )

        # Encode as offset from minimum
        offset_value = value - min_val
        bits_needed = (range_size - 1).bit_length()

        try:
            stream.write_bits(offset_value, bits_needed)
            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=stream.get_data_copy(),
                bits_encoded=bits_needed
            )
        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_constrained_integer(self, stream: BitStream,
                                  min_val: int, max_val: int) -> DecodeResult:
        """Decode a constrained integer using UPER rules"""
        range_size = max_val - min_val + 1

        if range_size == 1:
            # Single value - no bits to read
            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=min_val,
                bits_consumed=0
            )

        bits_needed = (range_size - 1).bit_length()

        try:
            if stream.bits_remaining() < bits_needed:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data: need {bits_needed} bits"
                )

            offset_value = stream.read_bits(bits_needed)
            value = offset_value + min_val

            if value > max_val:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Decoded value {value} exceeds maximum {max_val}"
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

    def encode_semi_constrained_integer(self, value: int, stream: BitStream,
                                       min_val: int) -> EncodeResult:
        """
        Encode a semi-constrained integer (only minimum bound) using UPER rules.

        Semi-constrained integers use a length determinant followed by octets.
        """
        if value < min_val:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=f"Value {value} below minimum {min_val}"
            )

        try:
            # Encode as offset from minimum
            offset_value = value - min_val

            # Determine number of octets needed
            if offset_value == 0:
                octets_needed = 1
            else:
                octets_needed = (offset_value.bit_length() + 7) // 8

            # Encode length determinant
            length_result = self._encode_length_determinant(octets_needed, stream)
            if not length_result.success:
                return length_result

            bits_encoded = length_result.bits_encoded

            # Encode the integer value in octets
            for i in range(octets_needed - 1, -1, -1):
                octet = (offset_value >> (i * 8)) & 0xFF
                stream.write_bits(octet, 8)
                bits_encoded += 8

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=stream.get_data_copy(),
                bits_encoded=bits_encoded
            )

        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_semi_constrained_integer(self, stream: BitStream,
                                       min_val: int) -> DecodeResult:
        """Decode a semi-constrained integer using UPER rules"""
        try:
            # Decode length determinant
            length_result = self._decode_length_determinant(stream)
            if not length_result.success:
                return length_result

            octets_count = length_result.decoded_value
            bits_consumed = length_result.bits_consumed

            # Decode the integer value from octets
            if stream.bits_remaining() < octets_count * 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data: need {octets_count} octets"
                )

            offset_value = 0
            for i in range(octets_count):
                octet = stream.read_bits(8)
                offset_value = (offset_value << 8) | octet
                bits_consumed += 8

            value = offset_value + min_val

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

    def encode_unconstrained_integer(self, value: int, stream: BitStream) -> EncodeResult:
        """
        Encode an unconstrained integer using UPER rules.

        Unconstrained integers use a length determinant followed by 
        two's complement representation.
        """
        try:
            # Determine number of octets needed for two's complement
            if value >= 0:
                # Positive: need extra bit for sign if MSB is 1
                bit_length = value.bit_length()
                octets_needed = (bit_length + 8) // 8  # +1 for sign bit, then round up
            else:
                # Negative: use two's complement
                bit_length = (abs(value) - 1).bit_length()
                octets_needed = (bit_length + 8) // 8

            if octets_needed == 0:
                octets_needed = 1

            # Encode length determinant
            length_result = self._encode_length_determinant(octets_needed, stream)
            if not length_result.success:
                return length_result

            bits_encoded = length_result.bits_encoded

            # Convert to two's complement representation
            if value >= 0:
                twos_complement = value
            else:
                twos_complement = (1 << (octets_needed * 8)) + value

            # Encode the integer value in octets (big-endian)
            for i in range(octets_needed - 1, -1, -1):
                octet = (twos_complement >> (i * 8)) & 0xFF
                stream.write_bits(octet, 8)
                bits_encoded += 8

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=stream.get_data_copy(),
                bits_encoded=bits_encoded
            )

        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_unconstrained_integer(self, stream: BitStream) -> DecodeResult:
        """Decode an unconstrained integer using UPER rules"""
        try:
            # Decode length determinant
            length_result = self._decode_length_determinant(stream)
            if not length_result.success:
                return length_result

            octets_count = length_result.decoded_value
            bits_consumed = length_result.bits_consumed

            # Decode the integer value from octets
            if stream.bits_remaining() < octets_count * 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Insufficient data: need {octets_count} octets"
                )

            # Read octets (big-endian)
            twos_complement = 0
            for i in range(octets_count):
                octet = stream.read_bits(8)
                twos_complement = (twos_complement << 8) | octet
                bits_consumed += 8

            # Convert from two's complement
            sign_bit = 1 << (octets_count * 8 - 1)
            if twos_complement & sign_bit:
                # Negative number
                value = twos_complement - (1 << (octets_count * 8))
            else:
                # Positive number
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

    def encode_real(self, value: float, stream: BitStream) -> EncodeResult:
        """
        Encode a REAL value using UPER rules.

        UPER encoding of REAL uses IEEE 754 double precision format.
        """
        try:
            import struct

            # Handle special cases
            if value == 0.0:
                # Zero is encoded as empty (length 0)
                return self._encode_length_determinant(0, stream)

            # Convert to IEEE 754 double precision
            ieee_bytes = struct.pack('>d', value)  # Big-endian double

            # Encode length determinant (8 octets for IEEE double)
            length_result = self._encode_length_determinant(8, stream)
            if not length_result.success:
                return length_result

            bits_encoded = length_result.bits_encoded

            # Encode the IEEE 754 bytes
            for byte in ieee_bytes:
                stream.write_bits(byte, 8)
                bits_encoded += 8

            return EncodeResult(
                success=True,
                error_code=ENCODE_OK,
                encoded_data=stream.get_data_copy(),
                bits_encoded=bits_encoded
            )

        except (BitStreamError, struct.error) as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def decode_real(self, stream: BitStream) -> DecodeResult:
        """Decode a REAL value using UPER rules"""
        try:
            import struct

            # Decode length determinant
            length_result = self._decode_length_determinant(stream)
            if not length_result.success:
                return length_result

            octets_count = length_result.decoded_value
            bits_consumed = length_result.bits_consumed

            # Handle special case of zero
            if octets_count == 0:
                return DecodeResult(
                    success=True,
                    error_code=DECODE_OK,
                    decoded_value=0.0,
                    bits_consumed=bits_consumed
                )

            # Expect 8 octets for IEEE double
            if octets_count != 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Expected 8 octets for IEEE double, got {octets_count}"
                )

            # Read IEEE 754 bytes
            if stream.bits_remaining() < 64:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message="Insufficient data for IEEE double"
                )

            ieee_bytes = bytearray()
            for i in range(8):
                octet = stream.read_bits(8)
                ieee_bytes.append(octet)
                bits_consumed += 8

            # Convert from IEEE 754 double precision
            value = struct.unpack('>d', ieee_bytes)[0]

            return DecodeResult(
                success=True,
                error_code=DECODE_OK,
                decoded_value=value,
                bits_consumed=bits_consumed
            )

        except (BitStreamError, struct.error) as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def _encode_length_determinant(self, length: int, stream: BitStream) -> EncodeResult:
        """
        Encode a length determinant according to UPER rules.

        Length determinants are used for variable-length encodings.
        """
        try:
            if length < 0:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Length cannot be negative: {length}"
                )

            if length < 128:
                # Short form: 0xxxxxxx
                stream.write_bits(length, 8)
                return EncodeResult(
                    success=True,
                    error_code=ENCODE_OK,
                    encoded_data=stream.get_data_copy(),
                    bits_encoded=8
                )
            elif length < 16384:
                # Medium form: 10xxxxxx xxxxxxxx
                stream.write_bits(0x8000 | length, 16)
                return EncodeResult(
                    success=True,
                    error_code=ENCODE_OK,
                    encoded_data=stream.get_data_copy(),
                    bits_encoded=16
                )
            else:
                # Long form: 11xxxxxx + length in octets
                return EncodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message=f"Length {length} too large for UPER encoding"
                )

        except BitStreamError as e:
            return EncodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )

    def _decode_length_determinant(self, stream: BitStream) -> DecodeResult:
        """Decode a length determinant according to UPER rules"""
        try:
            if stream.bits_remaining() < 8:
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message="Insufficient data for length determinant"
                )

            first_byte = stream.read_bits(8)

            if (first_byte & 0x80) == 0:
                # Short form: 0xxxxxxx
                return DecodeResult(
                    success=True,
                    error_code=DECODE_OK,
                    decoded_value=first_byte,
                    bits_consumed=8
                )
            elif (first_byte & 0xC0) == 0x80:
                # Medium form: 10xxxxxx xxxxxxxx
                if stream.bits_remaining() < 8:
                    return DecodeResult(
                        success=False,
                        error_code=ERROR_INVALID_VALUE,
                        error_message="Insufficient data for medium length determinant"
                    )

                second_byte = stream.read_bits(8)
                length = ((first_byte & 0x3F) << 8) | second_byte

                return DecodeResult(
                    success=True,
                    error_code=DECODE_OK,
                    decoded_value=length,
                    bits_consumed=16
                )
            else:
                # Long form: 11xxxxxx - not supported in this implementation
                return DecodeResult(
                    success=False,
                    error_code=ERROR_INVALID_VALUE,
                    error_message="Long form length determinant not supported"
                )

        except BitStreamError as e:
            return DecodeResult(
                success=False,
                error_code=ERROR_INVALID_VALUE,
                error_message=str(e)
            )