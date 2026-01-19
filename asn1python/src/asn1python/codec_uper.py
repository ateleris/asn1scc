from .decoder import Decoder
from .encoder import Encoder

from nagini_contracts.contracts import *

class UPERDecoder(Decoder):
    """
    UPER decoder implementation.

    This decoder provides flexible binary decoding for ASN.1 types
    following custom UPER encoding rules to support legacy protocols.
    """
    pass

class UPEREncoder(Encoder):
    """
    UPER encoder implementation.

    This encoder provides flexible binary encoding for ASN.1 types
    following custom UPER encoding rules to support legacy protocols.
    """

    def get_decoder(self) -> UPERDecoder:
        Requires(Acc(self.codec_predicate(), 1/20))
        Ensures(Acc(self.codec_predicate(), 1/20))
        Ensures(isinstance(Result(), UPERDecoder))
        Ensures(Result().codec_predicate())
        Ensures(Result().index_zero())
        Ensures(Result().buffer == self.buffer)
        Ensures(Result().segments == self.segments)
        
        instance = UPERDecoder.from_codec(self)
        assert isinstance(instance, UPERDecoder)
        return instance