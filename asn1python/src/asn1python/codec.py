"""
ASN.1 Python Runtime Library - Base Codec Framework

This module provides the base codec framework for ASN.1 encoding/decoding operations.
"""

from typing import Optional, Any
from dataclasses import dataclass
from enum import IntEnum
from .bitstream import BitStream, BitStreamError
from .asn1_types import Asn1Error


class ErrorCode(IntEnum):
    """Error codes for encoding/decoding operations"""
    SUCCESS = 0
    INSUFFICIENT_DATA = 1
    INVALID_VALUE = 2
    CONSTRAINT_VIOLATION = 3
    BUFFER_OVERFLOW = 4
    UNSUPPORTED_OPERATION = 5


# Constants for common error codes
ENCODE_OK = ErrorCode.SUCCESS
DECODE_OK = ErrorCode.SUCCESS
ERROR_INSUFFICIENT_DATA = ErrorCode.INSUFFICIENT_DATA
ERROR_INVALID_VALUE = ErrorCode.INVALID_VALUE
ERROR_CONSTRAINT_VIOLATION = ErrorCode.CONSTRAINT_VIOLATION
ERROR_BUFFER_OVERFLOW = ErrorCode.BUFFER_OVERFLOW
ERROR_UNSUPPORTED_OPERATION = ErrorCode.UNSUPPORTED_OPERATION


@dataclass
class EncodeResult:
    """Result of an encoding operation"""
    success: bool
    error_code: ErrorCode
    encoded_data: Optional[bytearray] = None
    bits_encoded: int = 0
    error_message: Optional[str] = None


@dataclass
class DecodeResult:
    """Result of a decoding operation"""
    success: bool
    error_code: ErrorCode
    decoded_value: Optional[Any] = None
    bits_consumed: int = 0
    error_message: Optional[str] = None


class CodecError(Asn1Error):
    """Base class for codec errors"""
    pass


class Codec:
    """
    Base class for ASN.1 codecs.

    This class provides common functionality for all ASN.1 encoding rules
    including UPER, ACN, XER, and BER.
    """

    def __init__(self, buffer_size = 8 * 1024 * 1024):
        assert buffer_size > 0, "Codec buffer_size must be greater than zero"
        self._max_bits = buffer_size  # 1MB default max size
        self._bitstream = BitStream(size_in_bits=self._max_bits)

    def encode_boolean(self, value: bool) -> EncodeResult:
        """Encode a boolean value"""
        try:
            self._bitstream.write_bit(value)
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

    def decode_boolean(self) -> DecodeResult:
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

    def encode_integer(self, value: int,
                      min_val: Optional[int] = None, 
                      max_val: Optional[int] = None,
                      size_in_bits: Optional[int] = None) -> EncodeResult:
        """
        Encode an integer value with optional constraints.

        Args:
            value: The integer value to encode
            min_val: Minimum allowed value (optional)
            max_val: Maximum allowed value (optional)
            size_in_bits: Fixed size in bits (optional)
        """
        try:
            # Validate constraints
            if min_val is not None and value < min_val:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Value {value} below minimum {min_val}"
                )

            if max_val is not None and value > max_val:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Value {value} above maximum {max_val}"
                )

            # Determine encoding size
            if size_in_bits is not None:
                bits_needed = size_in_bits
            elif min_val is not None and max_val is not None:
                range_size = max_val - min_val + 1
                bits_needed = (range_size - 1).bit_length()
                value = value - min_val  # Offset encoding
            else:
                # Default to minimum bits needed
                if value < 0:
                    # Two's complement encoding
                    bits_needed = (abs(value) - 1).bit_length() + 1
                else:
                    bits_needed = value.bit_length() if value > 0 else 1

            # Encode the value
            self._bitstream.write_bits(value, bits_needed)

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

    def decode_integer(self,
                      min_val: Optional[int] = None,
                      max_val: Optional[int] = None,
                      size_in_bits: Optional[int] = None) -> DecodeResult:
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

    def encode_enumerated(self, value: int, enum_values: list) -> EncodeResult:
        """Encode an enumerated value"""
        try:
            if value not in enum_values:
                return EncodeResult(
                    success=False,
                    error_code=ERROR_CONSTRAINT_VIOLATION,
                    error_message=f"Value {value} not in enumerated list"
                )

            index = enum_values.index(value)
            bits_needed = (len(enum_values) - 1).bit_length()

            self._bitstream.write_bits(index, bits_needed)

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

    def decode_enumerated(self, enum_values: list) -> DecodeResult:
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

    def encode_null(self) -> EncodeResult:
        """Encode a NULL value (typically no bits)"""
        return EncodeResult(
            success=True,
            error_code=ENCODE_OK,
            encoded_data=self._bitstream.get_data_copy(),
            bits_encoded=0
        )

    def decode_null(self) -> DecodeResult:
        """Decode a NULL value (typically no bits)"""
        return DecodeResult(
            success=True,
            error_code=DECODE_OK,
            decoded_value=None,
            bits_consumed=0
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

    def decode_bit_string(self,
                         min_length: int,
                         max_length: int) -> DecodeResult:
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