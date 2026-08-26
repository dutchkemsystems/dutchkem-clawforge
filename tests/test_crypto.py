import pytest
from clawforge.crypto.signer import Signer
from clawforge.crypto.hasher import sha256_hash, keccak256_hash, compute_hash, compute_task_proof_hash, compute_hash_chain_entry, verify_hash_chain, hash_file_content
from clawforge.crypto.vault import Vault, VaultError, encrypt_private_key, decrypt_private_key
import tempfile
from pathlib import Path


class TestSigner:
    def test_creates_valid_signature(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)
        sig = signer.sign_message("test message")
        assert sig is not None
        assert len(sig) > 0

    def test_signer_rejects_wrong_address(self):
        test_key = "0x" + "1" * 64
        with pytest.raises(ValueError, match="does not match"):
            Signer(test_key, "0x0000000000000000000000000000000000000001")

    def test_signer_address_property(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)
        assert signer.address == account.address

    def test_verify_signature_valid(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)
        sig = signer.sign_message("hello")
        assert signer.verify_signature("hello", sig) is True

    def test_verify_signature_invalid_message(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)
        sig = signer.sign_message("hello")
        assert signer.verify_signature("wrong", sig) is False

    def test_verify_signature_invalid_sig(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)
        assert signer.verify_signature("hello", "ff" * 65) is False

    def test_sign_task_bid(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)
        sig = signer.sign_task_bid("task-1", "50.0")
        assert len(sig) > 0

    def test_sign_proof(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)
        sig = signer.sign_proof("task-1", "abc123hash", "12345")
        assert len(sig) > 0

    def test_sign_settlement(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)
        sig = signer.sign_settlement("task-1", "100.0", "10.0")
        assert len(sig) > 0


class TestHasher:
    def test_sha256_deterministic(self):
        r1 = sha256_hash("test data")
        r2 = sha256_hash("test data")
        assert r1 == r2

    def test_sha256_different_inputs(self):
        assert sha256_hash("a") != sha256_hash("b")

    def test_keccak256_deterministic(self):
        r1 = keccak256_hash("test data")
        r2 = keccak256_hash("test data")
        assert r1 == r2

    def test_keccak256_different_inputs(self):
        assert keccak256_hash("a") != keccak256_hash("b")

    def test_compute_hash_sha256(self):
        assert compute_hash("data", "sha256") == sha256_hash("data")

    def test_compute_hash_keccak256(self):
        assert compute_hash("data", "keccak256") == keccak256_hash("data")

    def test_compute_hash_invalid_algorithm(self):
        with pytest.raises(ValueError, match="Unsupported"):
            compute_hash("data", "md5")

    def test_compute_task_proof_hash(self):
        result = compute_task_proof_hash("t1", "output", "123")
        assert len(result) == 64

    def test_compute_hash_chain_entry(self):
        result = compute_hash_chain_entry("prev_hash", "entry_data")
        assert len(result) == 64

    def test_verify_hash_chain_valid(self):
        e1 = {"prev_hash": "genesis", "hash": "aaa"}
        e2 = {"prev_hash": "aaa", "hash": "bbb"}
        assert verify_hash_chain([e1, e2]) is True

    def test_verify_hash_chain_broken(self):
        e1 = {"prev_hash": "genesis", "hash": "aaa"}
        e2 = {"prev_hash": "wrong", "hash": "bbb"}
        assert verify_hash_chain([e1, e2]) is False

    def test_verify_hash_chain_empty(self):
        assert verify_hash_chain([]) is True

    def test_hash_file_content(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            f.flush()
            result = hash_file_content(f.name)
            assert len(result) == 64


class TestVault:
    def test_encrypt_decrypt_roundtrip(self):
        vault = Vault("ab" * 32)
        encrypted = vault.encrypt("secret data")
        assert vault.decrypt(encrypted) == "secret data"

    def test_encrypted_is_different_each_time(self):
        vault = Vault("ab" * 32)
        e1 = vault.encrypt("same data")
        e2 = vault.encrypt("same data")
        assert e1 != e2

    def test_wrong_key_fails(self):
        v1 = Vault("ab" * 32)
        v2 = Vault("cd" * 32)
        enc = v1.encrypt("secret")
        with pytest.raises(VaultError):
            v2.decrypt(enc)

    def test_invalid_key_length(self):
        with pytest.raises(VaultError):
            Vault("short")

    def test_decrypt_in_memory_context_manager(self):
        vault = Vault("ab" * 32)
        enc = vault.encrypt("my key")
        with vault.decrypt_in_memory(enc) as key:
            assert key == "my key"

    def test_rotate_key(self):
        vault = Vault("ab" * 32)
        enc = vault.encrypt("data")
        vault.rotate_key("cd" * 32)
        with pytest.raises(VaultError):
            vault.decrypt(enc)

    def test_rotate_key_invalid(self):
        vault = Vault("ab" * 32)
        with pytest.raises(VaultError):
            vault.rotate_key("short")

    def test_encrypt_private_key_helper(self):
        enc = encrypt_private_key("0x" + "a" * 64, "ab" * 32)
        result = decrypt_private_key(enc, "ab" * 32)
        assert result == "0x" + "a" * 64

    def test_decrypt_private_key_wrong_key(self):
        enc = encrypt_private_key("0x" + "a" * 64, "ab" * 32)
        with pytest.raises(VaultError):
            decrypt_private_key(enc, "cd" * 32)
