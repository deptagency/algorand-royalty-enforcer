from algosdk import encoding
from algosdk.abi import Interface
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.future.transaction import AssetTransferTxn, PaymentTxn
from royalty_arc18.utils.abi import getMethod
from royalty_arc18.utils.accounts import getBalances, getTemporaryAccount
from royalty_arc18.utils.apps import deployEnforcer, getAppGlobalState
from royalty_arc18.utils.assets import mintNFT
from royalty_arc18.utils.clients import getAlgodClient, getKmdClient

ZERO_ADDR = encoding.encode_address(bytes(32))


with open("assets/enforcer_abi.json") as f:
    enforcerABI = Interface.from_json(f.read())


def test_create_enforcer():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    enforcerAppID, enforcerAppAddress = deployEnforcer(client, creator)
    actual = getAppGlobalState(client, enforcerAppID)
    expected = {
        b"administrator": encoding.decode_address(creator.getAddress()),
    }
    assert actual == expected


def test_set_policy():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    royalty = getTemporaryAccount(client, kmd)
    enforcerAppID, enforcerAppAddress = deployEnforcer(client, creator)

    assert enforcerAppID is not None and enforcerAppID > 0

    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "set_policy"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        method_args=[1000, royalty.getAddress()],
    )
    atc.execute(client, 2)

    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "get_policy"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
    )
    result = atc.execute(client, 2)

    assert result.abi_results[0].return_value == [royalty.getAddress(), 1000]

    actual = getAppGlobalState(client, enforcerAppID)
    expected = {
        b"administrator": encoding.decode_address(creator.getAddress()),
        b"royalty_receiver": encoding.decode_address(royalty.getAddress()),
        b"royalty_basis": 1000,
    }

    assert actual == expected


def test_set_administrator():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    admin = getTemporaryAccount(client, kmd)
    enforcerAppID, enforcerAppAddress = deployEnforcer(client, creator)

    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "set_administrator"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        method_args=[admin.getAddress()],
    )
    atc.execute(client, 2)

    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "get_administrator"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
    )
    result = atc.execute(client, 2)

    assert result.abi_results[0].return_value == admin.getAddress()

    actual = getAppGlobalState(client, enforcerAppID)
    expected = {
        b"administrator": encoding.decode_address(admin.getAddress()),
    }

    assert actual == expected


def test_create_offer():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    royalty = getTemporaryAccount(client, kmd)
    auth_seller = getTemporaryAccount(client, kmd)
    enforcerAppID, enforcerAppAddress = deployEnforcer(client, creator)
    nftAssetID = mintNFT(client, creator, enforcerAppAddress)

    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "set_policy"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        method_args=[1000, royalty.getAddress()],
    )
    atc.execute(client, 2)

    # Make an offer
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "offer"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        [nftAssetID, 1, auth_seller.getAddress(), 0, ZERO_ADDR],
    )
    atc.execute(client, 2)

    # Get offer details
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "get_offer"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        [nftAssetID, creator.getAddress()],
    )
    result = atc.execute(client, 2)

    assert result.abi_results[0].return_value == [auth_seller.getAddress(), 1]


def test_royalty_free_move():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    royalty = getTemporaryAccount(client, kmd)
    buyer = getTemporaryAccount(client, kmd)
    enforcerAppID, enforcerAppAddress = deployEnforcer(client, creator)
    nftAssetID = mintNFT(client, creator, enforcerAppAddress)

    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "set_policy"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        method_args=[1000, royalty.getAddress()],
    )
    atc.execute(client, 2)

    # Make an offer
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "offer"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        [nftAssetID, 1, creator.getAddress(), 0, ZERO_ADDR],
    )
    atc.execute(client, 2)

    # Buyer opt-in to NFT
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            signer=buyer.getSigner(),
            txn=AssetTransferTxn(
                sender=buyer.getAddress(),
                sp=sp,
                index=nftAssetID,
                receiver=buyer.getAddress(),
                amt=0,
            ),
        )
    )
    atc.execute(client, 2)

    # Royalty free move
    sp = client.suggested_params()
    sp.fee = 2000  # need to pay for inner txn fee (for asset transfer)
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "royalty_free_move"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        [nftAssetID, 1, creator.getAddress(), buyer.getAddress(), 1],
    )
    atc.execute(client, 2)

    seller_balances = getBalances(client, creator.getAddress())
    buyer_balances = getBalances(client, buyer.getAddress())

    assert seller_balances[nftAssetID] == 0
    assert buyer_balances[nftAssetID] == 1


def test_transfer():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    royalty = getTemporaryAccount(client, kmd)
    buyer = getTemporaryAccount(client, kmd)

    enforcerAppID, enforcerAppAddress = deployEnforcer(client, creator)
    nftAssetID = mintNFT(client, creator, enforcerAppAddress)

    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "set_policy"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        method_args=[1000, royalty.getAddress()],
    )
    atc.execute(client, 2)

    # Make an offer
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "offer"),
        creator.getAddress(),
        sp,
        creator.getSigner(),
        [nftAssetID, 1, buyer.getAddress(), 0, ZERO_ADDR],
    )
    atc.execute(client, 2)

    # Buyer opt-in to NFT
    sp = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            signer=buyer.getSigner(),
            txn=AssetTransferTxn(
                sender=buyer.getAddress(),
                sp=sp,
                index=nftAssetID,
                receiver=buyer.getAddress(),
                amt=0,
            ),
        )
    )
    atc.execute(client, 2)

    # Transfer
    sp = client.suggested_params()
    payTxn = TransactionWithSigner(
        signer=buyer.getSigner(),
        txn=PaymentTxn(
            sender=buyer.getAddress(),
            sp=sp,
            amt=int(1e7),
            receiver=enforcerAppAddress,
        ),
    )
    sp.fee = 4000  # need to pay for inner txn fee (for asset transfer + payments)
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        enforcerAppID,
        getMethod(enforcerABI, "transfer"),
        buyer.getAddress(),
        sp,
        buyer.getSigner(),
        [
            nftAssetID,
            1,
            creator.getAddress(),
            buyer.getAddress(),
            royalty.getAddress(),
            payTxn,
            0,
            1,
        ],
    )
    atc.execute(client, 2)

    seller_balances = getBalances(client, creator.getAddress())
    buyer_balances = getBalances(client, buyer.getAddress())

    assert seller_balances[nftAssetID] == 0
    assert buyer_balances[nftAssetID] == 1
