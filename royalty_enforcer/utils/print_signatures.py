from algosdk.abi import Interface

with open("assets/enforcer_abi.json") as f:
    enforcerABI = Interface.from_json(f.read())


for method in enforcerABI.methods:
    print(method.get_signature())
    print()
