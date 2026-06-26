# asn1python/tests/test_xer_decoder_cursor.py
from asn1python.xer_encoder import XEREncoder
from asn1python.xer_decoder import XERDecoder

def _dec(xml: str) -> XERDecoder:
    return XERDecoder.from_buffer(bytearray(xml.encode("utf-8")))

def test_peek_and_read_text():
    d = _dec("<age>42</age>")
    assert d.peek_start_tag() == "age"
    assert d.read_text_element("age") == "42"

def test_next_start_element_is_does_not_consume():
    d = _dec("<seq><x>1</x></seq>")
    d.expect_start("seq")
    assert d.next_start_element_is("x") is True
    assert d.next_start_element_is("x") is True   # still not consumed
    assert d.read_text_element("x") == "1"
    d.expect_end("seq")

def test_get_decoder_roundtrip_from_encoder():
    e = XEREncoder.of_size(); e.encode_integer("age", 7, 0)
    d = e.get_decoder()
    assert d.read_text_element("age") == "7"
