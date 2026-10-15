WWE 2K26 AutoY - Managed controller edition 0.2.2

FOR PLAYERS
Open the installed "User guide" shortcut for the complete English tutorial.

1. Run WWE2K26_AutoY_Setup.exe. Finish any official driver installers that open; choose Restart later
   inside those installers so AutoY Setup can finish first.
   Restart Windows if requested. Python and OCR are not required.
2. Close the game and old AutoY/AutoDefense/controller-emulator instances.
   Connect ONE physical Xbox controller via Bluetooth or USB.
3. Open AutoY. On first use, select the physical controller and click
   "Use this controller". AutoY will manage its visibility from now on.
4. Click Start. If asked, reconnect the controller and click OK.
5. Once AutoY says Running and its input values move, launch the game.
   Assign the virtual controller to your character. Use your physical pad normally.
6. Ctrl+Alt+Y sends a manual test Y while AutoY is running.
7. Stop or Exit releases the virtual controller and unhides the physical one.
   Reconnect it or restart the game if the game has cached the previous devices.

RESTORE CONTROLLER
Click "Restore controller" inside AutoY, or use the Start menu shortcut of
that name after closing AutoY. A watchdog also restores visibility when the
main process exits unexpectedly. A small per-user sign-in recovery command
retries an interrupted session after a Windows restart. It does not start
AutoY or hide the controller on its own.
If HidHide Configuration Client is open, close it so recovery can access the
driver. A forcibly killed watchdog or power loss cannot restore immediately;
use the shortcut or sign in to Windows again. Errors remain in recovery.log.

AUTOMATIC MANAGEMENT
Selecting a controller transfers management of that controller's listed
paths to AutoY. Even if it was previously hidden manually, it is unhidden
when AutoY stops. Other controller entries and application registrations are
preserved. Inverse HidHide mode is not overwritten; AutoY will explain that
normal mode is required. Do not change HidHide settings during an AutoY session.
A separate, non-whitelisted ControllerProbe.exe checks that XInput is hidden
from ordinary applications before AutoY creates its virtual controller.
Steam or a game previously whitelisted manually may still see the physical
controller: remove that game's/Steam's old whitelist entry if necessary.

SPEED AND SCOPE
Zero deliberate scan interval; 1 ms requested output-loop delay.
Actual latency depends on capture, CPU load, Windows scheduling and the game.
Automatic Y only. Physical A/B/X and all other mapped inputs pass through.
The original yellow-circle detector is retained. It is not letter OCR and
can trigger on unrelated yellow circles. Narrow the screen region if needed.
Screen region is relative to the first monitor: 0,0,1,1 means the full monitor.
Only one physical Xbox XInput controller is supported in this preview.
Third-party Xbox-compatible pads and multiple simultaneous controllers are
not covered by automatic hardware discovery. Re-select after changing
between USB and Bluetooth, because Windows uses different device paths.

DATA
%LOCALAPPDATA%\WWE2K26_AutoY
  discovery.json           controller discovery details
  latest.log               application errors
  recovery.log             watchdog / sign-in recovery errors
  controller.json          selected physical controller paths
  controller-session.json  recovery journal (exists during managed sessions)
  autoy_config.json        screen region

FOR THE BUILDER (THIS SOURCE ZIP)
Run BUILD_SETUP.bat on Windows x64 with 64-bit Python installed.
It builds the app, downloads the official signed driver installers and uses
Inno Setup 6.3 or newer to produce output\WWE2K26_AutoY_Setup.exe.
If Inno Setup is missing, the script installs it using Windows Package Manager.
If winget is unavailable, install Inno Setup from https://jrsoftware.org/isdl.php
and rerun the build. Internet is needed to build; the resulting setup includes
the drivers and Python runtime for offline installation.
BUILD_EXE.bat builds just dist\WWE2K26_AutoY for an already configured PC.
Keep that entire folder together, including ControllerProbe.exe and _internal.
Do not whitelist ControllerProbe.exe in HidHide.

VALIDATION STATUS
The source, simulated recovery lifecycle, and physical/automatic button merge
have been checked on Linux. The Windows EXE, installer, Bluetooth discovery,
PnP re-enumeration and real game timing still require testing on Windows.
A successful source test is not proof of working Windows drivers or gameplay.
Before sharing a paid release, verify normal start/stop, forced process exit,
controller reconnection, reboot recovery and a clean-machine install.

OFFICIAL REFERENCES
https://docs.nefarius.at/projects/HidHide/CLI-Usage/
https://github.com/nefarius/HidHide/releases/tag/v1.5.230.0
https://github.com/nefarius/ViGEmBus/releases/tag/v1.22.0
https://pyinstaller.org/en/stable/operating-mode.html

0.2.2: Startup checks, controller discovery and controller selection now run
in a background worker. The window stays responsive and displays elapsed
time. Unrelated PnP devices are filtered before expensive property queries.

0.2.2 discovery also checks HardwareID and XInput service metadata, handles
Bluetooth endpoint names, and records the inventory in discovery.json.
Update: rebuild BUILD_SETUP.bat, close the old AutoY, and install the new
setup over the previous version. Existing driver installs are reused.

0.2.2 fix: Game-controller usage markers are now checked in both HardwareID
and CompatibleID. This handles the observed Bluetooth Xbox record with
an empty service, null CompatibleID and game usage in HardwareID.
