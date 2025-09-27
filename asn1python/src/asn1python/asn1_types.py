"""
ASN.1 Python Runtime Library - Core Types

This module provides sized integer types and ASN.1 semantic types
that match the behavior of the C and Scala runtime libraries.
"""

import ctypes
from codecs import Codec
from typing import List
from enum import Enum
import abc
from dataclasses import dataclass
from functools import total_ordering

# Error classes
class Asn1Error(Exception):
    """Base class for ASN.1 runtime errors"""
    pass


class Asn1ValueError(Asn1Error):
    """Raised when a value is outside the valid range for a type"""
    pass


class Asn1OverflowError(Asn1Error):
    """Raised when an arithmetic operation would cause overflow"""
    pass

@dataclass(frozen=True)
class Asn1ConstraintValidResult:
    is_valid: bool
    error_code: int = 0
    message: str = ""

    def __bool__(self):
        return self.is_valid

    def __post_init__(self):
        if not self.is_valid and self.error_code <= 0:
            raise Exception("Error code must be set to a number > 0 if the constraint is not valid.")

        if self.is_valid and self.error_code > 0:
            raise Exception("No error code must be set if the constraint is valid.")

class Asn1Base(abc.ABC):
    from .encoder import Encoder
    from .decoder import Decoder

    @abc.abstractmethod
    def is_constraint_valid(self):
        pass

    @abc.abstractmethod
    def encode(self, codec: Encoder, check_constraints: bool = True):
        pass

    @classmethod
    def decode(cls, codec: Decoder, check_constraints: bool = True):
        pass

    @staticmethod
    def decode_pure(codec: Decoder, check_constraints: bool = True):
        pass


# Integer types using ctypes for automatic range validation and conversion

# Unsigned integer types
UInt8 = ctypes.c_uint8    # 8-bit unsigned integer (0 to 255)
UInt16 = ctypes.c_uint16  # 16-bit unsigned integer (0 to 65535)  
UInt32 = ctypes.c_uint32  # 32-bit unsigned integer (0 to 4294967295)
UInt64 = ctypes.c_uint64  # 64-bit unsigned integer (0 to 18446744073709551615)

# Signed integer types
Int8 = ctypes.c_int8      # 8-bit signed integer (-128 to 127)
Int16 = ctypes.c_int16    # 16-bit signed integer (-32768 to 32767)
Int32 = ctypes.c_int32    # 32-bit signed integer (-2147483648 to 2147483647)
Int64 = ctypes.c_int64    # 64-bit signed integer (-9223372036854775808 to 9223372036854775807)

# Byte type aliases
UByte = ctypes.c_uint8    # Unsigned byte (0 to 255)
Byte = ctypes.c_int8      # Signed byte (-128 to 127)
    

# ASN.1 compiler size types
Asn1SccSint32 = Int32
Asn1SccUint32 = UInt32
Asn1SccSint64 = UInt32
Asn1SccUint64 = UInt64
Asn1SccUint = int
Asn1SccSint = int

# ASN.1 semantic types - simplified to match C/Scala approach

# ASN.1 Real type - matches Scala "type asn1Real = Double" and C "typedef double asn1Real"
Asn1Real = float

# ASN.1 Boolean type - matches primitive bool in C and Scala
@total_ordering
class Asn1Boolean(Asn1Base):
    """
    ASN.1 Boolean wrapper that behaves as closely as possible to Python's bool.
    """
    __slots__ = ("_val",)

    def __init__(self, val):
        self._val = bool(val)

    # --- Core protocol ---
    def __bool__(self):
        return self._val

    def __repr__(self):
        return f"Asn1Boolean({self._val})"

    def __str__(self):
        return str(self._val)

    # --- Equality / ordering ---
    def __eq__(self, other):
        return self._val == bool(other)

    def __lt__(self, other):
        return self._val < bool(other)

    def __hash__(self):
        return hash(self._val)

    # --- Boolean operators ---
    def __and__(self, other):
        return Asn1Boolean(self._val & bool(other))

    def __or__(self, other):
        return Asn1Boolean(self._val | bool(other))

    def __xor__(self, other):
        return Asn1Boolean(self._val ^ bool(other))

    def __invert__(self):
        return Asn1Boolean(not self._val)

    # --- Attribute delegation (for any method/properties bool has) ---
    def __getattr__(self, name):
        return getattr(self._val, name)

    # --- Conversion helpers ---
    @property
    def value(self) -> bool:
        """Explicit access to the inner bool."""
        return self._val

    # --- Stub-Implementations of Asn1Base Methods ---
    def is_constraint_valid(self):
        raise NotImplementedError()

    def encode(self, codec: Codec):
        raise NotImplementedError()

class NullType(Asn1Base):
    """
    ASN.1 NullType wrapper that behaves as closely as possible to Python's None.
    Always falsy, always equal to None, singleton instance.
    """
    __slots__ = ()

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # --- Core protocol ---
    def __bool__(self):
        return False

    def __repr__(self):
        return "None"

    def __str__(self):
        return "None"

    # --- Equality ---
    def __eq__(self, other):
        return other is None or isinstance(other, NullType)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(None)

    # --- Pickling / copy compatibility ---
    def __reduce__(self):
        return (NullType, ())

    # --- Prevent accidental mutation / attributes ---
    def __setattr__(self, name, value):
        raise AttributeError(f"'{self.__class__.__name__}' object has no attributes")

    def __delattr__(self, name):
        raise AttributeError(f"'{self.__class__.__name__}' object has no attributes")
    
    def is_constraint_valid(self):
        # todo: evaluate if NullType.is_constraint_valid should return True or False
        return False
    
    def encode(self, codec: Codec):
        return
    
    def decode(cls, codec: Codec):
        return NullType()
    
    def decode_pure(cls, codec: Codec):
        return NullType()


# Floating point types for different precisions
Asn1Real32 = float  # matches C typedef float asn1Real32
Asn1Real64 = float  # matches C typedef double asn1Real64

# ASCII character type
ASCIIChar = int  # matches UByte in Scala

# Constants to match C and Scala implementations
OBJECT_IDENTIFIER_MAX_LENGTH = 20

# Bit manipulation constants
NO_OF_BITS_IN_BYTE = 8
NO_OF_BITS_IN_SHORT = 16
NO_OF_BITS_IN_INT = 32
NO_OF_BITS_IN_LONG = 64

# Error codes to match C implementation
ERR_INSUFFICIENT_DATA = 101
ERR_INCORRECT_PER_STREAM = 102
ERR_INVALID_CHOICE_ALTERNATIVE = 103
ERR_INVALID_ENUM_VALUE = 104
ERR_INVALID_XML_FILE = 200
ERR_INVALID_BER_FILE = 201
ERR_BER_LENGTH_MISMATCH = 202

# Error codes from Scala implementation
NOT_INITIALIZED_ERR_CODE = 1337
ERR_INVALID_ENUM_VALUE_SCALA = 2805
FAILED_READ_ERR_CODE = 5400

# Utility functions to match C and Scala implementations
def int2uint(v: int) -> int:
    """Convert signed integer to unsigned (matches C and Scala function)"""
    return ctypes.c_uint64(v).value

# def uint2int(v: int, uint_size_in_bytes: int) -> int:
#     """Convert unsigned integer to signed (matches C and Scala function)"""
#     match uint_size_in_bytes:
#         case 1: return ctypes.c_int8(v).value
#         case 2: return ctypes.c_int16(v).value
#         case 4: return ctypes.c_int32(v).value
#         case 8: return ctypes.c_int64(v).value
#         case _: raise ValueError(f"Unsupported size: {uint_size_in_bytes}")

# TODO: OctetString_equal might be required for isvalid_python:394
# def OctetString_equal(...):

# TODO: BitString_equal is required for isvalid_python:402
# def BitString_equal(...):


# Time types
class Asn1TimeZone:
    """ASN.1 timezone information"""
    __slots__ = ('sign', 'hours', 'mins')

    def __init__(self, sign: int, hours: int, mins: int):
        """
        Initialize timezone information.
        
        Args:
            sign: -1 or +1
            hours: Hours offset from UTC
            mins: Minutes offset from UTC
        """
        if sign not in (-1, 1):
            raise Asn1ValueError(f"Timezone sign must be -1 or +1, got {sign}")
        if not (0 <= hours <= 23):
            raise Asn1ValueError(f"Timezone hours must be 0-23, got {hours}")
        if not (0 <= mins <= 59):
            raise Asn1ValueError(f"Timezone minutes must be 0-59, got {mins}")
        
        self.sign = sign
        self.hours = hours
        self.mins = mins

    def __str__(self) -> str:
        sign_str = "+" if self.sign == 1 else "-"
        return f"{sign_str}{self.hours:02d}:{self.mins:02d}"

    def __repr__(self) -> str:
        return f"Asn1TimeZone({self.sign}, {self.hours}, {self.mins})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Asn1TimeZone):
            return self.sign == other.sign and self.hours == other.hours and self.mins == other.mins
        return False


class Asn1Date:
    """ASN.1 DATE type"""
    __slots__ = ('years', 'months', 'days')

    def __init__(self, years: int, months: int, days: int):
        """
        Initialize date.
        
        Args:
            years: Year value
            months: Month value (1-12)
            days: Day value (1-31)
        """
        if not (1 <= months <= 12):
            raise Asn1ValueError(f"Month must be 1-12, got {months}")
        if not (1 <= days <= 31):
            raise Asn1ValueError(f"Day must be 1-31, got {days}")
        
        self.years = years
        self.months = months
        self.days = days

    def __str__(self) -> str:
        return f"{self.years:04d}-{self.months:02d}-{self.days:02d}"

    def __repr__(self) -> str:
        return f"Asn1Date({self.years}, {self.months}, {self.days})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Asn1Date):
            return self.years == other.years and self.months == other.months and self.days == other.days
        return False


class Asn1LocalTime:
    """ASN.1 TIME (local time) type"""
    __slots__ = ('hours', 'mins', 'secs', 'fraction')

    def __init__(self, hours: int, mins: int, secs: int, fraction: int = 0):
        """
        Initialize local time.
        
        Args:
            hours: Hours (0-23)
            mins: Minutes (0-59)
            secs: Seconds (0-59)
            fraction: Fractional seconds (implementation-specific precision)
        """
        if not (0 <= hours <= 23):
            raise Asn1ValueError(f"Hours must be 0-23, got {hours}")
        if not (0 <= mins <= 59):
            raise Asn1ValueError(f"Minutes must be 0-59, got {mins}")
        if not (0 <= secs <= 59):
            raise Asn1ValueError(f"Seconds must be 0-59, got {secs}")
        if fraction < 0:
            raise Asn1ValueError(f"Fraction must be non-negative, got {fraction}")
        
        self.hours = hours
        self.mins = mins
        self.secs = secs
        self.fraction = fraction

    def __str__(self) -> str:
        if self.fraction == 0:
            return f"{self.hours:02d}:{self.mins:02d}:{self.secs:02d}"
        else:
            return f"{self.hours:02d}:{self.mins:02d}:{self.secs:02d}.{self.fraction}"

    def __repr__(self) -> str:
        return f"Asn1LocalTime({self.hours}, {self.mins}, {self.secs}, {self.fraction})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Asn1LocalTime):
            return (self.hours == other.hours and self.mins == other.mins and 
                   self.secs == other.secs and self.fraction == other.fraction)
        return False


class Asn1UtcTime:
    """ASN.1 TIME (UTC time) type"""
    __slots__ = ('hours', 'mins', 'secs', 'fraction')

    def __init__(self, hours: int, mins: int, secs: int, fraction: int = 0):
        """
        Initialize UTC time.
        
        Args:
            hours: Hours (0-23)
            mins: Minutes (0-59)
            secs: Seconds (0-59)
            fraction: Fractional seconds (implementation-specific precision)
        """
        if not (0 <= hours <= 23):
            raise Asn1ValueError(f"Hours must be 0-23, got {hours}")
        if not (0 <= mins <= 59):
            raise Asn1ValueError(f"Minutes must be 0-59, got {mins}")
        if not (0 <= secs <= 59):
            raise Asn1ValueError(f"Seconds must be 0-59, got {secs}")
        if fraction < 0:
            raise Asn1ValueError(f"Fraction must be non-negative, got {fraction}")
        
        self.hours = hours
        self.mins = mins
        self.secs = secs
        self.fraction = fraction

    def __str__(self) -> str:
        if self.fraction == 0:
            return f"{self.hours:02d}:{self.mins:02d}:{self.secs:02d}Z"
        else:
            return f"{self.hours:02d}:{self.mins:02d}:{self.secs:02d}.{self.fraction}Z"

    def __repr__(self) -> str:
        return f"Asn1UtcTime({self.hours}, {self.mins}, {self.secs}, {self.fraction})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Asn1UtcTime):
            return (self.hours == other.hours and self.mins == other.mins and 
                   self.secs == other.secs and self.fraction == other.fraction)
        return False


class Asn1TimeWithTimeZone:
    """ASN.1 TIME (time with time zone) type"""
    __slots__ = ('hours', 'mins', 'secs', 'fraction', 'tz')

    def __init__(self, hours: int, mins: int, secs: int, fraction: int, tz: Asn1TimeZone):
        """
        Initialize time with timezone.
        
        Args:
            hours: Hours (0-23)
            mins: Minutes (0-59)
            secs: Seconds (0-59)
            fraction: Fractional seconds (implementation-specific precision)
            tz: Timezone information
        """
        if not (0 <= hours <= 23):
            raise Asn1ValueError(f"Hours must be 0-23, got {hours}")
        if not (0 <= mins <= 59):
            raise Asn1ValueError(f"Minutes must be 0-59, got {mins}")
        if not (0 <= secs <= 59):
            raise Asn1ValueError(f"Seconds must be 0-59, got {secs}")
        if fraction < 0:
            raise Asn1ValueError(f"Fraction must be non-negative, got {fraction}")
        assert isinstance(tz, Asn1TimeZone)
        
        self.hours = hours
        self.mins = mins
        self.secs = secs
        self.fraction = fraction
        self.tz = tz

    def __str__(self) -> str:
        time_str = f"{self.hours:02d}:{self.mins:02d}:{self.secs:02d}"
        if self.fraction != 0:
            time_str += f".{self.fraction}"
        return time_str + str(self.tz)

    def __repr__(self) -> str:
        return f"Asn1TimeWithTimeZone({self.hours}, {self.mins}, {self.secs}, {self.fraction}, {self.tz!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Asn1TimeWithTimeZone):
            return (self.hours == other.hours and self.mins == other.mins and 
                   self.secs == other.secs and self.fraction == other.fraction and 
                   self.tz == other.tz)
        return False


class Asn1DateLocalTime:
    """ASN.1 DATE-TIME (local time) type"""
    __slots__ = ('date', 'time')

    def __init__(self, date: Asn1Date, time: Asn1LocalTime):
        """
        Initialize date-time with local time.
        
        Args:
            date: Date component
            time: Local time component
        """
        assert isinstance(date, Asn1Date)
        assert isinstance(time, Asn1LocalTime)
        
        self.date = date
        self.time = time

    def __str__(self) -> str:
        return f"{self.date}T{self.time}"

    def __repr__(self) -> str:
        return f"Asn1DateLocalTime({self.date!r}, {self.time!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Asn1DateLocalTime):
            return self.date == other.date and self.time == other.time
        return False


class Asn1DateUtcTime:
    """ASN.1 DATE-TIME (UTC time) type"""
    __slots__ = ('date', 'time')

    def __init__(self, date: Asn1Date, time: Asn1UtcTime):
        """
        Initialize date-time with UTC time.
        
        Args:
            date: Date component
            time: UTC time component
        """
        assert isinstance(date, Asn1Date)
        assert isinstance(time, Asn1UtcTime)

        self.date = date
        self.time = time

    def __str__(self) -> str:
        return f"{self.date}T{self.time}"

    def __repr__(self) -> str:
        return f"Asn1DateUtcTime({self.date!r}, {self.time!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Asn1DateUtcTime):
            return self.date == other.date and self.time == other.time
        return False


class Asn1DateTimeWithTimeZone:
    """ASN.1 DATE-TIME (time with time zone) type"""
    __slots__ = ('date', 'time')

    def __init__(self, date: Asn1Date, time: Asn1TimeWithTimeZone):
        """
        Initialize date-time with timezone.
        
        Args:
            date: Date component
            time: Time with timezone component
        """
        assert isinstance(date, Asn1Date)
        assert isinstance(time, Asn1TimeWithTimeZone)
        
        self.date = date
        self.time = time

    def __str__(self) -> str:
        return f"{self.date}T{self.time}"

    def __repr__(self) -> str:
        return f"Asn1DateTimeWithTimeZone({self.date!r}, {self.time!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Asn1DateTimeWithTimeZone):
            return self.date == other.date and self.time == other.time
        return False


# Timezone class enum to match Scala implementation
class Asn1TimeZoneClass(Enum):
    """ASN.1 timezone class enumeration"""
    Asn1TC_LocalTimeStamp = "Asn1TC_LocalTimeStamp"
    Asn1TC_UtcTimeStamp = "Asn1TC_UtcTimeStamp"
    Asn1TC_LocalTimeTZStamp = "Asn1TC_LocalTimeTZStamp"