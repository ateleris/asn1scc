import asn1python.codec_acn
import pytest
from asn1python.codec_acn import *

@pytest.fixture
def acn_codec() -> ACNCodec:
    acnCodec = asn1python.codec_acn.ACNCodec()
    return acnCodec

def test_test(acn_codec):
    print(acn_codec.enc_int_positive_integer_const_size(5, 32))