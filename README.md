# WWE 2K26 AutoY

Windows utility that detects the existing yellow-circle Y prompt and sends an
automatic Y press through a virtual Xbox controller. It reads one physical
Xbox controller and forwards its inputs through the virtual controller.

## For players

AutoY is a Windows x64 preview. It supports automatic Y only. It does not use
OCR and may react to unrelated yellow circles on screen.

The English user guide is included as `USER_GUIDE.pdf`. The compiled setup
executable is not included in this repository. If you already received the
installer, run it and follow the included setup instructions. Close the game
before installing or changing controller settings.

## Requirements

- Windows 10 version 2004 (build 19041) or newer, x64
- One Xbox controller connected by USB or Bluetooth
- ViGEmBus and HidHide drivers; the installer launches their official
  installers when they are missing

Python and OCR are not required to run the installed application.

## Build on Windows

1. Install 64-bit Python 3.12 or newer and ensure `py -3` works in PowerShell.
2. Run `BUILD_SETUP.bat` from this folder.
3. Complete the official driver-installation steps if prompted. If Inno Setup
   is missing, the build script attempts to install it with `winget`.
4. The setup file is written to `output\WWE2K26_AutoY_Setup.exe`.

The build requires an internet connection to download dependencies and the
official signed driver installers. `BUILD_EXE.bat` builds the application
folder without creating a Setup installer.

## Validation

The included unit tests cover the controller state handling, background
dispatch, and input merging:

```powershell
py -3 -m unittest discover -s tests -v
```

The source tests do not validate Windows driver installation, Bluetooth
device discovery, or input in WWE 2K26. See `VALIDATION.txt` for the current
test status and limitations.

## Safety and controller recovery

AutoY changes HidHide visibility for the physical controller selected by the
user while a managed session is active. Stop AutoY or use the installed
**Restore controller** shortcut to restore visibility. Close HidHide
Configuration Client while AutoY is managing the controller.

## Third-party components

See `THIRD_PARTY_NOTICES.txt` for project links and license references.
ViGEmBus and HidHide installers are downloaded unmodified from their official
Nefarius releases and display their own license terms during installation.

## Distribution

Do not add the compiled Setup executable to the Git history. This repository
is public, so anyone can view and download the source and build the program.
Public GitHub Release assets are also free to download. Use a payment-gated
storefront for any paid installer distribution.
