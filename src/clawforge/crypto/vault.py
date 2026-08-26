"""AES-256-GCM Secret Vault for key encryption at rest."""

import os
from contextlib import contextmanager
from typing import Generator

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import structlog

logger = structlog.get_logger(__name__)


class VaultError(Exception):
    """Raised when vault decryption fails."""


class Vault:
    """AES-256-GCM encryption vault for private key at rest."""

    def __init__(self, vault_key: str) -> None:
        """Initialize vault with encryption key.

        Args:
            vault_key: 32-byte hex key for AES-256-GCM encryption.
        """
        try:
            key_bytes = bytes.fromhex(vault_key)
            if len(key_bytes) != 32:
                raise ValueError("Vault key must be 32 bytes (64 hex characters)")
            self._key = key_bytes
        except ValueError as e:
            raise VaultError(f"Invalid vault key: {e}") from e

        logger.info("Vault initialized")

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: String to encrypt.

        Returns:
            Hex-encoded ciphertext with nonce prefix.
        """
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

        result = nonce.hex() + ciphertext.hex()

        logger.debug(
            "Data encrypted",
            plaintext_length=len(plaintext),
            ciphertext_length=len(result),
        )

        return result

    def decrypt(self, encrypted: str) -> str:
        """Decrypt ciphertext using AES-256-GCM.

        Args:
            encrypted: Hex-encoded ciphertext with nonce prefix.

        Returns:
            Decrypted plaintext string.

        Raises:
            VaultError: If decryption fails.
        """
        try:
            data = bytes.fromhex(encrypted)
            nonce = data[:12]
            ciphertext = data[12:]

            aesgcm = AESGCM(self._key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            return plaintext.decode()
        except Exception as e:
            raise VaultError(f"Decryption failed: {e}") from e

    @contextmanager
    def decrypt_in_memory(self, encrypted: str) -> Generator[str, None, None]:
        """Context manager that yields decrypted key and zeroizes after use.

        Args:
            encrypted: Hex-encoded encrypted key.

        Yields:
            Decrypted plaintext.

        Raises:
            VaultError: If decryption fails.
        """
        decrypted = self.decrypt(encrypted)
        try:
            yield decrypted
        finally:
            # Zeroize the decrypted key from memory
            decrypted = "0" * len(decrypted)
            del decrypted

    def rotate_key(self, new_vault_key: str) -> None:
        """Rotate the vault encryption key.

        Args:
            new_vault_key: New 32-byte hex key.

        Raises:
            VaultError: If new key is invalid.
        """
        try:
            new_key_bytes = bytes.fromhex(new_vault_key)
            if len(new_key_bytes) != 32:
                raise ValueError("Vault key must be 32 bytes (64 hex characters)")
            self._key = new_key_bytes
            logger.info("Vault key rotated")
        except ValueError as e:
            raise VaultError(f"Invalid new vault key: {e}") from e


def encrypt_private_key(private_key: str, vault_key: str) -> str:
    """Encrypt a private key for storage.

    Args:
        private_key: Ethereum private key.
        vault_key: 32-byte hex encryption key.

    Returns:
        Encrypted private key.
    """
    vault = Vault(vault_key)
    return vault.encrypt(private_key)


def decrypt_private_key(encrypted_key: str, vault_key: str) -> str:
    """Decrypt a private key from storage.

    Args:
        encrypted_key: Encrypted private key.
        vault_key: 32-byte hex encryption key.

    Returns:
        Decrypted private key.

    Raises:
        VaultError: If decryption fails.
    """
    vault = Vault(vault_key)
    return vault.decrypt(encrypted_key)
