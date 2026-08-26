"""Proof generation for task completion."""

import hashlib
import time
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from ..models import Proof


class ProofGenerator:
    def __init__(self, private_key: str):
        self._account = Account.from_key(private_key)

    def generate(self, task_id: str, output: str, on_chain: bool = False) -> Proof:
        if on_chain:
            # Use Keccak-256 for on-chain proofs (Ethereum compatible)
            data = f"claw:{task_id}:{output}"
            keccak_hex = Web3.keccak(data.encode()).hex()
            hash_value = "0x" + keccak_hex if not keccak_hex.startswith("0x") else keccak_hex
        else:
            data = f"claw:{task_id}:{output}"
            hash_value = hashlib.sha256(data.encode()).hexdigest()

        message = f"Proof for task {task_id}: {hash_value}"
        signed = self._account.sign_message(encode_defunct(text=message))

        return Proof(
            task_id=task_id,
            output_hash=hash_value,
            timestamp=time.time(),
            agent_signature=signed.signature.hex(),
            metadata={"on_chain": on_chain, "agent_address": self._account.address},
        )
