@echo off
setlocal
cd /d "%~dp0"

echo Building AuctionHouse.exe...

:: ── Use backend venv (set up by run.bat) ────────────────────────────
if not exist "backend\venv\Scripts\activate.bat" (
    echo ERROR: Run run.bat first to create the virtual environment.
    pause
    exit /b 1
)
call backend\venv\Scripts\activate.bat

:: ── Install build tools ──────────────────────────────────────────────
echo Installing build dependencies...
pip install pyinstaller pillow -q
if errorlevel 1 (
    echo ERROR: Failed to install build tools.
    pause
    exit /b 1
)

:: ── Generate icon ────────────────────────────────────────────────────
echo Generating icon...
python -c "
from PIL import Image, ImageDraw

sizes = [256, 128, 64, 48, 32, 16]
images = []
for size in sizes:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = max(1, size // 8)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(17, 17, 17, 255))
    color = (0, 217, 126, 255)
    lw = max(1, size // 13)
    x0 = size // 5
    y1, y2, y3 = size // 3, size // 2, int(size * 0.67)
    draw.line([(x0, y1), (size - x0,        y1)], fill=color, width=lw)
    draw.line([(x0, y2), (int(size * 0.65), y2)], fill=color, width=lw)
    draw.line([(x0, y3), (int(size * 0.72), y3)], fill=color, width=lw)
    images.append(img)
images[0].save('AuctionHouse.ico', format='ICO', append_images=images[1:],
               sizes=[(s, s) for s in sizes])
print('Icon created.')
"
if errorlevel 1 (
    echo ERROR: Icon generation failed.
    pause
    exit /b 1
)

:: ── Build exe ────────────────────────────────────────────────────────
echo Compiling AuctionHouse.exe...
pyinstaller --onefile --windowed --icon=AuctionHouse.ico --name=AuctionHouse launcher.py
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

:: ── Move exe to root ─────────────────────────────────────────────────
copy /y dist\AuctionHouse.exe . >nul

:: ── Cleanup ──────────────────────────────────────────────────────────
rmdir /s /q build dist __pycache__ 2>nul
del AuctionHouse.spec AuctionHouse.ico 2>nul

echo.
echo  AuctionHouse.exe is ready. Place it in the same folder as run.bat and double-click to launch.
echo.
pause
