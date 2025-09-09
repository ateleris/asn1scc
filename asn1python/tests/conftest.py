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