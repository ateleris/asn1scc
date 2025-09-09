import pytest
import random
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
