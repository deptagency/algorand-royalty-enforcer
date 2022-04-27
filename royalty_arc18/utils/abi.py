from algosdk.abi import Interface, Method


# Utility method til one is provided
def getMethod(i: Interface, name: str) -> Method:
    for m in i.methods:
        if m.name == name:
            return m
    raise Exception("No method with the name {}".format(name))
