# Error classes
class Asn1Exception(Exception):
    """Base class for ASN.1 runtime errors"""
    pass

class Asn1ValueOutOfRangeException(Asn1Exception):
    """Exception raised when an ASN.1 value is out of range"""
    pass

class Asn1ValueUnexpectedEndOfDataException(Asn1Exception):
    """Exception raised when an ASN.1 value is out of range"""
    pass

class Asn1InvalidValueException(Asn1Exception):
    """Raised when a value is outside the valid range for a type"""
    pass

class Asn1OverflowException(Asn1Exception):
    """Raised when an arithmetic operation would cause overflow"""
    pass

class Asn1TestcaseError(Asn1Exception):
    """Base Class for Testcase Errors"""
    pass

class Asn1TestcaseEncodeFailedError(Asn1TestcaseError):
    """Raised when the encoding fails in a testcase"""
    pass

class Asn1TestcaseDecodeFailedError(Asn1TestcaseError):
    """Raised when the decoding fails in a testcase"""
    pass

class Asn1TestcaseConstraintFailedError(Asn1TestcaseError):
    """Raised when the constraint validation fails in a testcase"""
    pass

class Asn1TestcaseDifferentResultError(Asn1TestcaseError):
    """Raised when the decoding of the encoded object yields a different result in a testcase"""
    pass