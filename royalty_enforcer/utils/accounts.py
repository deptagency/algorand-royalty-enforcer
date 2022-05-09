from typing import Any, Dict, List, Optional

from algosdk.account import address_from_private_key, generate_account
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
    TransactionSigner,
)
from algosdk.encoding import decode_address
from algosdk.future.transaction import PaymentTxn, Transaction, assign_group_id
from algosdk.kmd import KMDClient
from algosdk.mnemonic import from_private_key, to_private_key
from algosdk.v2client.algod import AlgodClient
from royalty_enforcer.utils.transactions import waitForTransaction


class Account:
    """Represents a private key and address for an Algorand account"""

    def __init__(self, privateKey: str) -> None:
        self.sk = privateKey
        self.addr = address_from_private_key(privateKey)

    def getAddress(self) -> str:
        return self.addr

    def getDecodedAddress(self) -> bytes:
        return decode_address(self.addr)

    def getPrivateKey(self) -> str:
        return self.sk

    def getMnemonic(self) -> str:
        return from_private_key(self.sk)

    def getSigner(self) -> TransactionSigner:
        return AccountTransactionSigner(self.sk)

    @classmethod
    def FromMnemonic(cls, m: str) -> "Account":
        return cls(to_private_key(m))


KMD_WALLET_NAME = "unencrypted-default-wallet"
KMD_WALLET_PASSWORD = ""

kmdAccounts: Optional[List[Account]] = None


def getGenesisAccounts(kmd: KMDClient) -> List[Account]:
    global kmdAccounts

    if kmdAccounts is None:
        wallets = kmd.list_wallets()
        walletID = None
        for wallet in wallets:
            if wallet["name"] == KMD_WALLET_NAME:
                walletID = wallet["id"]
                break

        if walletID is None:
            raise Exception("Wallet not found: {}".format(KMD_WALLET_NAME))

        walletHandle = kmd.init_wallet_handle(walletID, KMD_WALLET_PASSWORD)

        try:
            addresses = kmd.list_keys(walletHandle)
            privateKeys = [
                kmd.export_key(walletHandle, KMD_WALLET_PASSWORD, addr)
                for addr in addresses
            ]
            kmdAccounts = [Account(sk) for sk in privateKeys]
        finally:
            kmd.release_wallet_handle(walletHandle)

    return kmdAccounts


def getBalances(client: AlgodClient, account: str) -> Dict[int, int]:
    balances: Dict[int, int] = dict()

    accountInfo = client.account_info(account)

    # set key 0 to Algo balance
    balances[0] = accountInfo["amount"]

    assets: List[Dict[str, Any]] = accountInfo.get("assets", [])
    for assetHolding in assets:
        assetID = assetHolding["asset-id"]
        amount = assetHolding["amount"]
        balances[assetID] = amount

    return balances


FUNDING_AMOUNT = 100_000_000

accountList: List[Account] = []


def getTemporaryAccount(client: AlgodClient, kmd: KMDClient) -> Account:
    global accountList

    if len(accountList) == 0:
        sks = [generate_account()[0] for i in range(16)]
        accountList = [Account(sk) for sk in sks]

        genesisAccounts = getGenesisAccounts(kmd)
        suggestedParams = client.suggested_params()

        txns: List[Transaction] = []
        for i, a in enumerate(accountList):
            fundingAccount = genesisAccounts[i % len(genesisAccounts)]
            txns.append(
                PaymentTxn(
                    sender=fundingAccount.getAddress(),
                    receiver=a.getAddress(),
                    amt=FUNDING_AMOUNT,
                    sp=suggestedParams,
                )
            )

        txns = assign_group_id(txns)
        signedTxns = [
            txn.sign(genesisAccounts[i % len(genesisAccounts)].getPrivateKey())
            for i, txn in enumerate(txns)
        ]

        client.send_transactions(signedTxns)

        waitForTransaction(client, signedTxns[0].get_txid())

    return accountList.pop()
