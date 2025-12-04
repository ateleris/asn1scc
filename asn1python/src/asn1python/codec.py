"""
ASN.1 Python Runtime Library - Base Codec Framework

This module provides the base codec framework for ASN.1 encoding/decoding operations.
"""

from nagini_contracts.contracts import *
from abc import abstractmethod
from typing import Optional, Type, TypeVar, Generic, List
# from dataclasses import dataclass
from enum import IntEnum
from .bitstream import BitStream, BitStreamError
from .asn1_types import Asn1Exception
from .segment import Segment


class ErrorCode():
    """Error codes for encoding/decoding operations"""
    SUCCESS = 0
    INSUFFICIENT_DATA = 1
    INVALID_VALUE = 2
    CONSTRAINT_VIOLATION = 3
    BUFFER_OVERFLOW = 4
    UNSUPPORTED_OPERATION = 5

# Constants for common error codes
# ENCODE_OK = ErrorCode.SUCCESS
# DECODE_OK = ErrorCode.SUCCESS
# ERROR_INSUFFICIENT_DATA = ErrorCode.INSUFFICIENT_DATA
# ERROR_INVALID_VALUE = ErrorCode.INVALID_VALUE
# ERROR_CONSTRAINT_VIOLATION = ErrorCode.CONSTRAINT_VIOLATION
# ERROR_BUFFER_OVERFLOW = ErrorCode.BUFFER_OVERFLOW
# ERROR_UNSUPPORTED_OPERATION = ErrorCode.UNSUPPORTED_OPERATION


# @dataclass
# class EncodeResult:
#     """Result of an encoding operation"""
#     success: bool
#     error_code: ErrorCode
#     encoded_data: Optional[bytearray] = None
#     bits_encoded: int = 0
#     error_message: Optional[str] = None

#     def __bool__(self) -> bool:
#         return self.success


# TDVal = TypeVar('TDVal')

# @dataclass
# class DecodeResult(Generic[TDVal]):
#     """Result of a decoding operation"""
#     success: bool
#     error_code: ErrorCode
#     decoded_value: Optional[TDVal] = None
#     bits_consumed: int = 0
#     error_message: Optional[str] = None

#     def __bool__(self) -> bool:
#         return self.success


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

    @Predicate
    def codec_predicate(self) -> bool:
        return (Acc(self._bitstream) and self._bitstream.bitstream_invariant() and self._bitstream.segments_predicate(self.buffer))
        

    def __init__(self, buffer: bytearray) -> None:
        Requires(Acc(bytearray_pred(buffer), 1/20))
        Ensures(Acc(bytearray_pred(buffer), 1/20))
        Ensures(self.codec_predicate())
        self._bitstream = BitStream(buffer)
        
        Fold(self.codec_predicate())

    # def copy(self) -> T:
    #     """Creates and returns a copy of this codec instance"""
    #     bit_index = self._bitstream.current_used_bits
    #     new_codec = self._construct(self._bitstream.get_data_copy())
    #     new_codec._bitstream.set_bit_index(bit_index)
    #     return new_codec

    @classmethod
    @abstractmethod
    def of_size(cls, buffer_byte_size: int = 1024 * 1024) -> T:
        """Create a new codec with a buffer of length buffer_byte_size."""
        pass

    @classmethod
    @abstractmethod
    def _construct(cls, buffer: bytearray) -> T:
        pass
    
    def reset_bitstream(self):
        Requires(self.codec_predicate())
        Ensures(self.codec_predicate())
        Ensures(self.bit_index == 0)
        Ensures(self.segments == Old(self.segments))
        Ensures(self.segments_read_index == Old(self.segments_read_index))
        self._bitstream.reset()
    
    # def get_bitstream_buffer(self) -> bytearray:
    #     return self._bitstream.get_data()

    @property
    def bit_index(self) -> int:
        """
        Get the current bit position in the bitstream.

        Matches C: BitStream.currentBit + BitStream.currentByte * 8
        Matches Scala: BitStream.bitIndex
        Used by: ACN for tracking position, calculating sizes

        Returns:
            Current bit position (0-based index)
        """
        Requires(Rd(self.codec_predicate()))
        Unfold(Rd(self.codec_predicate()))
        return self._bitstream.current_used_bits
    
    #region Ghost
    
    @property
    def buffer(self) -> PByteSeq:
        Requires(Rd(self.codec_predicate()))
        Unfold(Rd(self.codec_predicate()))
        return self._bitstream.buffer()        
    
    @property
    def segments(self) -> PSeq[Segment]:
        Requires(Rd(self.codec_predicate()))
        Unfold(Rd(self.codec_predicate()))
        return self._bitstream.segments
    
    @property
    def segments_read_index(self) -> int:
        Requires(Rd(self.codec_predicate()))
        Unfold(Rd(self.codec_predicate()))
        return self._bitstream.segments_read_index
    
    #endregion