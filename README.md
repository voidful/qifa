# ⚡ qifa – Quick Installer for Flash Attention

> One command to detect, select, and install the correct [flash-attn](https://github.com/Dao-AILab/flash-attention) wheel for your environment.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: BSD-3](https://img.shields.io/badge/license-BSD--3-green.svg)](LICENSE)

---

## ✨ Features

- **Auto-Detection** – Identifies Python version, PyTorch version, CUDA version, and C++11 ABI
- **Smart Matching** – Finds the correct prebuilt wheel from official GitHub Releases
- **Zero Config** – Just run `qifa install` and you're done
- **Dry Run Mode** – Preview what will be installed before committing

> **Note**: Currently optimized for **Linux x86_64** official wheels. Windows/ROCm users will receive guidance but may need manual installation.

---

## 📦 Installation

```bash
pip install qifa
```

---

## 🚀 Quick Start

```bash
# Check your environment and see which wheel will be installed
qifa plan

# Install the matching flash-attn wheel
qifa install
```

---

## 📖 Commands

| Command | Description |
|---------|-------------|
| `qifa plan` | Show detected environment and the wheel that will be installed |
| `qifa install` | Download and install the matching wheel |
| `qifa uninstall` | Remove existing flash-attn installation |
| `qifa doctor` | Run compatibility checks and get guidance |

### Options

```bash
# Install a specific version
qifa install --version 2.5.8

# Force a specific C++11 ABI setting
qifa install --abi FALSE

# Preview without installing
qifa install --dry-run
```

---

## 🔍 Example Output

```bash
$ qifa plan
```

```json
{
  "python_tag": "cp310",
  "torch_mm": "2.1",
  "torch_cuda": "cu121",
  "chosen_cu_tag": "cu121",
  "abi_FALSE": true,
  "platform": "linux_x86_64",
  "version": "2.5.8",
  "found_asset": "flash_attn-2.5.8+cu121torch2.1cxx11abiFALSE-cp310-cp310-linux_x86_64.whl",
  "download_url": "https://github.com/Dao-AILab/flash-attention/releases/download/..."
}
```

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| **No matching wheel found** | Try `--version` to specify a different version, or `--abi TRUE` |
| **PyTorch not detected** | Install CUDA-enabled PyTorch first: `pip install torch --index-url https://download.pytorch.org/whl/cu121` |
| **Platform not supported** | Official wheels are for Linux x86_64; other platforms require building from source |

Run `qifa doctor` for detailed guidance on your specific environment.

---

## 📄 License

BSD-3-Clause © [Voidful](https://github.com/voidful)