from pyteal import *


class Keys:
    app = Bytes("app")
    asset = Bytes("asset")
    price = Bytes("price")
    amount = Bytes("amount")
    account = Bytes("account")


class Selectors:
    list = MethodSignature("list(asset,application,uint64,uint64,appl)void")

    buy = MethodSignature(
        "buy(asset,application,account,account,account,uint64,pay)void"
    )

    transfer = MethodSignature(
        "transfer(asset,uint64,account,account,account,txn,asset,uint64)void"
    )


@Subroutine(TealType.uint64)
def list_nft():
    asset_id = Txn.assets[Btoi(Txn.application_args[1])]
    app_id = Txn.applications[Btoi(Txn.application_args[2])]
    asset_amount = Btoi(Txn.application_args[3])
    price = Btoi(Txn.application_args[4])
    offer_txn = Gtxn[Txn.group_index() - Int(1)]

    return Seq(
        asset_balance := AssetHolding.balance(Txn.sender(), asset_id),
        asset_freeze := AssetParam.freeze(asset_id),
        asset_clawback := AssetParam.clawback(asset_id),
        app_addr := AppParam.address(app_id),
        offered := App.localGetEx(Txn.sender(), app_id, Itob(asset_id)),
        # Check stuff
        Assert(
            And(
                # We don't have anything there yet
                App.globalGet(Keys.app) == Int(0),
                # The app call to trigger offered is present and same as app id
                offer_txn.application_id() == app_id,
                # The caller has the asset
                asset_balance.value() > Int(0),
                # The freeze/clawback are set to app addr
                asset_freeze.value() == app_addr.value(),
                asset_clawback.value() == app_addr.value(),
                # The authorized addr for this asset is this apps account
                Extract(offered.value(), Int(0), Int(32))
                == Global.current_application_address(),
                ExtractUint64(offered.value(), Int(32)) <= asset_amount,
            )
        ),
        # Set appropriate parameters
        App.globalPut(Keys.app, app_id),
        App.globalPut(Keys.asset, asset_id),
        App.globalPut(Keys.amount, asset_amount),
        App.globalPut(Keys.price, price),
        App.globalPut(Keys.account, Txn.sender()),
        Int(1),
    )


@Subroutine(TealType.uint64)
def buy_nft():
    asset_id = Txn.assets[Btoi(Txn.application_args[1])]
    app_id = Txn.applications[Btoi(Txn.application_args[2])]
    app_addr = Txn.accounts[Btoi(Txn.application_args[3])]
    owner_acct = Txn.accounts[Btoi(Txn.application_args[4])]
    royalty_acct = Txn.accounts[Btoi(Txn.application_args[5])]
    asset_amount = Btoi(Txn.application_args[6])
    pay_txn = Gtxn[Txn.group_index() - Int(1)]

    # Make sure its the asset for sale
    # Make sure the payment is for the right amount
    # Issue inner app call to royalty to move asset
    return Seq(
        current_offer := App.localGetEx(owner_acct, app_id, Itob(asset_id)),
        Assert(
            And(
                # Matches what we have in global state
                owner_acct == App.globalGet(Keys.account),
                app_id == App.globalGet(Keys.app),
                asset_id == App.globalGet(Keys.asset),
                pay_txn.amount() >= App.globalGet(Keys.price),
                asset_amount <= App.globalGet(Keys.amount),
                # Pay me plz
                pay_txn.receiver() == Global.current_application_address(),
                current_offer.hasValue(),
            )
        ),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.amount: pay_txn.amount(),
                TxnField.receiver: app_addr,
            }
        ),
        InnerTxnBuilder.Next(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.ApplicationCall,
                TxnField.application_id: app_id,
                TxnField.application_args: [
                    Selectors.transfer,
                    Itob(Int(0)),  # Royalty Asset in 0th position of asset array
                    Itob(asset_amount),  # The number of units being purchased
                    Itob(Int(1)),  # Current owner first element here but offset by 1
                    Itob(Int(2)),  # Buyer
                    Itob(Int(3)),  # Who we need to pay for royalties
                    Itob(Int(0)),  # Asset idx of 0, should be ignored
                    Itob(
                        offered_amount(current_offer.value())
                    ),  # Current offered amount
                ],
                TxnField.assets: [asset_id],
                TxnField.accounts: [owner_acct, Txn.sender(), royalty_acct],
            }
        ),
        InnerTxnBuilder.Submit(),
        # Wipe listing
        App.globalDel(Keys.asset),
        App.globalDel(Keys.amount),
        App.globalDel(Keys.app),
        App.globalDel(Keys.account),
        App.globalDel(Keys.price),
        Int(1),
    )


@Subroutine(TealType.uint64)
def offered_amount(offer):
    return ExtractUint64(offer, Int(32))


@Subroutine(TealType.bytes)
def offered_auth(offer):
    return Extract(offer, Int(0), Int(32))


def approval():
    is_creator = Txn.sender() == Global.creator_address()

    action_router = Cond(
        [Txn.application_args[0] == Selectors.list, list_nft()],
        [Txn.application_args[0] == Selectors.buy, buy_nft()],
    )

    return Cond(
        [Txn.application_id() == Int(0), Approve()],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_creator)],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_creator)],
        [Txn.on_completion() == OnComplete.OptIn, Approve()],
        [Txn.on_completion() == OnComplete.CloseOut, Approve()],
        [Txn.on_completion() == OnComplete.NoOp, Return(action_router)],
    )


def clear():
    return Approve()


def compile_marketplace_approval():
    return compileTeal(approval(), mode=Mode.Application, version=6)


def compile_marketplace_clear():
    return compileTeal(clear(), mode=Mode.Application, version=6)


if __name__ == "__main__":
    # TODO: write teal contracts to files
    pass
