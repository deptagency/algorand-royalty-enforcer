from algosdk.encoding import is_valid_address
from royalty_arc18.utils.accounts import getTemporaryAccount
from royalty_arc18.utils.apps import (
    deployEnforcer,
    deployMarketplace,
    getAppGlobalState,
    marketplaceListNFT,
    setEnforcerPolicy,
)
from royalty_arc18.utils.assets import mintNFT
from royalty_arc18.utils.clients import getAlgodClient, getKmdClient


def test_deploy_marketplace():
    client = getAlgodClient()
    kmd = getKmdClient()
    sender = getTemporaryAccount(client, kmd)

    deployMarketplace(client, sender)


def test_list_nft():
    client = getAlgodClient()
    kmd = getKmdClient()
    sender = getTemporaryAccount(client, kmd)
    royalty = getTemporaryAccount(client, kmd)

    enforcer = deployEnforcer(client, sender)
    marketplace = deployMarketplace(client, sender)
    nftID = mintNFT(client, sender, enforcer.address)

    setEnforcerPolicy(client, enforcer, sender, 1000, royalty.getAddress())
    marketplaceListNFT(client, enforcer, marketplace, sender, nftID, 1, 10_000_000)

    actual = getAppGlobalState(client, marketplace.id)
    expected = {
        b"app": enforcer.id,
        b"asset": nftID,
        b"amount": 1,
        b"price": 10_000_000,
        b"account": sender.getDecodedAddress(),
    }

    assert actual == expected


def test_buy_nft():
    # TODO: implement
    pass


def test_delist_nft():
    # TODO: implement
    pass
