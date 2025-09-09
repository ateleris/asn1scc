from asn1python.acn_encoder import ACNEncoder
from asn1python.acn_decoder import ACNDecoder
import pytest
import random

@pytest.fixture
def acn_encoder() -> ACNEncoder:
    acnEncoder = ACNEncoder()
    return acnEncoder

sizes = [1, 2, 3, (4, 15), 6, (8, 255), 10, 12, (16, 65_535), (32, 4_294_967_295) 48, 64]

def test_enc_dec_int_positive_integer_const_size_single_value(acn_encoder: ACNEncoder) -> None:
    for size in sizes:
        # TODO: adjust for different bit sizes
        input: int = random.randint(0, 4_294_967_295)
        size_in_bits = 32
        encoded_res = acn_encoder.enc_int_positive_integer_const_size(input, size_in_bits)

        acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())

        decoded_res = acn_decoder.dec_int_positive_integer_const_size(size_in_bits)
        print(f"Input: {input}, decoded {decoded_res.decoded_value}, Passed: {input == decoded_res.decoded_value}")
        assert input == decoded_res.decoded_value

def test_enc_dec_int_positive_integer_const_size_multiple_values(acn_encoder: ACNEncoder) -> None:
    numbers = random.randint(3, 10)
    input: list[int] = []
    for i in range(numbers):
        input.append(random.randint(0, 65_535))
    size_in_bits = 16
    for i in input:
        encoded_res = acn_encoder.enc_int_positive_integer_const_size(i, size_in_bits)

    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())

    decoded_res = []
    for _ in range(len(input)):
        decoded_res.append(acn_decoder.dec_int_positive_integer_const_size(size_in_bits).decoded_value)
    print(f"Input: {input}, decoded {decoded_res}, Passed: {input == decoded_res}")
    assert input == decoded_res

def test_enc_dec_int_positive_integer_const_size_zero(acn_encoder: ACNEncoder) -> None:
    input: int = 0
    size_in_bits = 1
    encoded_res = acn_encoder.enc_int_positive_integer_const_size(input, size_in_bits)
    print(encoded_res)

    print(f"Buffer: {acn_encoder.get_bitstream_buffer()}, len {len(acn_encoder.get_bitstream_buffer()) * 8}")

    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())

    decoded_res = acn_decoder.dec_int_positive_integer_const_size(size_in_bits)
    print(decoded_res)
    print(f"Input: {input}, decoded {decoded_res.decoded_value}, Passed: {input == decoded_res.decoded_value}")
    assert input == decoded_res.decoded_value

def test_enc_dec_int_positive_integer_const_size_max_value_32(acn_encoder: ACNEncoder) -> None:
    input: int = 4_294_967_295
    size_in_bits = 32
    encoded_res = acn_encoder.enc_int_positive_integer_const_size(input, size_in_bits)

    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())

    decoded_res = acn_decoder.dec_int_positive_integer_const_size(size_in_bits)
    print(f"Input: {input}, decoded {decoded_res.decoded_value}, Passed: {input == decoded_res.decoded_value}")
    assert input == decoded_res.decoded_value

def test_enc_dec_int_positive_integer_const_size_exceed_max_value_32(acn_encoder: ACNEncoder) -> None:
    input: int = 4_294_967_296
    size_in_bits = 32
    encoded_res = acn_encoder.enc_int_positive_integer_const_size(input, size_in_bits)

    assert not encoded_res.success
    # acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())
    #
    # decoded_res = acn_decoder.dec_int_positive_integer_const_size(size_in_bits)
    # print(f"Input: {input}, decoded {decoded_res.decoded_value}, Passed: {input == decoded_res.decoded_value}")
    # assert input == decoded_res.decoded_value
