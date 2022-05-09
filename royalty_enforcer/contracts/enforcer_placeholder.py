from pyteal import *


class Keys:
    # Holds the current administrator
    administrator = Bytes("administrator")

    # Holds the basis points taken out for the royalty payment (1% = 100 bp)
    royalty_basis = Bytes("royalty_basis")

    # Holds the royalty recipient address
    royalty_receiver = Bytes("royalty_receiver")


class Constants:
    # 10_000 basis points = 100%
    basis_point_multiplier = 10_000


class Selectors:
    set_administrator = MethodSignature("set_administrator(address)void")
    get_administrator = MethodSignature("get_administrator()address")

    offer = MethodSignature("offer(asset,uint64,address,uint64,address)void")
    get_offer = MethodSignature("get_offer(uint64,account)(address,uint64)")

    set_policy = MethodSignature("set_policy(uint64,address)void")
    get_policy = MethodSignature("get_policy()(address,uint64)")

    set_payment_asset = MethodSignature("set_payment_asset(asset,bool)void")

    transfer = MethodSignature(
        "transfer(asset,uint64,account,account,account,txn,asset,uint64)void"
    )

    royalty_free_move = MethodSignature(
        "royalty_free_move(asset,uint64,account,account,uint64)void"
    )

    asset_create = MethodSignature(
        "asset_create(uint64,uint32,bool,string,string,string,[]byte,address,address,address,address)uint64"
    )

    asset_config = MethodSignature(
        "asset_config(asset,uint64,uint32,bool,string,string,string,[]byte,address,address,address,address)void"
    )

    asset_transfer = MethodSignature("asset_transfer(asset,uint64,account,account)void")

    asset_freeze = MethodSignature("asset_freeze(asset,account,bool)void")

    asset_destroy = MethodSignature("asset_destroy(asset)void")


# region Administrator


@Subroutine(TealType.bytes)
def administrator():
    return Seq(
        (admin := App.globalGetEx(Int(0), Keys.administrator)),
        If(admin.hasValue(), admin.value(), Global.creator_address()),
    )


@Subroutine(TealType.uint64)
def set_administrator():
    return Seq(
        (new_admin := abi.Address()).decode(Txn.application_args[1]),
        put_administrator(new_admin.encode()),
    )


@Subroutine(TealType.uint64)
def put_administrator(admin: Expr):
    return Seq(App.globalPut(Keys.administrator, admin), Int(1))


@Subroutine(TealType.uint64)
def get_administrator():
    return Seq(
        (admin := abi.Address()).decode(administrator()),
        abi.MethodReturn(admin),
        Int(1),
    )


# endregion


def approval():
    from_administrator = Txn.sender() == administrator()

    action_router = Cond(
        [
            And(
                Txn.application_args[0] == Selectors.royalty_free_move,
                from_administrator,
            ),
            Int(0),
        ],
        [
            And(Txn.application_args[0] == Selectors.set_policy, from_administrator),
            Int(0),
        ],
        [
            And(
                Txn.application_args[0] == Selectors.set_payment_asset,
                from_administrator,
            ),
            Int(0),
        ],
        [
            And(
                Txn.application_args[0] == Selectors.set_administrator,
                from_administrator,
            ),
            set_administrator(),
        ],
        [Txn.application_args[0] == Selectors.transfer, Int(0)],
        [Txn.application_args[0] == Selectors.offer, Int(0)],
        [Txn.application_args[0] == Selectors.get_offer, Int(0)],
        [Txn.application_args[0] == Selectors.get_policy, Int(0)],
        [Txn.application_args[0] == Selectors.asset_transfer, Int(0)],
        [Txn.application_args[0] == Selectors.asset_create, Int(0)],
        [Txn.application_args[0] == Selectors.asset_config, Int(0)],
        [Txn.application_args[0] == Selectors.asset_destroy, Int(0)],
        [Txn.application_args[0] == Selectors.asset_freeze, Int(0)],
        [Txn.application_args[0] == Selectors.get_administrator, get_administrator()],
    )

    return Cond(
        [Txn.application_id() == Int(0), Return(put_administrator(Txn.sender()))],
        [
            Txn.on_completion() == OnComplete.DeleteApplication,
            Return(from_administrator),
        ],
        [
            Txn.on_completion() == OnComplete.UpdateApplication,
            Return(from_administrator),
        ],
        [Txn.on_completion() == OnComplete.OptIn, Approve()],
        [Txn.on_completion() == OnComplete.CloseOut, Approve()],
        [Txn.on_completion() == OnComplete.NoOp, Return(action_router)],
    )


def clear():
    return Approve()


def compile_enforcer_placeholder_approval():
    return compileTeal(
        approval(),
        mode=Mode.Application,
        version=6,
        optimize=OptimizeOptions(scratch_slots=True),
    )


def compile_enforcer_placeholder_clear():
    return compileTeal(
        clear(),
        mode=Mode.Application,
        version=6,
        optimize=OptimizeOptions(scratch_slots=True),
    )


if __name__ == "__main__":
    with open("assets/enforcer_placeholder_approval.teal", "w") as f:
        f.write(compile_enforcer_placeholder_approval())
    with open("assets/enforcer_placeholder_clear.teal", "w") as f:
        f.write(compile_enforcer_placeholder_clear())
