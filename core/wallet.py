"""
Wallet and cryptography module for order signing.

This module handles:
- Private key management
- Order signing for Polymarket (EIP-712)
- Transaction signing for SX
- Secure key storage and loading
"""

import logging
import os
from typing import Optional, Dict, Any
from eth_account import Account
from eth_account.messages import encode_defunct, encode_structured_data
from web3 import Web3


class WalletError(Exception):
    """Raised when wallet operations fail."""


class Wallet:
    """
    Manages Ethereum wallet for signing orders and transactions.

    Supports:
    - Loading private key from environment variable
    - EIP-712 structured data signing (Polymarket)
    - Transaction signing (SX)
    - Address derivation
    """

    def __init__(self, private_key: Optional[str] = None):
        """
        Initialize wallet.

        Args:
            private_key: Private key as hex string (with or without 0x prefix)
                        If None, will try to load from PRIVATE_KEY env var

        Raises:
            WalletError: If private key is invalid or not found
        """
        if private_key is None:
            private_key = os.getenv("PRIVATE_KEY")

        if not private_key:
            raise WalletError(
                "Private key not provided. Set PRIVATE_KEY environment variable "
                "or pass private_key parameter."
            )

        # Ensure 0x prefix
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        try:
            self.account = Account.from_key(private_key)
            self.address = self.account.address
            logging.info("Wallet initialized: %s", self.address)
        except Exception as exc:
            raise WalletError(f"Invalid private key: {exc}") from exc

    def sign_message(self, message: str) -> str:
        """
        Sign a plain text message.

        Args:
            message: Message to sign

        Returns:
            Signature as hex string
        """
        message_encoded = encode_defunct(text=message)
        signed_message = self.account.sign_message(message_encoded)
        return signed_message.signature.hex()

    def sign_typed_data(self, typed_data: Dict[str, Any]) -> str:
        """
        Sign EIP-712 typed structured data (used by Polymarket).

        Args:
            typed_data: EIP-712 structured data dictionary with:
                - types: Type definitions
                - primaryType: Primary type name
                - domain: Domain separator
                - message: Message data

        Returns:
            Signature as hex string

        Example:
            typed_data = {
                "types": {
                    "EIP712Domain": [...],
                    "Order": [...]
                },
                "primaryType": "Order",
                "domain": {...},
                "message": {...}
            }
        """
        try:
            encoded_data = encode_structured_data(typed_data)
            signed_message = self.account.sign_message(encoded_data)
            return signed_message.signature.hex()
        except Exception as exc:
            raise WalletError(f"Failed to sign typed data: {exc}") from exc

    def sign_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Sign a transaction (used by SX and other DeFi protocols).

        Args:
            transaction: Transaction dictionary with fields:
                - to: Recipient address
                - value: Amount in Wei
                - gas: Gas limit
                - gasPrice: Gas price in Wei
                - nonce: Transaction nonce
                - data: Transaction data (optional)
                - chainId: Chain ID

        Returns:
            Signed transaction as hex string

        Example:
            tx = {
                "to": "0x...",
                "value": 0,
                "gas": 21000,
                "gasPrice": Web3.to_wei(50, 'gwei'),
                "nonce": 0,
                "chainId": 1
            }
        """
        try:
            signed_tx = self.account.sign_transaction(transaction)
            return signed_tx.rawTransaction.hex()
        except Exception as exc:
            raise WalletError(f"Failed to sign transaction: {exc}") from exc

    @staticmethod
    def create_random_wallet() -> 'Wallet':
        """
        Create a new random wallet.

        Returns:
            New Wallet instance with random private key

        Warning:
            Store the private key securely! It will be lost if not saved.
        """
        account = Account.create()
        logging.warning(
            "Created new wallet: %s (SAVE THE PRIVATE KEY SECURELY!)",
            account.address
        )
        return Wallet(private_key=account.key.hex())


class PolymarketOrderSigner:
    """
    Signs Polymarket CLOB orders using EIP-712.

    Polymarket uses a Central Limit Order Book (CLOB) that requires
    EIP-712 signed orders for off-chain order placement.
    """

    # Polymarket CLOB domain (mainnet)
    DOMAIN = {
        "name": "Polymarket CTF Exchange",
        "version": "1",
        "chainId": 137,  # Polygon mainnet
        "verifyingContract": "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
    }

    # EIP-712 type definitions
    TYPES = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "Order": [
            {"name": "salt", "type": "uint256"},
            {"name": "maker", "type": "address"},
            {"name": "signer", "type": "address"},
            {"name": "taker", "type": "address"},
            {"name": "tokenId", "type": "uint256"},
            {"name": "makerAmount", "type": "uint256"},
            {"name": "takerAmount", "type": "uint256"},
            {"name": "expiration", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
            {"name": "feeRateBps", "type": "uint256"},
            {"name": "side", "type": "uint8"},
            {"name": "signatureType", "type": "uint8"},
        ],
    }

    def __init__(self, wallet: Wallet):
        """
        Initialize order signer.

        Args:
            wallet: Wallet instance for signing
        """
        self.wallet = wallet

    def sign_order(
        self,
        token_id: str,
        maker_amount: int,
        taker_amount: int,
        side: int,  # 0 = BUY, 1 = SELL
        nonce: int,
        expiration: int,
        fee_rate_bps: int = 0,
        taker: str = "0x0000000000000000000000000000000000000000",
    ) -> str:
        """
        Sign a Polymarket order.

        Args:
            token_id: Token ID (market outcome)
            maker_amount: Amount maker provides (in wei)
            taker_amount: Amount taker provides (in wei)
            side: 0 for BUY, 1 for SELL
            nonce: Unique nonce for this order
            expiration: Expiration timestamp (unix)
            fee_rate_bps: Fee rate in basis points
            taker: Taker address (0x0 for any taker)

        Returns:
            Order signature as hex string
        """
        import time

        salt = int(time.time() * 1000)  # Timestamp in ms as salt

        order_message = {
            "salt": salt,
            "maker": self.wallet.address,
            "signer": self.wallet.address,
            "taker": taker,
            "tokenId": int(token_id, 16) if isinstance(token_id, str) else token_id,
            "makerAmount": maker_amount,
            "takerAmount": taker_amount,
            "expiration": expiration,
            "nonce": nonce,
            "feeRateBps": fee_rate_bps,
            "side": side,
            "signatureType": 0,  # EOA signature
        }

        typed_data = {
            "types": self.TYPES,
            "primaryType": "Order",
            "domain": self.DOMAIN,
            "message": order_message,
        }

        signature = self.wallet.sign_typed_data(typed_data)
        logging.info("Signed Polymarket order: side=%d, signature=%s...", side, signature[:10])
        return signature


def load_wallet_from_env() -> Optional[Wallet]:
    """
    Load wallet from environment variable.

    Returns:
        Wallet instance if PRIVATE_KEY is set, None otherwise
    """
    try:
        return Wallet()
    except WalletError as exc:
        logging.warning("Could not load wallet: %s", exc)
        return None
