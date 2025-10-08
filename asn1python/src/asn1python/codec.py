"""
ASN.1 Python Runtime Library - Base Codec Framework

This module provides the base codec framework for ASN.1 encoding/decoding operations.
"""

from abc import abstractmethod
from typing import Optional, Type, TypeVar, Generic, List
from dataclasses import dataclass
from enum import IntEnum
from .bitstream import BitStream, BitStreamError
from .asn1_types import Asn1Exception


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

    def __bool__(self) -> bool:
        return self.success


TDVal = TypeVar('TDVal')

@dataclass
class DecodeResult(Generic[TDVal]):
    """Result of a decoding operation"""
    success: bool
    error_code: ErrorCode
    decoded_value: Optional[TDVal] = None
    bits_consumed: int = 0
    error_message: Optional[str] = None

    def __bool__(self) -> bool:
        return self.success


class CodecError(Asn1Exception):
    """Base class for codec errors"""
    pass


T = TypeVar('T', bound='Codec')
class Codec(Generic[T]):
    """
    Base class for ASN.1 codecs.

    This class provides common functionality for all ASN.1 encoding rules
    including UPER, ACN, XER, and BER.
    """

    def __init__(self, buffer_bit_size: int = 8 * 1024 * 1024, buffer: Optional[bytearray] = None) -> None:
        if buffer is not None:
            buffer_bit_size = len(buffer) * 8

        assert buffer_bit_size > 0, "Codec buffer_size must be greater than zero"
        self._max_bits = buffer_bit_size  # 1MB default max size
        self._bitstream = BitStream(size_in_bits=self._max_bits, data=buffer)

    def copy(self) -> T:
        """Creates and returns a copy of this codec instance"""
        current_data = self._bitstream.get_data_copy()
        current_position = self._bitstream.current_bit_position

        new_codec = self._construct(self._max_bits)
        new_codec._bitstream.reset()
        if len(current_data) > 0:
            new_codec._bitstream.write_bytes(current_data)
        new_codec._bitstream.set_bit_position(current_position)

        return new_codec

    @abstractmethod
    def _construct(self, buffer_bit_size: int) -> T:
        pass

    def reset_bitstream(self):
        self._bitstream.reset()
    
    def get_bitstream_buffer(self) -> bytearray:
        return self._bitstream.get_data()