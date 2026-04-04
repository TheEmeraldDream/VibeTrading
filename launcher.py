"""
AuctionHouse launcher — opens run.bat in a new console window.
Compiled to AuctionHouse.exe via build_exe.bat using PyInstaller.
"""
import subprocess
import sys
from pathlib import Path


def main():
    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    run_bat = exe_dir / "run.bat"

    if not run_bat.exists():
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"run.bat not found in:\n{exe_dir}\n\nKeep AuctionHouse.exe in the same folder as run.bat.",
                "Auction House",
                0x10,  # MB_ICONERROR
            )
        except Exception:
            pass
        return

    subprocess.Popen(["cmd", "/c", str(run_bat)], creationflags=subprocess.CREATE_NEW_CONSOLE)


if __name__ == "__main__":
    main()
