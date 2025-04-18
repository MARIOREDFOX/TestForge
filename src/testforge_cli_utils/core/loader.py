from testforge_cli_utils.protocols import bmc, cxl, pcie


def load_protocol(protocol_name):
    """Load the appropriate protocol handler."""
    protocols = {
        "bmc": bmc,
        "cxl": cxl,
        "pcie": pcie,
    }

    return protocols.get(protocol_name, None)


def load_test_protocol(protocol_name):
    """Load test functionality based on protocol."""
    protocol = load_protocol(protocol_name)
    if protocol:
        return protocol.run_test()
    else:
        raise ValueError(f"Protocol {protocol_name} not found!")
