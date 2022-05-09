from base64 import b64decode
from typing import Any, Dict, List, Union, Tuple

from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.future.transaction import (
    ApplicationCallTxn,
    ApplicationCreateTxn,
    OnComplete,
    PaymentTxn,
    StateSchema,
    AssetOptInTxn,
)
from algosdk.abi import Interface
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient
from royalty_enforcer.contracts.enforcer import (
    compile_enforcer_approval,
    compile_enforcer_clear,
)
from royalty_enforcer.contracts.marketplace import (
    compile_marketplace_approval,
    compile_marketplace_clear,
)
from royalty_enforcer.utils.abi import getMethod
from royalty_enforcer.utils.accounts import Account
from royalty_enforcer.utils.transactions import ZERO_ADDR, waitForTransaction


with open("assets/enforcer_abi.json") as f:
    enforcerABI = Interface.from_json(f.read())

with open("assets/marketplace_abi.json") as f:
    marketplaceABI = Interface.from_json(f.read())


def fullyCompileContract(client: AlgodClient, teal: str) -> bytes:
    response = client.compile(teal)
    return b64decode(response["result"])


class App:
    def __init__(self, appID: int, abi: Interface):
        self.id = appID
        self.address = get_application_address(appID)
        self.abi = abi
        pass

    def getMethod(self, methodName: str):
        for method in self.abi.methods:
            if method.name == methodName:
                return method
        raise Exception("No method with the name {}".format(methodName))


def deployEnforcer(client: AlgodClient, sender: Account) -> App:
    approval = fullyCompileContract(client, compile_enforcer_approval())
    clear = fullyCompileContract(client, compile_enforcer_clear())
    txn = ApplicationCreateTxn(
        sender=sender.getAddress(),
        on_complete=OnComplete.NoOpOC,
        approval_program=approval,
        clear_program=clear,
        global_schema=StateSchema(1, 2),
        local_schema=StateSchema(0, 16),
        sp=client.suggested_params(),
    )

    signedTxn = txn.sign(sender.getPrivateKey())
    client.send_transaction(signedTxn)

    response = waitForTransaction(client, signedTxn.get_txid())
    appID = response.applicationIndex
    assert appID is not None and appID > 0
    # appAddress = get_application_address(appID)
    app = App(appID, enforcerABI)

    # Pay min balance to enforcer account and opt-in to contract to enable making offers
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()

    # Enforcer contract needs min balance to be able to send transactions
    atc.add_transaction(
        TransactionWithSigner(
            txn=PaymentTxn(
                sender=sender.getAddress(),
                amt=int(1e6),
                receiver=app.address,
                sp=sp,
            ),
            signer=sender.getSigner(),
        )
    )

    # As creator we want to opt-in so we can call offer on the enforcer contract
    atc.add_transaction(
        TransactionWithSigner(
            txn=ApplicationCallTxn(
                sender=sender.getAddress(),
                index=app.id,
                on_complete=OnComplete.OptInOC,
                sp=sp,
            ),
            signer=sender.getSigner(),
        )
    )
    atc.execute(client, 2)

    return app


def deployMarketplace(client: AlgodClient, sender: Account) -> App:
    approval = fullyCompileContract(client, compile_marketplace_approval())
    clear = fullyCompileContract(client, compile_marketplace_clear())
    txn = ApplicationCreateTxn(
        sender=sender.getAddress(),
        on_complete=OnComplete.NoOpOC,
        approval_program=approval,
        clear_program=clear,
        global_schema=StateSchema(4, 1),
        local_schema=StateSchema(0, 16),
        sp=client.suggested_params(),
    )

    signedTxn = txn.sign(sender.getPrivateKey())
    client.send_transaction(signedTxn)

    response = waitForTransaction(client, signedTxn.get_txid())
    appID = response.applicationIndex
    assert appID is not None and appID > 0
    app = App(appID, marketplaceABI)

    # Pay min balance to enforcer account and opt-in to contract to enable making offers
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()

    # Enforcer contract needs min balance to be able to send transactions
    atc.add_transaction(
        TransactionWithSigner(
            txn=PaymentTxn(
                sender=sender.getAddress(),
                amt=int(1e6),
                receiver=app.address,
                sp=sp,
            ),
            signer=sender.getSigner(),
        )
    )
    atc.execute(client, 2)

    return app


def decodeState(stateArray: List[Any]) -> Dict[bytes, Union[int, bytes]]:
    state: Dict[bytes, Union[int, bytes]] = dict()

    for pair in stateArray:
        key = b64decode(pair["key"])

        value = pair["value"]
        valueType = value["type"]

        if valueType == 2:
            # value is uint64
            value = value.get("uint", 0)
        elif valueType == 1:
            # value is byte array
            value = b64decode(value.get("bytes", ""))
        else:
            raise Exception(f"Unexpected state type: {valueType}")

        state[key] = value

    return state


def getAppCreator(client: AlgodClient, appID: int) -> str:
    app = client.application_info(appID)
    return app["params"]["creator"]


def getAppGlobalState(
    client: AlgodClient, appID: int
) -> Dict[bytes, Union[int, bytes]]:
    appInfo = client.application_info(appID)
    return decodeState(appInfo["params"]["global-state"])


def setEnforcerPolicy(
    client: AlgodClient,
    enforcer: App,
    sender: Account,
    royaltyBasisPoints: int,
    royaltyRecipientAddress: str,
):
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcer.id,
        enforcer.getMethod("set_policy"),
        sender.getAddress(),
        sp,
        sender.getSigner(),
        method_args=[royaltyBasisPoints, royaltyRecipientAddress],
    )
    atc.execute(client, 2)


def getEnforcerPolicy(
    client: AlgodClient, enforcer: App, sender: Account
) -> Tuple[str, int]:
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcer.id,
        enforcer.getMethod("get_policy"),
        sender.getAddress(),
        sp,
        sender.getSigner(),
    )
    result = atc.execute(client, 2)
    royaltyRecipientAddress, royaltyBasisPoints = result.abi_results[0].return_value
    assert isinstance(royaltyRecipientAddress, str)
    assert isinstance(royaltyBasisPoints, int)
    return royaltyRecipientAddress, royaltyBasisPoints


def setEnforcerAdmin(
    client: AlgodClient,
    enforcer: App,
    sender: Account,
    adminAddress: str,
):
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcer.id,
        enforcer.getMethod("set_administrator"),
        sender.getAddress(),
        sp,
        sender.getSigner(),
        method_args=[adminAddress],
    )
    atc.execute(client, 2)


def getEnforcerAdmin(client: AlgodClient, enforcer: App, sender: Account) -> str:
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcer.id,
        enforcer.getMethod("get_administrator"),
        sender.getAddress(),
        sp,
        sender.getSigner(),
    )
    result = atc.execute(client, 2)
    adminAddress = result.abi_results[0].return_value
    assert isinstance(adminAddress, str)
    return adminAddress


def setEnforcerOffer(
    client: AlgodClient,
    enforcer: App,
    sender: Account,
    nftID: int,
    amount: int,
    authAddress: str,
    expectedAmount: int,
    expectedAuthAddress: str,
):
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcer.id,
        enforcer.getMethod("offer"),
        sender.getAddress(),
        sp,
        sender.getSigner(),
        [nftID, amount, authAddress, expectedAmount, expectedAuthAddress],
    )
    atc.execute(client, 2)


def getEnforcerOffer(
    client: AlgodClient,
    enforcer: App,
    sender: Account,
    nftID: int,
    sellerAddress: str,
) -> Tuple[str, int]:
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcer.id,
        enforcer.getMethod("get_offer"),
        sender.getAddress(),
        sp,
        sender.getSigner(),
        [nftID, sellerAddress],
    )
    result = atc.execute(client, 2)
    authAddress, amount = result.abi_results[0].return_value
    assert isinstance(authAddress, str)
    assert isinstance(amount, int)
    return authAddress, amount


def enforcerTransfer(
    client: AlgodClient,
    enforcer: App,
    buyer: Account,
    price: int,
    nftID: int,
    amount: int,
    sellerAddress: str,
    royaltyAddress: str,
):
    sp = client.suggested_params()
    payTxn = TransactionWithSigner(
        signer=buyer.getSigner(),
        txn=PaymentTxn(
            sender=buyer.getAddress(),
            sp=sp,
            amt=price,
            receiver=enforcer.address,
        ),
    )
    sp.fee = 4000  # need to pay for inner txn fee (for asset transfer + payments)
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcer.id,
        enforcer.getMethod("transfer"),
        buyer.getAddress(),
        sp,
        buyer.getSigner(),
        [
            nftID,
            amount,
            sellerAddress,
            buyer.getAddress(),
            royaltyAddress,
            payTxn,
            0,
            amount,
        ],
    )
    atc.execute(client, 2)


def enforcerRoyaltyFreeMove(
    client: AlgodClient,
    enforcer: App,
    sender: Account,
    nftID: int,
    amount: int,
    ownerAddress: str,
    buyerAddress: str,
):
    sp = client.suggested_params()
    sp.fee = 2000  # need to pay for inner txn fee (for asset transfer)
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcer.id,
        enforcer.getMethod("royalty_free_move"),
        sender.getAddress(),
        sp,
        sender.getSigner(),
        [nftID, amount, ownerAddress, buyerAddress, amount],
    )
    atc.execute(client, 2)


def marketplaceListNFT(
    client: AlgodClient,
    enforcer: App,
    marketplace: App,
    sender: Account,
    nftID: int,
    amount: int,
    price: int,
):
    # Won't send this, just using ATC to help serialize the transaction
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcer.id,
        enforcer.getMethod("offer"),
        sender.getAddress(),
        sp=client.suggested_params(),
        signer=sender.getSigner(),
        method_args=[nftID, amount, marketplace.address, 0, ZERO_ADDR],
    )
    group = atc.build_group()

    # List for sale (calls offer on enforcer)
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=marketplace.id,
        method=marketplace.getMethod("list"),
        sender=sender.getAddress(),
        sp=client.suggested_params(),
        signer=sender.getSigner(),
        method_args=[nftID, enforcer.id, amount, price, group[0]],
    )
    atc.execute(client, 2)


def marketplaceBuyNFT(
    client: AlgodClient,
    enforcer: App,
    marketplace: App,
    sellerAddress: str,
    royaltyAddress: str,
    buyer: Account,
    nftID: int,
    amount: int,
    price: int,
):
    atc = AtomicTransactionComposer()
    paymentTxn = TransactionWithSigner(
        txn=PaymentTxn(
            sender=buyer.getAddress(),
            sp=client.suggested_params(),
            amt=price,
            receiver=marketplace.address,
        ),
        signer=buyer.getSigner(),
    )
    atc.add_transaction(
        TransactionWithSigner(
            txn=AssetOptInTxn(
                sender=buyer.getAddress(),
                sp=client.suggested_params(),
                index=nftID,
            ),
            signer=buyer.getSigner(),
        )
    )
    sp = client.suggested_params()
    # provide additional txn fee to pay for inner txns
    sp.fee = 4000
    atc.add_method_call(
        app_id=marketplace.id,
        method=marketplace.getMethod("buy"),
        sender=buyer.getAddress(),
        sp=sp,
        signer=buyer.getSigner(),
        method_args=[
            nftID,
            enforcer.id,
            enforcer.address,
            sellerAddress,
            royaltyAddress,
            amount,
            paymentTxn,
        ],
    )
    atc.execute(client, 2)
