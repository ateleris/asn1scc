from asn1python.acn_encoder import ACNEncoder
from asn1python.acn_decoder import ACNDecoder
import pytest

@pytest.fixture
def acn_encoder() -> ACNEncoder:
    acnEncoder = ACNEncoder()
    return acnEncoder

def test_test(acn_encoder: ACNEncoder) -> None:
    input: int = 5
    size_in_bits = 32
    encoded_res = acn_encoder.enc_int_positive_integer_const_size(input, size_in_bits)
    print(encoded_res)

    print(f"Buffer: {acn_encoder.get_bitstream_buffer()}, len {len(acn_encoder.get_bitstream_buffer()) * 8}")

    acn_decoder = ACNDecoder(acn_encoder.get_bitstream_buffer())

    decoded_res = acn_decoder.dec_int_positive_integer_const_size(size_in_bits)
    print(decoded_res)
    print(f"Input: {input}, decoded {decoded_res.decoded_value}, Passed: {input == decoded_res.decoded_value}")
    assert input, decoded_res.decoded_value
