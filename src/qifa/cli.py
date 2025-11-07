import argparse, platform, re, sys, subprocess, json, os, shutil, pathlib, time
from typing import Optional, Tuple, Dict, Any, List
import requests
from packaging.version import Version, InvalidVersion

DAO_REPO = "Dao-AILab/flash-attention"
GITHUB_TAG_API = "https://api.github.com/repos/{repo}/releases/tags/v{ver}"
GITHUB_REL_API = "https://api.github.com/repos/{repo}/releases"
GITHUB_DL_URL = "https://github.com/{repo}/releases/download/v{ver}/{fname}"

def run(cmd: List[str], check=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def detect_python_tag() -> str:
    major = sys.version_info.major
    minor = sys.version_info.minor
    return f"cp{major}{minor}"

def detect_torch() -> Tuple[Optional[str], Optional[str], Optional[bool]]:
    try:
        import torch
    except Exception:
        return None, None, None
    ver = torch.__version__.split("+")[0]
    # 取主次版號，例如 2.0.1 -> 2.0
    try:
        v = Version(ver)
        torch_mm = f"{v.major}.{v.minor}"
    except InvalidVersion:
        torch_mm = ver
    # 將 torch 的 CUDA 標記轉成 cu118 / cu121 等
    cu_raw = getattr(torch.version, "cuda", None)
    if cu_raw is None:
        # 可能是 ROCm 或 CPU-only
        cu_tag = None
    else:
        cu_nums = cu_raw.replace(".", "")
        # 12.1 -> cu121, 11.8 -> cu118
        cu_tag = f"cu{cu_nums}"
    # C++11 ABI。pip 版 PyTorch 多為 False
    try:
        from torch import _C as _torchC
        abi = bool(getattr(_torchC, "_GLIBCXX_USE_CXX11_ABI", 0))
    except Exception:
        abi = None
    return torch_mm, cu_tag, abi

def detect_platform() -> str:
    if sys.platform.startswith("linux") and platform.machine() == "x86_64":
        return "linux_x86_64"
    if sys.platform.startswith("win"):
        return "win_amd64"
    if sys.platform == "darwin":
        return "macosx"  # 不支援
    return platform.system()

def get_nvcc_version() -> Optional[str]:
    try:
        out = run(["nvcc", "-V"], check=False).stdout
    except Exception:
        return None
    m = re.search(r"release\s+(\d+)\.(\d+)", out)
    if not m:
        return None
    return f"cu{m.group(1)}{m.group(2)}"

def pick_cu_tag(torch_cu: Optional[str]) -> Optional[str]:
    # 優先用 torch.version.cuda。若沒有則嘗試 nvcc。
    if torch_cu:
        return torch_cu
    return get_nvcc_version()

def list_release_assets(version: Optional[str]) -> List[Dict[str, Any]]:
    if version:
        url = GITHUB_TAG_API.format(repo=DAO_REPO, ver=version)
        r = requests.get(url, timeout=20)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        data = r.json()
        return data.get("assets", [])
    # 未指定就抓最新 10 個 release
    r = requests.get(GITHUB_REL_API.format(repo=DAO_REPO), timeout=20, params={"per_page": 10})
    r.raise_for_status()
    releases = r.json()
    assets = []
    for rel in releases:
        tag = rel.get("tag_name", "")
        if not tag.startswith("v"):
            continue
        assets.extend(rel.get("assets", []))
    return assets

def candidate_wheel_names(version: str, cu_tag: str, torch_mm: str, py_tag: str, abi_false: bool, plat: str) -> List[str]:
    abi = "cxx11abiFALSE" if abi_false else "cxx11abiTRUE"
    pyabi = f"{py_tag}-{py_tag}"
    return [
        f"flash_attn-{version}+{cu_tag}torch{torch_mm}{abi}-{pyabi}-{plat}.whl",
        # 部分發佈可能無 cu 次版，例如 cu12
        f"flash_attn-{version}+cu12torch{torch_mm}{abi}-{pyabi}-{plat}.whl",
        # 退一步允許 cp311-cp311u 等變體
        f"flash_attn-{version}+{cu_tag}torch{torch_mm}{abi}-{py_tag}-*.whl",
    ]

def select_asset(assets: List[Dict[str, Any]], patterns: List[str]) -> Optional[Dict[str, Any]]:
    import fnmatch
    for pat in patterns:
        for a in assets:
            name = a.get("name","")
            if fnmatch.fnmatch(name, pat):
                return a
    return None

def pip_uninstall():
    run([sys.executable, "-m", "pip", "uninstall", "flash-attn", "-y"], check=False)

def pip_install(target: str):
    run([sys.executable, "-m", "pip", "install", "--no-cache-dir", target])

def plan(version: Optional[str], abi: Optional[str], dry: bool):
    py_tag = detect_python_tag()
    torch_mm, torch_cu, abi_flag = detect_torch()
    plat = detect_platform()
    if plat != "linux_x86_64":
        print(f"[Warning] Auto-handling is currently for Linux x86_64 only. Your platform: {plat}")
    if torch_mm is None:
        print("[Error] Could not import torch. Please install a CUDA-enabled PyTorch first.")
        sys.exit(2)
    cu_tag = pick_cu_tag(torch_cu)
    if not cu_tag:
        print("[Error] Could not detect CUDA version. Ensure your PyTorch is CUDA-enabled or nvcc is installed.")
        sys.exit(2)
    abi_false = True if abi is None else (abi.upper() == "FALSE")
    ver = version or "2.5.8"
    assets = list_release_assets(ver if version else None)
    pats = candidate_wheel_names(ver, cu_tag, torch_mm, py_tag, abi_false, plat)
    asset = select_asset(assets, pats)
    print(json.dumps({
        "python_tag": py_tag,
        "torch_mm": torch_mm,
        "torch_cuda": torch_cu,
        "chosen_cu_tag": cu_tag,
        "abi_FALSE": abi_false,
        "platform": plat,
        "version": ver,
        "found_asset": asset.get("name") if asset else None,
        "download_url": asset.get("browser_download_url") if asset else None,
    }, ensure_ascii=False, indent=2))
    if not asset:
        print("[Hint] No matching wheel found. Try specifying --version or switching --abi TRUE.")
    return asset

def do_install(version: Optional[str], abi: Optional[str], dry: bool):
    asset = plan(version, abi, dry=True)
    if not asset:
        print("[失敗] 無對應 wheel。請變更版本或自行從 Releases 選擇。")
        sys.exit(3)
    url = asset["browser_download_url"]
    if dry:
        print(f"[dry-run] {url}")
        return
    print("[Action] Uninstall existing flash-attn first")
    pip_uninstall()
    print(f"[Download] {url}")
    # 讓 pip 直接裝 URL，避免手動儲存
    pip_install(url)
    print("[Done] flash-attn installation complete")

def doctor():
    py_tag = detect_python_tag()
    torch_mm, torch_cu, abi_flag = detect_torch()
    plat = detect_platform()
    hints = []
    if torch_mm is None:
        hints.append("torch not found. Install a CUDA-enabled PyTorch, e.g. pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
    if plat != "linux_x86_64":
        hints.append("Official wheels primarily target Linux x86_64. Other platforms may require building from source or third-party wheels.")
    if abi_flag is False:
        abi_s = "FALSE"
    elif abi_flag is True:
        abi_s = "TRUE"
    else:
        abi_s = "unknown"
    report = {
        "python_tag": py_tag,
        "platform": plat,
        "torch_mm": torch_mm,
        "torch_cuda": torch_cu,
        "abi": abi_s,
        "advice": hints,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

def main():
    p = argparse.ArgumentParser(prog="qifa", description="Auto-pick the correct flash-attn wheel for your environment")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("plan", help="Show the planned wheel and detected environment")
    sp.add_argument("--version", type=str, default=None, help="flash-attn version. Defaults to 2.5.8 (stable)")
    sp.add_argument("--abi", type=str, choices=["FALSE", "TRUE"], default=None, help="Prefer FALSE by default")
    sp.add_argument("--dry-run", action="store_true")

    si = sub.add_parser("install", help="Download and install the matching wheel")
    si.add_argument("--version", type=str, default=None)
    si.add_argument("--abi", type=str, choices=["FALSE", "TRUE"], default=None)
    si.add_argument("--dry-run", action="store_true")

    su = sub.add_parser("uninstall", help="Uninstall flash-attn")
    sd = sub.add_parser("doctor", help="Check environment and provide guidance")

    args = p.parse_args()
    if args.cmd == "plan":
        plan(args.version, args.abi, args.dry_run)
    elif args.cmd == "install":
        do_install(args.version, args.abi, args.dry_run)
    elif args.cmd == "uninstall":
        pip_uninstall()
    elif args.cmd == "doctor":
        doctor()

if __name__ == "__main__":
    main()