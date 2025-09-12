import math
import pytest
import random
from random import choice
from string import printable
from asn1python.acn_encoder import ACNEncoder

@pytest.fixture
def acn_encoder() -> ACNEncoder:
    return ACNEncoder()

@pytest.fixture
def seed() -> int:
    seed = random.randint(0, 1_000_000)
    random.seed(seed)
    return seed

def pytest_generate_tests(metafunc):
    if "bit" in metafunc.fixturenames:
        metafunc.parametrize("bit", [1, 2, 3, 4, 6, 8, 10, 12, 16, 32, 48, 64])
    if "nibble" in metafunc.fixturenames:
        metafunc.parametrize("nibble", [1, 2, 3, 4, 5, 6])
    if "max_length" in metafunc.fixturenames:
        metafunc.parametrize("max_length", [1, 2, 3, 4, 5, 6, 7, 8, 16, 32, 64, 128, 256, 512, 1024])
    if "null_characters" in metafunc.fixturenames:
        metafunc.parametrize("null_characters", [bytes(1), bytes(2), bytes(4), bytes(8)])

# Utility functions for integer range calculations
def get_unsigned_max(bits: int) -> int:
    """Get maximum value for unsigned integer with given bit size."""
    return (2 ** bits) - 1

def get_unsigned_min(bits: int) -> int:
    """Get minimum value for unsigned integer with given bit size."""
    return 0

def get_signed_max(bits: int) -> int:
    """Get maximum value for signed integer with given bit size."""
    return (2 ** (bits - 1)) - 1

def get_signed_min(bits: int) -> int:
    """Get minimum value for signed integer with given bit size."""
    return -(2 ** (bits - 1))

def get_random_unsigned(bits: int) -> int:
    """Get random unsigned integer for given bit size."""
    return random.randint(get_unsigned_min(bits), get_unsigned_max(bits))

def get_random_signed(bits: int) -> int:
    """Get random signed integer for given bit size."""
    return random.randint(get_signed_min(bits), get_signed_max(bits))

def get_random_float(precision: str = "double", positive_only: bool = False, negative_only: bool = False) -> float:
    """Get random IEEE 754 floating-point number for testing (normal values only).
    
    Args:
        precision: "single" for 32-bit or "double" for 64-bit precision testing
        positive_only: If True, return only positive values
        negative_only: If True, return only negative values
        
    Returns:
        Random normal float value (positive, negative, or both based on parameters)
    """
    # Define ranges based on precision
    if precision == "single":
        # IEEE 754 single precision ranges
        min_normal = 1.175494e-38
        max_normal = 3.402823e+38
    else:  # double precision (default)
        # IEEE 754 double precision ranges  
        min_normal = 2.2250738585072014e-308
        max_normal = 1.7976931348623157e+308
    
    # Generate positive value
    value = random.uniform(min_normal, max_normal / 1e100)
    
    # Apply sign based on parameters
    if negative_only:
        return -value
    elif positive_only:
        return value
    else:
        # Random sign
        return value if random.choice([True, False]) else -value

def get_small_float(precision: str = "double", positive_only: bool = False, negative_only: bool = False) -> float:
    """Get random small IEEE 754 floating-point number (near zero).
    
    Args:
        precision: "single" for 32-bit or "double" for 64-bit precision testing
        positive_only: If True, return only positive values
        negative_only: If True, return only negative values
        
    Returns:
        Random small float value (positive, negative, or both based on parameters)
    """
    # Define ranges based on precision
    if precision == "single":
        # IEEE 754 single precision ranges
        min_normal = 1.175494e-38
        min_subnormal = 1.401298e-45
    else:  # double precision (default)
        # IEEE 754 double precision ranges  
        min_normal = 2.2250738585072014e-308
        min_subnormal = 5e-324
    
    # Generate positive small value
    small_value = random.uniform(min_subnormal, min_normal)
    
    # Apply sign based on parameters
    if negative_only:
        return -small_value
    elif positive_only:
        return small_value
    else:
        # Random sign
        return small_value if random.choice([True, False]) else -small_value

def get_big_float(precision: str = "double", positive: bool = True) -> float:
    """Get random large IEEE 754 floating-point number (near limits).
    
    Args:
        precision: "single" for 32-bit or "double" for 64-bit precision testing
        positive: If True, return only positive values
        
    Returns:
        Random large float value (positive, negative, or both based on parameters)
    """
    # Define ranges based on precision
    if precision == "single":
        # IEEE 754 single precision ranges
        max_normal = 3.402823e+38
    else:  # double precision (default)
        # IEEE 754 double precision ranges  
        max_normal = 1.7976931348623157e+308
    
    # Generate positive large value
    large_value = random.uniform(max_normal / 1e10, max_normal)
    
    # Apply sign based on parameters

    if positive:
        return large_value
    else:
        return -large_value

def get_zero_and_special_floats() -> list[float]:
    """Get zero or special IEEE 754 floating-point values.
    
    Returns:
        Random special float value (±0, ±∞, NaN, unity values, constants)
    """
    return [
        0.0, -0.0,              # Positive and negative zero
        float('inf'),           # Positive infinity
        float('-inf'),          # Negative infinity
        1.0, -1.0,             # Simple unity values
        math.pi, -math.pi,      # Mathematical constants
        math.e, -math.e
    ]

def get_random_max_length_digits(length: int) -> int:
    """Get random integer between 0 and maximum value with given number of digits.
    
    Args:
        length: Number of digits (e.g., 4 means max value is 9999)
        
    Returns:
        Random integer between 0 and (10^length - 1)
        
    Examples:
        get_random_max_digits(1) -> random int between 0 and 9
        get_random_max_digits(4) -> random int between 0 and 9999
    """
    if length <= 0:
        raise ValueError("Length must be positive")
    
    max_value = (10 ** length) - 1
    return random.randint(0, max_value)

def get_nibble_max_digit(length: int) -> int:
    if length <= 0:
        raise ValueError("Length must be positive")

    return (10 ** length) - 1

def get_random_string_random_length(max_length: int) -> str:
    return get_random_string(random.randint(1, max_length))

def get_random_string(length: int) -> str:
    # Use printable ASCII characters (letters, digits, punctuation, whitespace)
    # Excludes control characters for easier debugging
    return ''.join(choice(printable.rstrip()) for _ in range(length))

def get_null_terminator_string_random_size(length: int) -> str:
    return ''.join('\0' for _ in range(random.randint(1, length)))

def get_null_terminator_string(length: int) -> str:
    return ''.join('\0' for _ in range(length))