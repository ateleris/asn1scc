from asn1python.acn_encoder import ACNEncoder
from asn1python.acn_decoder import ACNDecoder
import pytest

@pytest.fixture
def acn_encoder() -> ACNEncoder:
    acnEncoder = ACNEncoder()
    return acnEncoder

def test_enc_dec_int_positive_integer_const_size_single_value(acn_encoder: ACNEncoder) -> None:
    input: int = 5
    size_in_bits = 32
    encoded_res = acn_encoder.enc_int_positive_integer_const_size(input, size_in_bits)
    print(encoded_res)

    print(f"Buffer: {acn_encoder.get_bitstream_buffer()}, len {len(acn_encoder.get_bitstream_buffer()) * 8}")

    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())

    decoded_res = acn_decoder.dec_int_positive_integer_const_size(size_in_bits)
    print(decoded_res)
    print(f"Input: {input}, decoded {decoded_res.decoded_value}, Passed: {input == decoded_res.decoded_value}")
    assert input == decoded_res.decoded_value

def test_enc_dec_int_positive_integer_const_size_multiple_values(acn_encoder: ACNEncoder) -> None:
    input: list[int] = [5, 29, 80]
    size_in_bits = 16
    for i in input:
        encoded_res = acn_encoder.enc_int_positive_integer_const_size(i, size_in_bits)
        print(encoded_res)

    print(f"Buffer: {acn_encoder.get_bitstream_buffer()}, len {len(acn_encoder.get_bitstream_buffer()) * 8}")

    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())

    decoded_res = []
    for _ in range(len(input)):
        decoded_res.append(acn_decoder.dec_int_positive_integer_const_size(size_in_bits).decoded_value)
    print(decoded_res)
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
