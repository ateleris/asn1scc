
from asn1python import *
from typing import *
import BasicTypes
from enum import Enum
from dataclasses import dataclass, field

from manual_clean_reference.general import Asn1Base
from src.asn1python import Codec

ERR_TC_2_1_DISTRIBUTEONOFFDEVICECOMMANDS_ONOFFDEVICEADDRESSES: int = 4126  # (SIZE(1 .. maxTC-2-1-OnOffDeviceAdressesCount))
DeviceAddress_REQUIRED_BYTES_FOR_ACN_ENCODING: int = 0
DeviceAddress_REQUIRED_BITS_FOR_ACN_ENCODING: int = 0

class DeviceAddress_Enum(Enum):
    addr0 = 1

@dataclass(frozen=True)
class DeviceAddress(Asn1Base):
    val: DeviceAddress_Enum = DeviceAddress_Enum.addr0

    def is_constraint_valid(self):
        return isinstance(val, DeviceAddress_Enum)
        # ODER: return val == DeviceAddress_Enum.addr0

    def encode(self, codec: Codec):
        res = self.is_constraint_valid()
        if res:
            codec.encode_integer(self.val.value, 0, 0)
        return res

    @classmethod
    def decode(cls, codec: Codec):
        int_val = codec.decodeConstrainedPosWholeNumber(0,0)
        v = DeviceAddress_Enum(int_val)
        instance = cls(val=v)
        res = instance.is_constraint_valid()
        if res:
            return instance
        return res

    @classmethod
    def decode_pure(cls, codec: Codec):
        cpy = codec.copy()
        return DeviceAddress.decode(cpy)


# ERR_DEVICEADDRESS: int = 4111  # addr0
#
#
# ERR_ACN_ENCODE_DEVICEADDRESS: int = 4114  #
# DeviceAddress_REQUIRED_BYTES_FOR_ACN_ENCODING: int = 0
# DeviceAddress_REQUIRED_BITS_FOR_ACN_ENCODING: int = 0
#
# ERR_ACN_DECODE_DEVICEADDRESS: int = 4115  #

@dataclass(frozen=True)
class TC_2_1_DistributeOnOffDeviceCommands_onOffDeviceAddresses:
    nCount: int = 0  # remnant from C -> we don't need nCount actually. -> len(arr)
    arr: List[DeviceAddress] = field(default_factory=list)  # todo: type is generated as int...

    def __post_init__(self):
        if self.nCount > 63 or self.nCount < 1 or self.nCount < len(arr):
            raise ValueError("Something Error!")

    def is_constraint_valid(self):
        ret = self.nCount <= 63 and self.nCount >= 1
        if ret:
            for i in range(self.nCount):
                ret = self.arr[i].is_constraint_valid()  # todo: call on int -> unclear
                if not ret:
                    break
        else:
            ret = Asn1ConstraintValidResult(is_valid=False, error_code=ERR_TC_2_1_DISTRIBUTEONOFFDEVICECOMMANDS_ONOFFDEVICEADDRESSES)
        return ret

    def encode(self, codec: Codec):
        ret = self.is_constraint_valid()
        if ret:
            ret = codec.encode_constraint_whole_number(self.nCount, 1, 63)
            for val in self.arr:
                ret = val.encode(codec)
        return ret

    @classmethod
    def decode(cls, codec: Codec):
        nCount_val = codec.decode_constraint_whole_number(1, 63)
        vals = []
        for i in range(nCount_val):
            vals.append(DeviceAddress.decode(codec))
        instance = cls(nCount=nCount_val, arr=vals)
        ret = instance.is_constraint_valid()
        if ret:
            return instance
        return ret

    @classmethod
    def decode_pure(cls, codec: Codec):
        cpy = codec.copy()
        return TC_2_1_DistributeOnOffDeviceCommands_onOffDeviceAddresses.decode(cpy)


@dataclass(frozen=True)
class TC_2_1_DistributeOnOffDeviceCommands:
    onOffDeviceAddresses: TC_2_1_DistributeOnOffDeviceCommands_onOffDeviceAddresses

    #
    # ERR_TC_2_1_DISTRIBUTEONOFFDEVICECOMMANDS_ONOFFDEVICEADDRESSES_ELM_2: int = 4121  #
    #
    # ERR_TC_2_1_DISTRIBUTEONOFFDEVICECOMMANDS: int = 4131  #
    #
    # TC_2_1_DistributeOnOffDeviceCommands_REQUIRED_BYTES_FOR_ACN_ENCODING: int = 1
    # TC_2_1_DistributeOnOffDeviceCommands_REQUIRED_BITS_FOR_ACN_ENCODING: int = 6
    #
    # ERR_ACN_DECODE_TC_2_1_DISTRIBUTEONOFFDEVICECOMMANDS: int = 4135  #
    #
    # ERR_ACN_DECODE_TC_2_1_DISTRIBUTEONOFFDEVICECOMMANDS_ONOFFDEVICEADDRESSES: int = 4130  #
    #
    # ERR_ACN_DECODE_TC_2_1_DISTRIBUTEONOFFDEVICECOMMANDS_ONOFFDEVICEADDRESSES_ELM_2: int = 4125  #
    #
    # maxTC_2_1_OnOffDeviceAdressesCount: int = 63 # variables:172# variables_python PrintValueAssignment

    def is_constraint_valid(self) -> Union[int, Asn1SccError]:
        return self.onOffDeviceAddresses.is_constraint_valid()

    def encode(self, codec: Codec):
        res = self.is_constraint_valid()
        if res:
            res = self.onOffDeviceAddresses.encode(codec)
        return res

    @classmethod
    def decode(cls, codec: Codec):
        addrs = TC_2_1_DistributeOnOffDeviceCommands_onOffDeviceAddresses.decode(codec)
        instance = cls(onOffDeviceAddresses=addrs)
        ret = instance.is_constraint_valid()
        if ret:
            return instance
        return ret

    @classmethod
    def decode_pure(cls, codec: Codec):
        cpy = codec.copy()
        return TC_2_1_DistributeOnOffDeviceCommands.decode(cpy)
