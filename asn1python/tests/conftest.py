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