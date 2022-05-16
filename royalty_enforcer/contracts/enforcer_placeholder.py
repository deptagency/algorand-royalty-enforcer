from pyteal import *

from royalty_enforcer.contracts.enforcer import *


def approval():
    from_administrator = Txn.sender() == administrator()

    action_router = Cond(
        # Only support policy and administrator actions until TEAL v7
        [
            And(Txn.application_args[0] == Selectors.set_policy, from_administrator),
            set_policy(),
        ],
        [Txn.application_args[0] == Selectors.get_policy, get_policy()],
        [
            And(
                Txn.application_args[0] == Selectors.set_administrator,
                from_administrator,
            ),
            set_administrator(),
        ],
        [Txn.application_args[0] == Selectors.get_administrator, get_administrator()],
        # The following methods are not yet implemented while waiting for TEAL v7
        [Txn.application_args[0] == Selectors.royalty_free_move, Int(0)],
        [Txn.application_args[0] == Selectors.set_payment_asset, Int(0)],
        [Txn.application_args[0] == Selectors.transfer, Int(0)],
        [Txn.application_args[0] == Selectors.offer, Int(0)],
        [Txn.application_args[0] == Selectors.get_offer, Int(0)],
        [Txn.application_args[0] == Selectors.asset_transfer, Int(0)],
        [Txn.application_args[0] == Selectors.asset_create, Int(0)],
        [Txn.application_args[0] == Selectors.asset_config, Int(0)],
        [Txn.application_args[0] == Selectors.asset_destroy, Int(0)],
        [Txn.application_args[0] == Selectors.asset_freeze, Int(0)],
        [Txn.application_args[0] == Selectors.is_asset_frozen, Int(0)],
        [Txn.application_args[0] == Selectors.get_asset_name, Int(0)],
        [Txn.application_args[0] == Selectors.get_clawback_addr, Int(0)],
        [Txn.application_args[0] == Selectors.get_decimals, Int(0)],
        [Txn.application_args[0] == Selectors.get_default_frozen, Int(0)],
        [Txn.application_args[0] == Selectors.get_freeze_addr, Int(0)],
        [Txn.application_args[0] == Selectors.get_manager_addr, Int(0)],
        [Txn.application_args[0] == Selectors.get_metadata_hash, Int(0)],
        [Txn.application_args[0] == Selectors.get_reserve_addr, Int(0)],
        [Txn.application_args[0] == Selectors.get_total, Int(0)],
        [Txn.application_args[0] == Selectors.get_unit_name, Int(0)],
        [Txn.application_args[0] == Selectors.get_url, Int(0)],
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
