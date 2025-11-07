# flashattn-helper

A small command-line utility that **detects your Python, PyTorch, CUDA, and C++11 ABI**. It then picks the matching prebuilt `flash-attn` wheel from the official GitHub Releases and installs it.

- Detects: Python tag, PyTorch version and CUDA tag, C++11 ABI.
- Filters matching wheels from Releases. Prefers `cxx11abiFALSE` by default.
- One command install. Or use `--dry-run` to print the selected wheel URL.

> Note: Currently optimized for Linux x86_64 official wheels. Windows or ROCm will print guidance but will not auto-install.

## Installation
```bash
pip install flashattn
```

## Usage
```bash
flashattn plan            # show environment and the wheel to be used
flashattn install         # download and install
flashattn install --version 2.5.8
flashattn install --abi FALSE --dry-run
flashattn uninstall       # remove existing flash-attn
flashattn doctor          # quick compatibility checks
```