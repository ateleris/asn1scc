from typing import List, Optional

from asn1python import Codec, DecodeResult, ERROR_INSUFFICIENT_DATA, DECODE_OK, BitStreamError, ERROR_INVALID_VALUE, \
    ERROR_CONSTRAINT_VIOLATION


class Decoder(Codec):

    def __init__(self, buffer: bytearray) -> None:
        super().__init__(buffer=buffer)

    def decode_boolean(self) -> DecodeResult[bool]:
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

    def decode_integer(self,
                      min_val: Optional[int] = None,
                      max_val: Optional[int] = None,
                      size_in_bits: Optional[int] = None) -> DecodeResult[int]:
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

    def decode_enumerated(self, enum_values: List[int]) -> DecodeResult:
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
