# TestForge Architecture

TestForge is a hardware/system-level test automation framework designed to support:

- CXL device testing
- PCIe enumeration and validation
- BMC interaction via IPMI/Redfish
- Firmware flashing and regression testing

## Modules

- **core/**: Test runner, loader, logging, reporting
- **protocols/**: Hardware access abstraction
- **utils/**: Helpers for SSH, retry logic, config loading
- **cli.py**: Click-based CLI entrypoint

