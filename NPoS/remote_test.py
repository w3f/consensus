import npos
import pprint
from substrateinterface import SubstrateInterface
from substrateinterface.utils.ss58 import ss58_decode, ss58_encode


pp = pprint.PrettyPrinter(indent=4)

substrate = SubstrateInterface(
    url="ws://localhost:9944",
    address_type=0,
    type_registry={'types': {
            "StakingLedger<AccountId, BalanceOf>": {
                "type": "struct",
                "type_mapping": [
                    ["stash", "AccountId"],
                    ["total", "Compact<Balance>"],
                    ["active", "Compact<Balance>"],
                    ["unlocking", "Vec<UnlockChunk<Balance>>"],
                    ["claimedReward", "Vec<EraIndex>"]
                ]
            },
        }
    },
    type_registry_preset='polkadot',
)

head = substrate.get_chain_finalised_head()


def get_candidates():
    prefix = substrate.generate_storage_hash("Staking", "Validators")
    pairs = substrate.rpc_request(method="state_getPairs", params=[prefix, head])['result']
    last_32_bytes = list(map(lambda p: "0x" + p[0][-64:], pairs))
    return list(map(lambda k: ss58_encode(k), last_32_bytes))


def get_nominators():
    prefix = substrate.generate_storage_hash("Staking", "Nominators")
    pairs = substrate.rpc_request(method="state_getPairs", params=[prefix, head])['result']

    nominators = list(
        map(lambda p: ("0x" + p[0][-64:], substrate.decode_scale("Nominations<AccountId>", p[1])['targets']), pairs)
    )

    nominators = list(map(lambda x: (
        ss58_encode(x[0], substrate.address_type),
        x[1],
    ), nominators))

    return list(map(lambda x: (
        x[0],
        get_backing_stake_of(x[0]),
        [ss58_encode(acc, substrate.address_type) for acc in x[1]],
    ), nominators))


def get_backing_stake_of(who):
    ctrl = substrate.get_runtime_state(
        module="Staking",
        storage_function="Bonded",
        params=[who],
        block_hash=head,
    )['result']

    ctrl = ss58_encode(ctrl, substrate.address_type)

    ledger = substrate.get_runtime_state(
        module="Staking",
        storage_function="Ledger",
        params=[ctrl],
        block_hash=head,
    )['result']

    return ledger['active']


def validator_count():
    return substrate.get_runtime_state("Staking", "ValidatorCount", [], head)['result']


candidates = get_candidates()
nominators = get_nominators()
to_elect = validator_count()

print("{} validators, {} nominators, electing {}".format(len(candidates), len(nominators), to_elect))
distribution, winners = npos.phragmms(nominators, to_elect)
npos.print_list(winners)
print(sum([c.backed_stake for c in winners]))
print(min([c.backed_stake for c in winners]))
score = [min([c.backed_stake for c in winners]), sum([c.backed_stake for c in winners])]
print("score = [{:,}, {:,}]".format(int(score[0]), int(score[1])))
