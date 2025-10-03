# """
# Unit tests for integer
#
# Methods to test:
#   - encode_integer
#   - decode_integer
#   - encode_integer_big_endian
# """
import random

from asn1python.acn_encoder import ACNEncoder
from asn1python.acn_decoder import ACNDecoder
from conftest import get_signed_max, get_random_unsigned, get_unsigned_max, get_random_signed, get_signed_min


def _encode_and_decode_integer(acn_encoder: ACNEncoder, input_number: int, bit: int, signed: bool) -> tuple[bool, int]:
    """Helper function to encode and decode a single positive integer value.

    Returns:
        Tuple of (success, decoded_value)
    """
    if signed:
        max_val = get_signed_max(bit)
        min_val = get_signed_min(bit)
    else:
        max_val = get_unsigned_max(bit)
        min_val = 0

    encoded_res = acn_encoder.encode_integer(input_number, min_val, max_val, bit)
    if not encoded_res.success:
        return False, 0

    acn_decoder: ACNDecoder = acn_encoder.get_decoder()
    decoded_res = acn_decoder.decode_integer(min_val, max_val, bit)

    if not decoded_res.success:
        return False, 0

    return True, decoded_res.decoded_value


def _encode_and_decode_integers(acn_encoder: ACNEncoder, input_numbers: list[int], bit: int, signed: bool) -> tuple[bool, list[int]]:
    """Helper function to encode and decode multiple positive integer values.

    Returns:
        Tuple of (success, decoded_values_list)
    """
    if signed:
        max_val = get_signed_max(bit)
        min_val = get_signed_min(bit)
    else:
        max_val = get_unsigned_max(bit)
        min_val = 0
    # Encode all values first
    for input_number in input_numbers:
        encoded_res = acn_encoder.encode_integer(input_number, min_val, max_val, bit)
        if not encoded_res.success:
            return False, []

    # Decode all values
    acn_decoder: ACNDecoder = acn_encoder.get_decoder()
    decoded_values = []

    for _ in range(len(input_numbers)):
        decoded_res = acn_decoder.decode_integer(min_val, max_val, bit)
        if not decoded_res.success:
            return False, []
        decoded_values.append(decoded_res.decoded_value)

    return True, decoded_values


def _test_single_integer(acn_encoder: ACNEncoder, input_number: int, bit: int, signed: bool) -> None:
    """Helper function to test encoding/decoding of a single positive integer value."""
    success, decoded_value = _encode_and_decode_integer(acn_encoder, input_number, bit, signed)
    assert success, f"Encoding/decoding failed for input {input_number}"

    print(f"Input: {input_number}, decoded {decoded_value}, Passed: {input_number == decoded_value}")
    assert input_number == decoded_value


def _test_multiple_integers(acn_encoder: ACNEncoder, input_numbers: list[int], bit: int, signed: bool) -> None:
    """Helper function to test encoding/decoding of multiple positive integer values."""
    success, decoded_values = _encode_and_decode_integers(acn_encoder, input_numbers, bit, signed)
    assert success, f"Encoding/decoding failed for input {input_numbers}"

    print(f"Input: {input_numbers}, decoded {decoded_values}, Passed: {input_numbers == decoded_values}")
    assert input_numbers == decoded_values


def test_enc_dec_integer_single_value_unsigned(acn_encoder: ACNEncoder, seed: int, bit: int, signed: bool) -> None:
    if signed:
        input_number = get_random_signed(bit)
    else:
        input_number: int = get_random_unsigned(bit)
    _test_single_integer(acn_encoder, input_number, bit, signed)

def test_enc_dec_integer_multiple_values(acn_encoder: ACNEncoder, seed: int, bit: int, signed: bool) -> None:
    input_numbers: list[int] = []
    for i in range(random.randint(3, 10)):
        if signed:
            input_numbers.append(get_random_signed(bit))
        else:
            input_numbers.append(get_random_unsigned(bit))

    _test_multiple_integers(acn_encoder, input_numbers, bit, signed)


def test_enc_dec_integer_zero(acn_encoder: ACNEncoder, seed: int, bit: int, signed: bool) -> None:
    input_number: int = 0
    _test_single_integer(acn_encoder, input_number, bit, signed)


def test_enc_dec_integer_max_value(acn_encoder: ACNEncoder, seed: int, bit: int, signed: bool) -> None:
    if signed:
        input_number: int = get_signed_max(bit)
    else:
        input_number: int = get_unsigned_max(bit)
    _test_single_integer(acn_encoder, input_number, bit, False)


def test_enc_dec_integer_exceed_max_value(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
        input_number: int = get_unsigned_max(bit) + 1
        encoded_res = acn_encoder.encode_integer(input_number, 0, get_unsigned_max(bit), bit)
        assert not encoded_res.success

        input_number: int = get_signed_max(bit) + 1
        encoded_res = acn_encoder.encode_integer(input_number, get_signed_min(bit), get_signed_max(bit), bit)
        assert not encoded_res.success