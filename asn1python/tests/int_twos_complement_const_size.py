import random

from asn1python.acn_decoder import ACNDecoder
from asn1python.acn_encoder import ACNEncoder
from conftest import get_random_signed, get_signed_max, get_signed_min

# TODO: we have always to test positive and negative numbers in each pass.

def test_enc_dec_int_twos_complement_const_size_single_value(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_number: int = get_random_signed(bit)
    encoded_res = acn_encoder.enc_int_twos_complement_const_size(input_number, bit)
    assert encoded_res.success

    acn_decoder: ACNDecoder = acn_encoder.get_decoder()

    decoded_res = acn_decoder.dec_int_twos_complement_const_size(bit)
    assert decoded_res.success
    print(f"Input: {input_number}, decoded {decoded_res.decoded_value}, Passed: {input_number == decoded_res.decoded_value}")
    assert input_number == decoded_res.decoded_value

def test_enc_dec_int_twos_complement_const_size_multiple_values(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_numbers: list[int] = []
    for i in range(random.randint(3, 10)):
        input_numbers.append(get_random_signed(bit))
    for i in input_numbers:
        encoded_res = acn_encoder.enc_int_twos_complement_const_size(i, bit)
        assert encoded_res.success

    acn_decoder: ACNDecoder = acn_encoder.get_decoder()

    decoded_res = []
    for _ in range(len(input_numbers)):
        decoded_res.append(acn_decoder.dec_int_twos_complement_const_size(bit).decoded_value)
    print(f"Input: {input_numbers}, decoded {decoded_res}, Passed: {input_numbers == decoded_res}")
    assert input_numbers == decoded_res

def test_enc_dec_int_twos_complement_const_size_zero(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_number: int = 0

    encoded_res = acn_encoder.enc_int_twos_complement_const_size(input_number, bit)
    assert encoded_res.success
    acn_decoder: ACNDecoder = acn_encoder.get_decoder()
    decoded_res = acn_decoder.dec_int_twos_complement_const_size(bit)
    print(f"Input: {input_number}, decoded {decoded_res.decoded_value}, Passed: {input_number == decoded_res.decoded_value}")
    assert input_number == decoded_res.decoded_value

def test_enc_dec_int_twos_complement_const_size_max_value(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_number: int = get_signed_max(bit)

    encoded_res = acn_encoder.enc_int_twos_complement_const_size(input_number, bit)
    assert encoded_res.success
    acn_decoder: ACNDecoder = acn_encoder.get_decoder()
    decoded_res = acn_decoder.dec_int_twos_complement_const_size(bit)
    print(f"Input: {input_number}, decoded {decoded_res.decoded_value}, Passed: {input_number == decoded_res.decoded_value}")
    assert input_number == decoded_res.decoded_value
    ## TODO: add - case

def test_enc_dec_int_twos_complement_const_size_exceed_max_value(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_number: int = get_signed_max(bit) + 1
    encoded_res = acn_encoder.enc_int_twos_complement_const_size(input_number, bit)
    assert not encoded_res.success

    ## TODO: add - case
