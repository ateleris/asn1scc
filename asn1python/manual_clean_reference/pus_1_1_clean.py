
from asn1python import *
from typing import *
import BasicTypes
from enum import Enum
from dataclasses import dataclass, field

from src.asn1python import Asn1Error
from src.asn1python.asn1_types import Asn1Base


# codec extract

@dataclass(frozen=True)
class Asn1ConstraintValidResult:
    is_valid: bool
    error_code: int = 0

    def __bool__(self):
        return self.is_valid

    def __post_init__(self):
        if not self.is_valid and self.error_code <= 0:
            raise Exception("Error code must be set to a number > 0 if the constraint is not valid.")

        if self.is_valid and self.error_code > 0:
            raise Exception("No error code must be set if the constraint is valid.")
# end

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