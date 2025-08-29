
from asn1python import *
from PUS_2_1 import *


def DeviceAddress_ACN_enc_dec(pVal: DeviceAddress, filename: str) -> Union[int, Asn1SccError]:
    decodedPDU: DeviceAddress = DeviceAddress()

    codec = ACNCodec(int(DeviceAddress_REQUIRED_BYTES_FOR_ACN_ENCODING))

    res = DeviceAddress_ACN_Encode(pVal, codec, True)
    if isinstance(res, Asn1SccError):
        # test_cases_python.stg 35
        return Asn1SccError(1)

    codec.reset_bitstream()
    # Decode value
    res = DeviceAddress_ACN_Decode(codec)

    if isinstance(res, Asn1SccError):
        # test_cases_python.stg 45
        return Asn1SccError(2)
    decodedPDU = res
    # test_cases_python JoinItems
    # test_cases_python.stg:107
    # test_cases_python Codec_validate_output
    # test_cases_python.stg:80
    # validate decoded data
    res = DeviceAddress_IsConstraintValid(decodedPDU)

    if isinstance(res, Asn1SccError):
        # test_cases_python.stg 68
        return Asn1SccError(3)
    # test_cases_python JoinItems
    # test_cases_python.stg:107
    # test_cases_python Codec_compare_input_with_output
    # test_cases_python.stg:88
    if not DeviceAddress_Equal(pVal, decodedPDU):
        # test_cases_python.stg 74
        return Asn1SccError(4)
    # test_cases_python JoinItems
    # test_cases_python.stg:107
    # test_cases_python Codec_write_bitstreamToFile
    # test_cases_python.stg:99
    codec.reset_bitstream()
    with open(f"{filename}.dat", "wb") as fp:
        fp.write(codec.get_bitstream_buffer())

    # test_cases_python.stg 119
    return ret