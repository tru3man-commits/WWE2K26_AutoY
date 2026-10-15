"""Run on Windows x64: py -3 build.py [--setup]."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def run(*args):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)


def main():
    if sys.platform != 'win32' or struct.calcsize('P') != 8:
        raise RuntimeError('Build on Windows using 64-bit Python.')
    env = ROOT / '.build-venv'
    if not env.exists():
        run(sys.executable, '-m', 'venv', env)
    python = env / 'Scripts/python.exe'
    run(python, '-m', 'pip', 'install', '--upgrade', 'pip')
    run(python, '-m', 'pip', 'install', 'pyinstaller>=6.21,<7', '-r', 'requirements.txt')
    run(python, '-m', 'unittest', 'discover', '-s', 'tests', '-v')
    run(python, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', 'WWE2K26_AutoY', '--collect-all', 'vgamepad', '--collect-all', 'pynput',
        '--hidden-import', 'pynput.keyboard._win32', '--hidden-import', 'pynput.mouse._win32',
        '--copy-metadata', 'vgamepad', '--copy-metadata', 'pynput', '--copy-metadata', 'mss',
        '--copy-metadata', 'numpy', '--copy-metadata', 'opencv-python-headless',
        '--add-data', 'discover_controllers.ps1:.', 'launcher.py')
    app = ROOT / 'dist/WWE2K26_AutoY'
    shutil.copy2(app / 'WWE2K26_AutoY.exe', app / 'ControllerProbe.exe')
    for name in ('README.txt', 'USER_GUIDE.pdf', 'THIRD_PARTY_NOTICES.txt'):
        shutil.copy2(ROOT / name, app / name)
    with (app / 'build-versions.txt').open('w', encoding='utf-8') as output:
        subprocess.run([str(python), '-m', 'pip', 'freeze'], stdout=output, check=True)
    if '--setup' in sys.argv:
        run('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'installer/build_setup.ps1')
        print('SETUP READY: output/WWE2K26_AutoY_Setup.exe')
        os.startfile(ROOT / 'output')
    else:
        print('APP READY:', app / 'WWE2K26_AutoY.exe')
        os.startfile(app)


if __name__ == '__main__':
    main()
