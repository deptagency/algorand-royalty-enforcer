from algosdk.encoding import is_valid_address
from royalty_enforcer.utils.accounts import getBalances, getTemporaryAccount
from royalty_enforcer.utils.apps import (
    deployEnforcer,
    deployMarketplace,
    getAppGlobalState,
    marketplaceBuyNFT,
    marketplaceListNFT,
    setEnforcerPolicy,
)
from royalty_enforcer.utils.assets import mintNFT
from royalty_enforcer.utils.clients import getAlgodClient, getKmdClient


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
    client = getAlgodClient()
    kmd = getKmdClient()
    sender = getTemporaryAccount(client, kmd)
    royalty = getTemporaryAccount(client, kmd)
    buyer = getTemporaryAccount(client, kmd)

    enforcer = deployEnforcer(client, sender)
    marketplace = deployMarketplace(client, sender)
    nftID = mintNFT(client, sender, enforcer.address)
    basisPoints = 1000
    amount = 1
    price = 1_000_000

    setEnforcerPolicy(client, enforcer, sender, basisPoints, royalty.getAddress())
    marketplaceListNFT(client, enforcer, marketplace, sender, nftID, amount, price)
    marketplaceBuyNFT(
        client,
        enforcer,
        marketplace,
        sender.getAddress(),
        royalty.getAddress(),
        buyer,
        nftID,
        amount,
        price,
    )

    buyerBalances = getBalances(client, buyer.getAddress())
    assert buyerBalances[nftID] == amount
    sellerBalances = getBalances(client, sender.getAddress())
    assert sellerBalances[nftID] == 0


def test_delist_nft():
    # TODO: implement
    pass
