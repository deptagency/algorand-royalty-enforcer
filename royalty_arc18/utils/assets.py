from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.future.transaction import AssetCreateTxn, AssetTransferTxn
from algosdk.v2client.algod import AlgodClient
from royalty_arc18.utils.accounts import Account
from royalty_arc18.utils.transactions import waitForTransaction


def mintNFT(client: AlgodClient, creator: Account, enforcer_address: str) -> int:
    signer = creator.getSigner()
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            signer=signer,
            txn=AssetCreateTxn(
                sender=creator.getAddress(),
                sp=sp,
                total=1,
                decimals=0,
                default_frozen=True,
                asset_name="My NFT",
                clawback=enforcer_address,
                freeze=enforcer_address,
                manager=enforcer_address,
                reserve=enforcer_address,
                unit_name="NFT",
                url="https://example.com",
            ),
        )
    )
    result = atc.execute(client, 2)
    response = waitForTransaction(client, result.tx_ids[0])
    assert response.assetIndex is not None and response.assetIndex > 0
    return response.assetIndex


def optInToNFT(client: AlgodClient, sender: Account, nftID: int):
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            signer=sender.getSigner(),
            txn=AssetTransferTxn(
                sender=sender.getAddress(),
                sp=sp,
                index=nftID,
                receiver=sender.getAddress(),
                amt=0,
            ),
        )
    )
    atc.execute(client, 2)
