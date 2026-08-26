"""EIP-191 CLAW_V2 message signing."""

from typing import Optional

from eth_account import Account
from eth_account.messages import encode_defunct
import structlog

logger = structlog.get_logger(__name__)


class Signer:
    """EIP-191 CLAW_V2 domain-separated message signer."""

    def __init__(self, private_key: str, wallet_address: str) -> None:
        """Initialize signer with private key and wallet address.

        Args:
            private_key: Ethereum private key (hex string).
            wallet_address: Expected wallet address for validation.

        Raises:
            ValueError: If private key doesn't match wallet address.
        """
        self._private_key = private_key
        self._wallet_address = wallet_address
        self._account = Account.from_key(private_key)

        if self._account.address.lower() != wallet_address.lower():
            raise ValueError("Private key does not match wallet address")

        logger.info(
            "Signer initialized",
            wallet=self._wallet_address,
        )

    @property
    def address(self) -> str:
        """Get wallet address."""
        return self._wallet_address

    def sign_message(self, message: str) -> str:
        """Sign message using CLAW_V2 domain separation.

        The message format follows EIP-191:
        "\\x19Ethereum Signed Message:\\n{len(message)}" + message

        Args:
            message: Message to sign.

        Returns:
            Signed message as hex string.
        """
        encode = encode_defunct(text=message)
        signed = self._account.sign_message(encode)

        logger.debug(
            "Message signed",
            wallet=self._wallet_address,
            message_length=len(message),
        )

        return signed.signature.hex()

    def verify_signature(self, message: str, signature: str) -> bool:
        """Verify CLAW_V2 signature against public key.

        Args:
            message: Original message.
            signature: Signature to verify.

        Returns:
            True if signature is valid.
        """
        try:
            encode = encode_defunct(text=message)
            recovered = Account.recover_message(encode, signature=bytes.fromhex(signature))
            is_valid = recovered.lower() == self._wallet_address.lower()

            logger.debug(
                "Signature verified",
                wallet=self._wallet_address,
                valid=is_valid,
            )

            return is_valid
        except Exception as e:
            logger.warning(
                "Signature verification failed",
                error=str(e),
            )
            return False

    def sign_task_bid(self, task_id: str, bid_amount: str) -> str:
        """Sign a task bid.

        Args:
            task_id: Task identifier.
            bid_amount: Bid amount in USDC.

        Returns:
            Signed bid message.
        """
        message = f"BID:{task_id}:{bid_amount}"
        return self.sign_message(message)

    def sign_proof(self, task_id: str, output_hash: str, timestamp: str) -> str:
        """Sign a work proof.

        Args:
            task_id: Task identifier.
            output_hash: Hash of work output.
            timestamp: Proof timestamp.

        Returns:
            Signed proof.
        """
        message = f"PROOF:{task_id}:{output_hash}:{timestamp}"
        return self.sign_message(message)

    def sign_settlement(self, task_id: str, earnings: str, stake: str) -> str:
        """Sign a settlement statement.

        Args:
            task_id: Task identifier.
            earnings: Earnings amount.
            stake: Stake amount.

        Returns:
            Signed settlement.
        """
        message = f"SETTLE:{task_id}:{earnings}:{stake}"
        return self.sign_message(message)
