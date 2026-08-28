import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("CLAW_EARN_WALLET", "0x0000000000000000000000000000000000000000")
os.environ.setdefault("CLAW_EARN_PRIVATE_KEY", "0x" + "1" * 64)

from clawforge.config import Settings


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_settings(tmp_data_dir):
    return Settings(
        CLAW_EARN_WALLET="0x0000000000000000000000000000000000000000",
        CLAW_EARN_PRIVATE_KEY="0x" + "1" * 64,
        CLAW_VAULT_KEY="test_vault_key_32_bytes_long!!",
        MEMORY_PATH=str(tmp_data_dir / "memory"),
        AUDIT_PATH=str(tmp_data_dir / "audit"),
        ECONOMY_PATH=str(tmp_data_dir / "economy"),
    )
