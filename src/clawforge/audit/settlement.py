import time

from eth_account import Account
from eth_account.messages import encode_defunct

from ..models import SettlementStatement, StateTransition
from .logger import HashChainLogger


class SettlementGenerator:
    def __init__(self, logger: HashChainLogger, private_key: str):
        self.logger = logger
        self._account = Account.from_key(private_key)

    def generate(self, task_id: str, transitions: list[StateTransition], amount: float) -> SettlementStatement:
        statement = SettlementStatement(
            task_id=task_id,
            agent_address=self._account.address,
            transitions=transitions,
            total_amount=amount,
            generated_at=time.time(),
        )

        content = statement.model_dump_json()
        signed = self._account.sign_message(encode_defunct(text=content))
        statement.signature = signed.signature.hex()

        self.logger.log("settlement_generated", task_id, {"amount": amount})

        return statement
