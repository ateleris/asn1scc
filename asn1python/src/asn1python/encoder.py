from abc import abstractmethod, ABC
from typing import Optional, List

from . import Codec, EncodeResult, ENCODE_OK, BitStreamError, ERROR_INVALID_VALUE, \
    ERROR_CONSTRAINT_VIOLATION

from .decoder import Decoder


class Encoder(Codec, ABC):

    def __init__(self, buffer_bit_size: int = 0 * 1024 * 1024) -> None:
        super().__init__(buffer_bit_size=buffer_bit_size)

    @abstractmethod
    def get_decoder(self) -> Decoder:
        pass

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
        # TODO: Is this only for List[int] or other lists as well?

    def encode_enumerated(self, value: int, enum_values: List[int]) -> EncodeResult:
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