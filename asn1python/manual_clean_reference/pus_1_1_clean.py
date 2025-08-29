
from asn1python import *
from typing import *
import BasicTypes
from enum import Enum
from dataclasses import dataclass, field

from src.asn1python import Asn1Error
from src.asn1python.asn1_types import Asn1Base


@dataclass(frozen=True)
class TM_1_1_SuccessfulAcceptanceVerificationReport(Asn1Base):

    request_ID: VerificationRequest.VerificationRequest_ID = VerificationRequest.VerificationRequest_ID()

    def is_constraint_valid(self) -> Asn1ConstraintValidResult:
        return self.request_ID.is_constraint_valid()

    def encode(self, codec: Codec):
        res = self.is_constraint_valid()
        if res:
            self.request_ID.encode(codec)
        else:
            pass
            # todo: what do we do if constraint is valid?

    @classmethod
    def decode(cls, codec: Codec):
        request_ID = VerificationRequest.VerificationRequest_ID.decode(codec)
        instance = cls(request_ID=request_ID)
        res = instance.is_constraint_valid()
        if res:
            return instance
        else:
            pass
            # todo: raise error?


    def TM_1_1_SuccessfulAcceptanceVerificationReport_ACN_Decode_pure(codec: ACNCodec) -> Tuple[ACNCodec, Union[TM_1_1_SuccessfulAcceptanceVerificationReport, Asn1SccError]]:
        cpy = codec.copy()
        res = TM_1_1_SuccessfulAcceptanceVerificationReport_ACN_Decode(cpy)
        return cpy, res