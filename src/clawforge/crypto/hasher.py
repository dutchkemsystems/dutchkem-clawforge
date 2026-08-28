"""SHA-256 and Keccak-256 hashing utilities."""

import hashlib
from pathlib import Path

from web3 import Web3
import structlog

logger = structlog.get_logger(__name__)


def sha256_hash(data: str) -> str:
    """Compute SHA-256 hash of data."""
    hash_obj = hashlib.sha256(data.encode())
    return hash_obj.hexdigest()


def keccak256_hash(data: str) -> str:
    """Compute Keccak-256 hash of data (Ethereum compatible)."""
    return Web3.keccak(data.encode()).hex()


def compute_hash(data: str, algorithm: str = "sha256") -> str:
    """Compute hash using specified algorithm."""
    if algorithm == "sha256":
        return sha256_hash(data)
    elif algorithm == "keccak256":
        return keccak256_hash(data)
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def compute_task_proof_hash(
    task_id: str,
    output_data: str,
    timestamp: str,
    algorithm: str = "sha256",
) -> str:
    """Compute hash for task proof."""
    proof_data = f"{task_id}:{output_data}:{timestamp}"
    return compute_hash(proof_data, algorithm)


def compute_hash_chain_entry(
    previous_hash: str,
    entry_data: str,
    algorithm: str = "sha256",
) -> str:
    """Compute hash chain entry including previous hash."""
    chain_data = f"{previous_hash}:{entry_data}"
    return compute_hash(chain_data, algorithm)


def verify_hash_chain(
    entries: list[dict[str, str]],
    algorithm: str = "sha256",
) -> bool:
    """Verify integrity of hash chain."""
    if not entries:
        return True

    for i in range(1, len(entries)):
        if entries[i].get("prev_hash") != entries[i - 1].get("hash"):
            logger.warning(
                "Hash chain broken",
                index=i,
                expected=entries[i - 1].get("hash"),
                actual=entries[i].get("prev_hash"),
            )
            return False

    logger.info("Hash chain verified", entries=len(entries))
    return True


def hash_file_content(file_path: str, allowed_dirs: list[str] | None = None) -> str:
    """Compute SHA-256 hash of file content.

    Validates path is a regular file within allowed directories to prevent path traversal.
    """
    resolved = Path(file_path).resolve()
    if not resolved.is_file():
        raise ValueError(f"Not a valid file: {file_path}")

    # Path traversal protection: restrict to allowed directories
    if allowed_dirs:
        in_allowed = any(
            resolved.resolve().is_relative_to(Path(d).resolve()) for d in allowed_dirs
        )
        if not in_allowed:
            raise ValueError(f"Path outside allowed directories: {file_path}")

    sha256 = hashlib.sha256()
    with open(resolved, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
