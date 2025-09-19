import random

from asn1python.acn_decoder import ACNDecoder
from asn1python.acn_encoder import ACNEncoder
from conftest import get_min_uint_ascii, get_max_uint_ascii, get_random_uint_ascii


def _encode_and_decode_unsigned_integer_as_ascii(acn_encoder: ACNEncoder, input_number: int) -> tuple[bool, int]:
    """Helper function to encode and decode a unsigned integer value as ascii.

    Returns:
        Tuple of (success, decoded_value)
    """
    encoded_res = acn_encoder.enc_uint_ascii_var_size_length_embedded(input_number)
    if not encoded_res.success:
        return False, 0

    acn_decoder: ACNDecoder = acn_encoder.get_decoder()
    decoded_res = acn_decoder.dec_uint_ascii_var_size_length_embedded()

    if not decoded_res.success:
        return False, 0

    return True, decoded_res.decoded_value


def _encode_and_decode_multiple_unsigned_integers_as_ascii(acn_encoder: ACNEncoder, input_numbers: list[int]) -> tuple[bool, list[int]]:
    """Helper function to encode and decode multiple unsigned integer values as ascii.

    Returns:
        Tuple of (success, decoded_values_list)
    """
    # Encode all values first
    for input_number in input_numbers:
        encoded_res = acn_encoder.enc_uint_ascii_var_size_length_embedded(input_number)
        if not encoded_res.success:
            return False, []

    # Decode all values
    acn_decoder: ACNDecoder = acn_encoder.get_decoder()
    decoded_values = []

    for _ in range(len(input_numbers)):
        decoded_res = acn_decoder.dec_uint_ascii_var_size_length_embedded()
        if not decoded_res.success:
            return False, []
        decoded_values.append(decoded_res.decoded_value)

    return True, decoded_values


def _test_single_unsigned_integer(acn_encoder: ACNEncoder, input_number: int) -> None:
    """Helper function to test encoding/decoding of a single positive integer value."""
    success, decoded_value = _encode_and_decode_unsigned_integer_as_ascii(acn_encoder, input_number)
    assert success, f"Encoding/decoding failed for input {input_number}"

    print(f"Input: {input_number}, decoded {decoded_value}, Passed: {input_number == decoded_value}")
    assert input_number == decoded_value


def _test_multiple_unsigned_integers(acn_encoder: ACNEncoder, input_numbers: list[int]) -> None:
    """Helper function to test encoding/decoding of multiple positive integer values."""
    success, decoded_values = _encode_and_decode_multiple_unsigned_integers_as_ascii(acn_encoder, input_numbers)
    assert success, f"Encoding/decoding failed for input {input_numbers}"

    print(f"Input: {input_numbers}, decoded {decoded_values}, Passed: {input_numbers == decoded_values}")
    assert input_numbers == decoded_values


def test_enc_dec_uint_ascii_const_size_single_value(acn_encoder: ACNEncoder, seed: int, byte: int) -> None:
    input_number: int = get_random_uint_ascii(byte)
    _test_single_unsigned_integer(acn_encoder, input_number)


def test_enc_dec_uint_ascii_const_size_multiple_values(acn_encoder: ACNEncoder, seed: int, byte: int) -> None:
    input_numbers: list[int] = []
    for i in range(random.randint(3, 10)):
        input_numbers.append(get_random_uint_ascii(byte))

    _test_multiple_unsigned_integers(acn_encoder, input_numbers)

def test_enc_dec_uint_ascii_const_size_zero(acn_encoder: ACNEncoder, seed: int) -> None:
    input_number: int = 0
    _test_single_unsigned_integer(acn_encoder, input_number)

def test_enc_dec_uint_ascii_const_size_max_value(acn_encoder: ACNEncoder, seed: int, byte: int) -> None:
    input_number: int = get_max_uint_ascii(byte)
    _test_single_unsigned_integer(acn_encoder, input_number)

def test_enc_dec_uint_ascii_const_size_min_value(acn_encoder: ACNEncoder, seed: int, byte: int) -> None:
    input_number: int = get_min_uint_ascii(byte)
    _test_single_unsigned_integer(acn_encoder, input_number)

def test_enc_dec_uint_ascii_const_size_exceed_max_value(acn_encoder: ACNEncoder, seed: int, byte: int) -> None:
    input_number: int = get_max_uint_ascii(byte) + 1
    _test_single_unsigned_integer(acn_encoder, input_number)

def test_enc_dec_uint_ascii_const_size_exceed_min_value(acn_encoder: ACNEncoder, seed: int, byte: int) -> None:
    input_number: int = get_min_uint_ascii(byte) - 1
    encoded_res = acn_encoder.enc_uint_ascii_var_size_length_embedded(input_number)
    assert not encoded_res.success
