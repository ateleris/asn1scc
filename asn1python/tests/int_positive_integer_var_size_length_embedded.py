import random

from asn1python.acn_decoder import ACNDecoder
from asn1python.acn_encoder import ACNEncoder

def test_enc_dec_int_positive_integer_var_size_length_embedded_single_value(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    max_int_size = (2**bit)-1
    input_number: int = random.randint(1, max_int_size)

    _ = acn_encoder.enc_int_positive_integer_var_size_length_embedded(input_number)

    acn_decoder: ACNDecoder = acn_encoder.get_decoder()

    decoded_res = acn_decoder.dec_int_positive_integer_var_size_length_embedded()
    print(f"Input: {input_number}, decoded {decoded_res.decoded_value}, Passed: {input_number == decoded_res.decoded_value}")
    assert input_number == decoded_res.decoded_value

def test_enc_dec_int_positive_integer_var_size_length_embedded_multiple_values(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    max_int_size = (2 ** bit) - 1
    input_numbers: list[int] = []
    for i in range(random.randint(3, 10)):
        input_numbers.append(random.randint(0, max_int_size))
    for i in input_numbers:
        _ = acn_encoder.enc_int_positive_integer_var_size_length_embedded(i,)

    acn_decoder: ACNDecoder = acn_encoder.get_decoder()

    decoded_res = []
    for _ in range(len(input_numbers)):
        decoded_res.append(acn_decoder.dec_int_positive_integer_var_size_length_embedded().decoded_value)
    print(f"Input: {input_numbers}, decoded {decoded_res}, Passed: {input_numbers == decoded_res}")
    assert input_numbers == decoded_res

def test_enc_dec_enc_dec_int_positive_integer_var_size_length_embedded_zero(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_number: int = 0

    _ = acn_encoder.enc_int_positive_integer_var_size_length_embedded(input_number)
    acn_decoder: ACNDecoder = acn_encoder.get_decoder()
    decoded_res = acn_decoder.dec_int_positive_integer_var_size_length_embedded()
    print(f"Input: {input_number}, decoded {decoded_res.decoded_value}, Passed: {input_number == decoded_res.decoded_value}")
    assert input_number == decoded_res.decoded_value

def test_enc_dec_enc_dec_int_positive_integer_var_size_length_embedded_max_value(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_number: int = (2 ** bit) - 1

    _ = acn_encoder.enc_int_positive_integer_var_size_length_embedded(input_number)
    acn_decoder: ACNDecoder = acn_encoder.get_decoder()
    decoded_res = acn_decoder.dec_int_positive_integer_var_size_length_embedded()
    print(f"Input: {input_number}, decoded {decoded_res.decoded_value}, Passed: {input_number == decoded_res.decoded_value}")
    assert input_number == decoded_res.decoded_value

def test_enc_dec_enc_dec_int_positive_integer_var_size_length_embedded_exceed_max_value(acn_encoder: ACNEncoder, seed: int, bit: int) -> None:
    input_number: int = (2 ** bit)
    encoded_res = acn_encoder.enc_int_positive_integer_var_size_length_embedded(input_number)
    # Should still work, it has variable size!
    assert encoded_res.success