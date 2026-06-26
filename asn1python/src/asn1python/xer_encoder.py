"""
ASN.1 XER (XML Encoding Rules) encoder.

This module provides the XEREncoder for encoding ASN.1 values to XML.
"""

from typing import List
from asn1python.xer_codec import XER_INDENT_UNIT


class XEREncoder:
    """
    XER encoder that builds XML text incrementally.

    XER is text-based, so we accumulate output in a list and join at the end.
    No pre-allocation occurs — the size hint to of_size() is ignored.
    """

    def __init__(self) -> None:
        self._parts: List[str] = []

    @classmethod
    def of_size(cls, buffer_byte_size: int = 0) -> "XEREncoder":
        """
        Create a new XER encoder.

        XER is text: build incrementally, never pre-allocate the worst case.
        The buffer_byte_size hint is ignored.

        Args:
            buffer_byte_size: Ignored; provided for API consistency with other codecs.

        Returns:
            A new XEREncoder instance.
        """
        return cls()

    def write_raw(self, text: str) -> None:
        """
        Write raw text to the encoder.

        Args:
            text: The text to append to the output.
        """
        self._parts.append(text)

    def indent(self, level: int) -> None:
        """
        Write indentation for the given nesting level.

        Args:
            level: The nesting level; each level is 4 spaces.
        """
        if level > 0:
            self._parts.append(XER_INDENT_UNIT * level)

    def get_xml(self) -> str:
        """
        Get the accumulated XML text.

        Returns:
            The complete XML as a string.
        """
        return "".join(self._parts)

    def get_bitstream_buffer(self) -> bytearray:
        """
        Get the XML as a UTF-8 encoded bytearray.

        This allows the existing template layer (e.g., Codec_write_bitstreamToFile)
        to work unchanged by encoding the XML text as bytes.

        Returns:
            The XML encoded as UTF-8 bytes in a bytearray.
        """
        return bytearray(self.get_xml().encode("utf-8"))
