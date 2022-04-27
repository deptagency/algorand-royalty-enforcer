from base64 import b64decode
from typing import Any, Dict, List, Union

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
)
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient
from royalty_arc18.contracts.enforcer import (
    compile_enforcer_approval,
    compile_enforcer_clear,
)
from royalty_arc18.utils.accounts import Account
from royalty_arc18.utils.transactions import waitForTransaction


def fullyCompileContract(client: AlgodClient, teal: str) -> bytes:
    response = client.compile(teal)
    return b64decode(response["result"])


def deployEnforcer(client: AlgodClient, sender: Account):
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
    appAddress = get_application_address(appID)

    # Pay min balance to enforcer account and opt-in to contract to enable making offers
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()

    # Enforcer contract needs min balance to be able to send transactions
    atc.add_transaction(
        TransactionWithSigner(
            txn=PaymentTxn(
                sender=sender.getAddress(),
                amt=int(1e6),
                receiver=appAddress,
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
                index=appID,
                on_complete=OnComplete.OptInOC,
                sp=sp,
            ),
            signer=sender.getSigner(),
        )
    )
    atc.execute(client, 2)

    return appID, appAddress


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
