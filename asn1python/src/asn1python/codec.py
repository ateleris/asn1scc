"""
ASN.1 Python Runtime Library - Base Codec Framework

This module provides the base codec framework for ASN.1 encoding/decoding operations.
"""

from abc import ABC
from typing import Optional, TypeVar, Generic
from dataclasses import dataclass
from enum import IntEnum

from asn1_types import Asn1Exception
from bitstream import BitStream, BitStreamError
from segment import Segment

from nagini_contracts.contracts import *


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


@dataclass(frozen=True)
class EncodeResult:
    """Result of an encoding operation"""
    success: bool
    error_code: ErrorCode
    bits_encoded: int = 0
    error_message: Optional[str] = None

    @Pure
    def __bool__(self) -> bool:
        return self.success


TDVal = TypeVar('TDVal')
@dataclass(frozen=True)
class DecodeResult(Generic[TDVal]):
    """Result of a decoding operation"""
    success: bool
    error_code: ErrorCode
    decoded_value: Optional[TDVal] = None
    bits_consumed: int = 0
    error_message: Optional[str] = None

    @Pure
    def __bool__(self) -> bool:
        return self.success

class CodecError(Asn1Exception):
    """Base class for codec errors"""
    pass

class Codec(ABC):
    """
    Base class for ASN.1 codecs.

    This class provides common functionality for all ASN.1 encoding rules
    including UPER, ACN, XER, and BER.
    """

    @Predicate
    def codec_predicate(self) -> bool:
        return (Acc(self._bitstream) and self._bitstream.bitstream_invariant() and self._bitstream.segments_predicate(self._bitstream.buffer()))
        
    @Pure
    def index_zero(self) -> bool:
        Requires(Rd(self.codec_predicate()))
        return self.bit_index == 0 and self.segments_read_index == 0

    def __init__(self, bitstream: BitStream) -> None:
        """
        Creates a new Codec from the provided Bitstream
        """
        Requires(Acc(bitstream.bitstream_invariant(), 1/20) and Acc(bitstream.segments_predicate(bitstream.buffer()), 1/20))
        Ensures(Acc(bitstream.bitstream_invariant(), 1/20) and Acc(bitstream.segments_predicate(bitstream.buffer()), 1/20))
        Ensures(self.codec_predicate())
        Ensures(self.index_zero())
        Ensures(self.buffer is bitstream.buffer())
        Ensures(self.segments is bitstream.segments)
        
        self._bitstream = BitStream.from_bitstream(bitstream)        
        Fold(self.codec_predicate())

    @classmethod
    def from_codec(cls, codec: 'Codec') -> 'Codec':
        Requires(Acc(codec.codec_predicate(), 1/20))
        Ensures(Acc(codec.codec_predicate(), 1/20))
        Ensures(isinstance(Result(), cls))
        Ensures(Result().codec_predicate())
        Ensures(Result().index_zero())
        Ensures(Result().buffer is codec.buffer)
        Ensures(Result().segments is codec.segments)
        
        Unfold(Acc(codec.codec_predicate(), 1/20))
        instance = cls(codec._bitstream)
        Fold(Acc(codec.codec_predicate(), 1/20))
        return instance

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> 'Codec':
        Requires(Acc(bytearray_pred(buffer), 1/20))
        Ensures(Acc(bytearray_pred(buffer), 1/20))
        Ensures(ToByteSeq(buffer) is Old(ToByteSeq(buffer)))
        Ensures(isinstance(Result(), cls))
        Ensures(Result().codec_predicate())
        Ensures(Result().index_zero())
        Ensures(Result().buffer is ToByteSeq(buffer))
        Ensures(len(Result().segments) == 0)
        
        return cls(BitStream(buffer))

    @classmethod
    def of_size(cls, buffer_byte_size: int = 1024 * 1024) -> 'Codec':
        """Create a new codec with a buffer of length buffer_byte_size."""
        Ensures(isinstance(Result(), cls))
        Ensures(Result().codec_predicate())
        Ensures(Result().index_zero())
        Ensures(len(Result().buffer) == buffer_byte_size)
        Ensures(len(Result().segments) == 0)
        
        return cls.from_buffer(bytearray(buffer_byte_size))

#     # def copy(self) -> 'Codec':
#     #     """Creates and returns a copy of this codec instance"""
#     #     @Requires(Acc(self.codec_predicate(), 1/20))
#     #     @Ensures(Acc(self.codec_predicate(), 1/20))
#     #     @Ensures(isinstance(Result(), T))
#     #     @Ensures(Codec.codec_predicate(Result()))

#     #     bit_index = self._bitstream.current_used_bits
#     #     new_codec = self._construct(self._bitstream.get_data_copy())
#     #     new_codec._bitstream.set_bit_index(bit_index)
#     #     return new_codec
    
#     # def get_bitstream_buffer(self) -> bytearray:
#     #     return self._bitstream.get_data()

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
    
    @property
    def remaining_bits(self) -> int:
        Requires(Rd(self.codec_predicate()))
        Unfold(Rd(self.codec_predicate()))
        return self._bitstream.remaining_bits

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