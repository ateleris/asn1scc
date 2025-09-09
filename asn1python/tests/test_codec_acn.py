import random

from asn1python.acn_decoder import ACNDecoder
from asn1python.acn_encoder import ACNEncoder


def test_enc_dec_int_positive_integer_const_size_single_value(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    max_int_size = (2**bit)-1
    input_number: int = random.randint(1, max_int_size)

    _ = acn_encoder.enc_int_positive_integer_const_size(input_number, bit)

    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())

    decoded_res = acn_decoder.dec_int_positive_integer_const_size(bit)
    print(f"Input: {input_number}, decoded {decoded_res.decoded_value}, Passed: {input_number == decoded_res.decoded_value}")
    assert input_number == decoded_res.decoded_value

def test_enc_dec_int_positive_integer_const_size_multiple_values(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    max_int_size = (2 ** bit) - 1
    input_numbers: list[int] = []
    for i in range(random.randint(3, 10)):
        input_numbers.append(random.randint(0, max_int_size))
    for i in input_numbers:
        _ = acn_encoder.enc_int_positive_integer_const_size(i, bit)

    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())

    decoded_res = []
    for _ in range(len(input_numbers)):
        decoded_res.append(acn_decoder.dec_int_positive_integer_const_size(bit).decoded_value)
    print(f"Input: {input_numbers}, decoded {decoded_res}, Passed: {input_numbers == decoded_res}")
    assert input_numbers == decoded_res

def test_enc_dec_int_positive_integer_const_size_zero(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_number: int = 0

    _ = acn_encoder.enc_int_positive_integer_const_size(input_number, bit)
    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())
    decoded_res = acn_decoder.dec_int_positive_integer_const_size(bit)
    print(f"Input: {input_number}, decoded {decoded_res.decoded_value}, Passed: {input_number == decoded_res.decoded_value}")
    assert input_number == decoded_res.decoded_value

def test_enc_dec_int_positive_integer_const_size_max_value_32(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input: int = (2 ** bit) - 1

    _ = acn_encoder.enc_int_positive_integer_const_size(input, bit)
    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())
    decoded_res = acn_decoder.dec_int_positive_integer_const_size(bit)
    print(f"Input: {input}, decoded {decoded_res.decoded_value}, Passed: {input == decoded_res.decoded_value}")
    assert input == decoded_res.decoded_value

def test_enc_dec_int_positive_integer_const_size_exceed_max_value_32(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_number: int = (2 ** bit)
    encoded_res = acn_encoder.enc_int_positive_integer_const_size(input_number, bit)
    assert not encoded_res.success
