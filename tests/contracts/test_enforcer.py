from royalty_arc18.utils.accounts import getBalances, getTemporaryAccount
from royalty_arc18.utils.apps import (
    deployEnforcer,
    enforcerRoyaltyFreeMove,
    enforcerTransfer,
    getAppGlobalState,
    getEnforcerAdmin,
    getEnforcerOffer,
    getEnforcerPolicy,
    setEnforcerAdmin,
    setEnforcerOffer,
    setEnforcerPolicy,
)
from royalty_arc18.utils.assets import mintNFT, optInToNFT
from royalty_arc18.utils.clients import getAlgodClient, getKmdClient
from royalty_arc18.utils.transactions import ZERO_ADDR


def test_create_enforcer():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    enforcer = deployEnforcer(client, creator)
    actual = getAppGlobalState(client, enforcer.id)
    expected = {
        b"administrator": creator.getDecodedAddress(),
    }
    assert actual == expected


def test_set_policy():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    royalty = getTemporaryAccount(client, kmd)
    enforcer = deployEnforcer(client, creator)

    setEnforcerPolicy(client, enforcer, creator, 1000, royalty.getAddress())

    assert getEnforcerPolicy(client, enforcer, creator) == (
        royalty.getAddress(),
        1000,
    )

    actual = getAppGlobalState(client, enforcer.id)
    expected = {
        b"administrator": creator.getDecodedAddress(),
        b"royalty_receiver": royalty.getDecodedAddress(),
        b"royalty_basis": 1000,
    }

    assert actual == expected


def test_set_administrator():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    admin = getTemporaryAccount(client, kmd)
    enforcer = deployEnforcer(client, creator)

    setEnforcerAdmin(client, enforcer, creator, admin.getAddress())

    assert getEnforcerAdmin(client, enforcer, creator) == admin.getAddress()

    actual = getAppGlobalState(client, enforcer.id)
    expected = {
        b"administrator": admin.getDecodedAddress(),
    }

    assert actual == expected


def test_create_offer():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    royalty = getTemporaryAccount(client, kmd)
    auth_seller = getTemporaryAccount(client, kmd)
    enforcer = deployEnforcer(client, creator)
    nftAssetID = mintNFT(client, creator, enforcer.address)

    setEnforcerPolicy(client, enforcer, creator, 1000, royalty.getAddress())

    # Make an offer
    setEnforcerOffer(
        client,
        enforcer,
        creator,
        nftAssetID,
        1,
        auth_seller.getAddress(),
        0,
        ZERO_ADDR,
    )

    # Get offer details
    assert getEnforcerOffer(
        client, enforcer, creator, nftAssetID, creator.getAddress()
    ) == (auth_seller.getAddress(), 1)


def test_royalty_free_move():
    client = getAlgodClient()
    kmd = getKmdClient()
    creator = getTemporaryAccount(client, kmd)
    royalty = getTemporaryAccount(client, kmd)
    buyer = getTemporaryAccount(client, kmd)
    enforcer = deployEnforcer(client, creator)
    nftAssetID = mintNFT(client, creator, enforcer.address)

    setEnforcerPolicy(client, enforcer, creator, 1000, royalty.getAddress())

    # Make an offer
    setEnforcerOffer(
        client,
        enforcer,
        creator,
        nftAssetID,
        1,
        creator.getAddress(),
        0,
        ZERO_ADDR,
    )

    # Buyer opt-in to NFT
    optInToNFT(
        client,
        buyer,
        nftAssetID,
    )

    # Royalty free move
    enforcerRoyaltyFreeMove(
        client,
        enforcer,
        creator,
        nftAssetID,
        1,
        creator.getAddress(),
        buyer.getAddress(),
    )

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

    enforcer = deployEnforcer(client, creator)
    nftAssetID = mintNFT(client, creator, enforcer.address)

    setEnforcerPolicy(client, enforcer, creator, 1000, royalty.getAddress())

    # Make an offer
    setEnforcerOffer(
        client,
        enforcer,
        creator,
        nftAssetID,
        1,
        buyer.getAddress(),
        0,
        ZERO_ADDR,
    )

    # Buyer opt-in to NFT
    optInToNFT(
        client,
        buyer,
        nftAssetID,
    )

    # Transfer
    enforcerTransfer(
        client,
        enforcer,
        buyer,
        10_000_000,
        nftAssetID,
        1,
        creator.getAddress(),
        royalty.getAddress(),
    )

    seller_balances = getBalances(client, creator.getAddress())
    buyer_balances = getBalances(client, buyer.getAddress())

    assert seller_balances[nftAssetID] == 0
    assert buyer_balances[nftAssetID] == 1
