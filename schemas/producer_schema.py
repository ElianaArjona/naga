from pydantic import BaseModel
from datetime import datetime

class EthereumBlock(BaseModel):
    block_number: int
    block_hash: str
    timestamp: datetime
    transactions: int
    miner: str