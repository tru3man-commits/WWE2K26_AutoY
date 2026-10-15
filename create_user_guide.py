from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, KeepTogether, HRFlowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'USER_GUIDE.pdf'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
pdfmetrics.registerFont(TTFont('DV', FONT))
pdfmetrics.registerFont(TTFont('DV-Bold', BOLD))
NAVY = colors.HexColor('#252525')
INK = colors.HexColor('#292929')
MUTED = colors.HexColor('#666666')
TEAL = colors.HexColor('#333333')
PALE = colors.white
LIGHT = colors.HexColor('#F3F3F3')
AMBER = colors.white
RED = colors.HexColor('#333333')
GREEN = colors.HexColor('#333333')
PAGE_W, PAGE_H = A4

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleX', fontName='DV-Bold', fontSize=23, leading=29, textColor=NAVY, spaceAfter=5))
styles.add(ParagraphStyle(name='SubX', fontName='DV', fontSize=10, leading=14, textColor=MUTED))
styles.add(ParagraphStyle(name='H1X', fontName='DV-Bold', fontSize=18, leading=23, textColor=NAVY, spaceBefore=0, spaceAfter=7))
styles.add(ParagraphStyle(name='H2X', fontName='DV-Bold', fontSize=11, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle(name='BodyX', fontName='DV', fontSize=9.4, leading=14, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name='SmallX', fontName='DV', fontSize=8, leading=11, textColor=MUTED, spaceAfter=3))
styles.add(ParagraphStyle(name='BulletX', fontName='DV', fontSize=9.2, leading=13.5, leftIndent=12, firstLineIndent=-8, bulletIndent=1, textColor=INK, spaceAfter=3))
styles.add(ParagraphStyle(name='CallX', fontName='DV', fontSize=9.2, leading=13.5, textColor=INK, leftIndent=10, rightIndent=5, spaceBefore=3, spaceAfter=7))
styles.add(ParagraphStyle(name='CellX', fontName='DV', fontSize=8.4, leading=11.5, textColor=INK))
styles.add(ParagraphStyle(name='CellBoldX', fontName='DV-Bold', fontSize=8.4, leading=11.5, textColor=NAVY))
styles.add(ParagraphStyle(name='LabelX', fontName='DV-Bold', fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=3))

P = lambda txt, style='BodyX': Paragraph(txt, styles[style])
def bullets(items):
    return [Paragraph('&bull; ' + x, styles['BulletX']) for x in items]
def callout(text, bg=PALE):
    return Paragraph('<b>Note:</b> ' + text, styles['CallX'])

def table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
    cmds = [('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('LINEBELOW',(0,0),(-1,-1),0.35,colors.HexColor('#D2D2D2'))]
    if header:
        cmds += [('BACKGROUND',(0,0),(-1,0),LIGHT),
                 ('LINEABOVE',(0,0),(-1,0),0.7,colors.HexColor('#888888')),
                 ('LINEBELOW',(0,0),(-1,0),0.7,colors.HexColor('#888888'))]
    t.setStyle(TableStyle(cmds))
    return t

def footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(colors.HexColor('#D2D2D2'))
        canvas.line(22*mm, 15*mm, PAGE_W-22*mm, 15*mm)
        canvas.setFont('DV', 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(22*mm, 10*mm, 'WWE 2K26 AutoY - User Guide - Version 0.2.2')
        canvas.drawRightString(PAGE_W-22*mm, 10*mm, str(doc.page))
    canvas.restoreState()

doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=22*mm, leftMargin=22*mm,
                        topMargin=20*mm, bottomMargin=22*mm,
                        title='WWE 2K26 AutoY - Complete User Guide', author='AutoY')
story=[]
# 1 Title and quick overview
story += [Spacer(1,10*mm),P('WWE 2K26 AutoY','TitleX'),
          P('Setup and user guide - Version 0.2.2','SubX'),
          Spacer(1,4*mm),HRFlowable(width='100%', thickness=0.7, color=colors.HexColor('#888888')),
          Spacer(1,8*mm),P('What AutoY does','H1X'),
          P('AutoY watches the first monitor for the game\'s small yellow circular Y prompt. When it sees the prompt, it presses Y on a virtual Xbox controller. At the same time, it forwards your physical Xbox controller\'s buttons and sticks to that same virtual controller.'),
          callout('In the game, assign the virtual Xbox controller as your player controller. Keep using your physical Xbox pad in your hands.'),
          Spacer(1,4*mm),P('Before you start','H2X')]
story += bullets([
    '<b>Automatic input:</b> Y only. Physical A, B, X, other mapped buttons, triggers and both sticks pass through.',
    '<b>Supported setup:</b> Windows 10 (build 19041) or newer, 64-bit, and one physical Xbox XInput controller connected by Bluetooth or USB.',
    '<b>All-in-one installer:</b> One Setup.exe installs AutoY and installs ViGEmBus and HidHide if they are missing. No separate driver downloads, Python, or OCR are needed.',
    '<b>Scope:</b> Detection uses the original yellow-circle image detector, not OCR. A similar yellow circle elsewhere on screen can trigger it.',
])
story += [Spacer(1,4*mm),P('Quick start','H2X'),
          P('<b>Install Setup</b> &gt; select your controller &gt; click Start &gt; launch the game and assign the virtual controller.'),
          PageBreak()]
# 2 Install
story += [P('1. Install the all-in-one Setup','H1X'),P('The single WWE2K26_AutoY_Setup.exe installs the AutoY app and the two drivers it needs: ViGEmBus and HidHide. If the drivers are already installed, Setup reuses them. You do not need to download or install them separately.'),P('Installation steps','H2X')]
story += bullets([
    'Close WWE 2K26, Steam controller tools, other controller emulators, and any older AutoY/AutoDefense window.',
    'Run <b>WWE2K26_AutoY_Setup.exe</b> and approve the Windows administrator prompt. The Setup package contains AutoY and the driver installers.',
    'If ViGEmBus or HidHide is missing, its official installer opens during Setup. Accept its license and install prompts, then return to AutoY Setup. If it offers Restart later, choose that so the main Setup can finish.',
    'Let AutoY Setup finish. Restart Windows afterward if a driver requested a restart.',
    'Open <b>WWE 2K26 AutoY</b> from the Start menu. You do not need Python, OCR, a separate HidHide setup, or HidHideCLI commands.',
])
story += [callout('Use the one Setup.exe for everything. Do not run separate HidHide or ViGEmBus downloads or enter manual HidHide commands.',AMBER),Spacer(1,6*mm),P('What Setup installs','H2X')]
rows=[[P('Component','CellBoldX'),P('Purpose','CellBoldX')],
      [P('AutoY','CellBoldX'),P('Finds the Y prompt and combines the physical pad input with Auto Y.','CellX')],
      [P('ViGEmBus','CellBoldX'),P('Creates the virtual Xbox 360 controller that the game will use.','CellX')],
      [P('HidHide','CellBoldX'),P('Hides the selected physical controller from ordinary games while AutoY is active, preventing duplicate controller assignment.','CellX')]]
story.append(table(rows,[36*mm,130*mm]))
story += [Spacer(1,5*mm),P('The installer does not uninstall these shared drivers when AutoY is removed. Other controller software may rely on them.','SmallX'),PageBreak()]
# 3 select controller and auto hid
story += [P('2. Select your controller','H1X'),P('AutoY needs to know which physical Xbox pad it should manage. Connect only the pad you want to use before selecting it.'),P('First-time setup','H2X')]
story += bullets([
    'Connect one physical Xbox controller over Bluetooth or USB. If you change between Bluetooth and USB later, select it again because Windows may expose different device paths.',
    'Open AutoY and click <b>Select controller...</b>. Wait for discovery to finish.',
    'Choose your physical Xbox controller and click <b>Use this controller</b>. Do not select a virtual pad or a controller created by another emulator.',
    'AutoY saves the selected device paths in your user profile. You normally only need to repeat selection after changing connection type or controller.',
])
story += [P('Automatic controller hiding','H2X'),P('AutoY configures HidHide for the controller you select. You do not need to open HidHide Configuration Client, manually hide the pad, or add AutoY to the allow-list yourself. AutoY handles those settings when needed so the game sees one virtual pad while AutoY can read the physical controller.'),
          table([[P('When','CellBoldX'),P('What happens','CellBoldX')],
                 [P('AutoY is stopped','CellBoldX'),P('The selected physical controller is available to Windows and games.','CellX')],
                 [P('You click Start','CellBoldX'),P('AutoY prepares recovery, hides the selected physical controller paths, checks that ordinary apps cannot see them, then starts virtual-controller forwarding.','CellX')],
                 [P('You click Stop / Exit','CellBoldX'),P('The virtual controller is released and AutoY unhides the selected physical controller.','CellX')]], [42*mm,124*mm]),
          Spacer(1,5*mm),callout('Keep HidHide Configuration Client closed while AutoY is starting, stopping, or restoring. The configuration client can hold the driver in a way that prevents AutoY from applying changes.',AMBER),
          Spacer(1,5*mm),P('Important behavior','H2X')]
story += bullets([
    'Selecting a controller transfers its visibility management to AutoY. When AutoY stops, that selected controller is made visible again, even if you had hidden it manually before.',
    'Other HidHide device entries and app registrations are preserved. AutoY adds itself to the allowed-app list automatically. Do not add the game or ControllerProbe.exe to that list.',
    'Do not change HidHide settings while AutoY is running. Inverse mode is not supported; AutoY will report if it is enabled.',
])
story.append(PageBreak())
# 4 game flow
story += [P('3. Start the game the right way','H1X'),P('The order matters because games often cache which controllers were connected when they started.'),P('Recommended play session','H2X')]
rows=[[P('Step','CellBoldX'),P('Action','CellBoldX'),P('Expected result','CellBoldX')],
      [P('1','CellBoldX'),P('Connect the selected physical Xbox controller.','CellX'),P('Windows sees the pad; AutoY can read its input.','CellX')],
      [P('2','CellBoldX'),P('Open AutoY and click Start.','CellX'),P('Status says Running; input readouts change when you move sticks or press buttons.','CellX')],
      [P('3','CellBoldX'),P('Launch WWE 2K26 after AutoY is Running.','CellX'),P('The game sees the virtual Xbox controller.','CellX')],
      [P('4','CellBoldX'),P('Assign the virtual controller to your player/character in the game.','CellX'),P('Use the physical pad normally; its inputs are forwarded to the virtual pad.','CellX')],
      [P('5','CellBoldX'),P('When finished, stop AutoY before disconnecting the pad.','CellX'),P('Physical pad becomes visible again.','CellX')]]
story.append(table(rows,[14*mm,70*mm,82*mm]))
story += [Spacer(1,5*mm),P('Verify the setup before a match','H2X')]
story += bullets([
    'In AutoY, check the status says <b>Running</b>. The physical input readouts should react to your sticks and buttons.',
    'Use <b>Ctrl+Alt+Y</b> while AutoY is running to send a short manual Y test. This tests the virtual output path without waiting for a screen prompt.',
    'If the game had already started before AutoY, close and relaunch the game after AutoY is running. Games may not refresh their controller list live.',
    'If the game still lists two pads, stop AutoY, close the game, reconnect the physical controller, then start AutoY and launch the game again.',
])
story += [callout('If the game detects only the virtual pad, that is expected. AutoY reads your real controller and forwards its input through the virtual pad.'),Spacer(1,5*mm),P('Stop safely','H2X'),P('Click Stop before closing the game or disconnecting the controller. AutoY releases the virtual pad and restores visibility of the selected physical pad. If the game cached the old controller list, reconnect the pad and restart the game.'),PageBreak()]
# 5 detection screen region
story += [P('4. Detection and screen region','H1X'),P('AutoY looks for the game\'s yellow circular Y cue in a screen capture. It does not read the letter with OCR. The scan loop has no deliberate wait; real response time still depends on capture, CPU load, Windows scheduling, and the game.'),P('Use the full first monitor','H2X'),P('The default region covers the full first monitor: left 0, top 0, right 1, bottom 1. The region uses fractions of that monitor, where 0 is the left/top edge and 1 is the right/bottom edge.'),P('To change it','H2X')]
story += bullets([
    'Click <b>Screen region...</b> in AutoY.',
    'Enter left, top, right, and bottom values between 0 and 1. Left must be less than right; top must be less than bottom.',
    'Use 0, 0, 1, 1 to monitor the whole first display. A smaller region can reduce false triggers if the same yellow circular shape appears elsewhere.',
    'Keep the game prompt on the first monitor. AutoY currently captures only the first monitor; it does not combine multiple displays.',
])
story += [P('Examples','H2X'),table([[P('Goal','CellBoldX'),P('Left / top / right / bottom','CellBoldX')],
                 [P('Full first monitor','CellX'),P('0 / 0 / 1 / 1','CellX')],
                 [P('Center half of the screen','CellX'),P('0.25 / 0.25 / 0.75 / 0.75','CellX')],
                 [P('Right-side region','CellX'),P('0.50 / 0 / 1 / 1','CellX')]], [60*mm,106*mm]),
          Spacer(1,5*mm),callout('A tight region can miss prompts that appear outside it. Start with the full screen; narrow it only if you see false positives.',AMBER),Spacer(1,5*mm),P('What “ultra-fast” means','H2X'),P('AutoY requests continuous scanning without a deliberate scan interval and presses the virtual Y button for a short pulse. This minimizes software delay, but cannot guarantee a fixed millisecond response: screenshot capture and game/Windows timing vary by PC.'),PageBreak()]
# 6 troubleshooting
story += [P('5. Troubleshooting','H1X'),P('Try the matching steps in order. Keep the game closed until AutoY reports Running.'),
          table([[P('Symptom','CellBoldX'),P('Try this','CellBoldX')],
                 [P('No controller found','CellBoldX'),P('Confirm the pad is connected in Windows. Close other emulators and connect only one physical Xbox pad. Open Select controller again. If it still fails, save discovery.json for support.','CellX')],
                 [P('Start says a physical controller is still visible','CellBoldX'),P('Close HidHide Configuration Client and the game. Re-select the controller. Switch the Xbox pad off/on (or unplug/reconnect USB) when prompted, then retry. Close Steam Input or other remappers temporarily.','CellX')],
                 [P('Controller readouts do not move','CellBoldX'),P('Check Bluetooth/USB connection and battery. Confirm the selected pad is the one in your hands. Stop and reconnect it, then retry. If driver installation was just completed, restart Windows.','CellX')],
                 [P('Game sees two controllers or assigns the wrong one','CellBoldX'),P('Stop AutoY and close the game. Ensure only one physical Xbox controller is connected. Start AutoY first, then relaunch the game and assign the virtual Xbox controller. Remove an old manual HidHide allow-list entry for the game or Steam if it makes the physical device visible.','CellX')],
                 [P('Y does not trigger','CellBoldX'),P('Confirm the prompt is the yellow circular Y icon and appears on the first monitor. Use Ctrl+Alt+Y to test the output path. Check the screen region covers the prompt. Similar yellow circles can also trigger.','CellX')],
                 [P('Physical pad stops working after closing/crash','CellBoldX'),P('Use Restore controller in AutoY or the Start menu. Close HidHide Configuration Client first. After a forced shutdown, sign in again and run Restore controller if needed.','CellX')],
                 [P('HidHide inverse mode error','CellBoldX'),P('AutoY requires normal HidHide mode. Open HidHide Configuration Client, turn off inverse mode, close the client, then click Restore controller and try again.','CellX')]], [48*mm,118*mm]),
          Spacer(1,5*mm),callout('AutoY includes a recovery watchdog. If the main app exits unexpectedly, it attempts to restore the selected controller. The Restore controller shortcut is the manual recovery path.',PALE),PageBreak()]
# 7 recovery privacy uninstall
story += [P('6. Restore, uninstall, and support','H1X'),P('Restore the physical controller','H2X'),P('If the controller is hidden or unavailable, close AutoY and HidHide Configuration Client, then use <b>Restore controller</b> in the app or the Start menu. If Windows or the controller has just restarted, sign in and run Restore controller. Recovery does not start AutoY or hide the pad by itself.'),P('Uninstall','H2X'),P('Use Windows Settings &gt; Apps to uninstall WWE 2K26 AutoY. The uninstaller attempts to restore the selected controller first. ViGEmBus and HidHide are shared system drivers and are left installed, because other software may use them. Remove them separately only if you know no other app needs them.'),P('Logs and local data','H2X'),P(r'AutoY stores its settings and diagnostic files in <font name="DV-Bold">%LOCALAPPDATA%\WWE2K26_AutoY</font>. Useful files include:')]
rows=[[P('File','CellBoldX'),P('Contains','CellBoldX')],
      [P('discovery.json','CellBoldX'),P('Windows controller discovery details. May contain device identifiers; review before sharing.','CellX')],
      [P('latest.log','CellBoldX'),P('Most recent application errors.','CellX')],
      [P('recovery.log','CellBoldX'),P('Watchdog and sign-in recovery errors.','CellX')],
      [P('controller.json','CellBoldX'),P('Selected device paths. May contain identifying details.','CellX')],
      [P('autoy_config.json','CellBoldX'),P('Screen region and detection settings.','CellX')]]
story.append(table(rows,[47*mm,119*mm]))
story += [Spacer(1,5*mm),P('If you contact the publisher','H2X')]
story += bullets([
    'Include AutoY version 0.2.2, Windows version, controller model, Bluetooth or USB, and the exact status/error text.',
    'Say whether the manual Ctrl+Alt+Y test works and whether physical input readouts move.',
    'Attach latest.log and, if discovery is failing, discovery.json. Review these files first and remove device identifiers or other personal details you do not want to share.',
])
story += [Spacer(1,5*mm),HRFlowable(width='100%', thickness=0.8, color=colors.HexColor('#D6DFE7')),Spacer(1,4*mm),P('Known limits','H2X'),P('This preview supports one physical Xbox XInput controller, automatic Y detection, and the first monitor. It does not automatically detect A/B/X prompts, guarantee game compatibility, or guarantee a fixed response time. Test a new setup in a low-stakes practice mode before relying on it.'),Spacer(1,3*mm),P('WWE 2K26 and Xbox are trademarks of their respective owners. AutoY is an independent community utility and is not affiliated with or endorsed by the game publisher or Microsoft.','SmallX')]
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
