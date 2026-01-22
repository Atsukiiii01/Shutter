"""
Shutter - Hardware Privacy Monitor
Checks for unauthorized mic/cam access on Win/Mac.
"""

import os, sys, time, signal, logging
import platform, threading, subprocess
from typing import List

# Attempt imports
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    # FIXME: Add auto-install for missing libs?
    print("Error: Missing 'pystray' or 'Pillow'. Run pip install -r requirements.txt")
    sys.exit(1)

# Platform specific imports
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

if IS_WIN:
    try:
        from plyer import notification
    except: pass # Optional dependency

class ShutterApp:
    def __init__(self):
        self.name = "Shutter"
        self._running = True
        self._prev_state = False # tracks if we were active last loop
        self._threats = []
        self._history = []
        
        # Color profile
        self.pal = {'ok': 'green', 'bad': 'red', 'sketchy': 'orange'}
        
        self.log_file = os.path.join(os.path.expanduser("~"), "shutter_security.log")
        self._init_log()
        
        # print(f"DEBUG: App started on {platform.system()}")

    def _init_log(self):
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _draw_icon(self, color_key):
        # 64x64 is standard for tray icons
        w = 64
        c = self.pal.get(color_key, 'green')
        
        img = Image.new('RGB', (w, w), (255, 255, 255))
        d = ImageDraw.Draw(img)
        
        # Draw base
        d.rectangle((0, 0, w, w), fill='white')
        d.ellipse((10, 10, 54, 54), fill=c)
        return img

    def notify(self, title, msg):
        """Dispatches notification based on OS quirks"""
        if IS_MAC:
            # osascript is ugly but reliable
            t_safe = title.replace('"', '')
            m_safe = msg.replace('"', '')
            cmd = f'display notification "{m_safe}" with title "{t_safe}" sound name "Ping"'
            subprocess.run(["osascript", "-e", cmd], check=False)
        elif IS_WIN:
            try:
                notification.notify(title=title, message=msg, app_name=self.name, timeout=5)
            except Exception as e:
                # print(f"Notify failed: {e}") 
                pass

    def gui_dashboard(self, icon, _):
        state_txt = "⚠️ HARDWARE ACTIVE" if self._prev_state else "✅ Secure"
        
        # Get last few logs
        logs = "\n".join(self._history[-5:]) if len(self._history) > 0 else "No events yet."
        
        content = f"Status: {state_txt}\n\nLatest Events:\n{logs}\n\nLog Path:\n{self.log_file}"
        
        if IS_MAC:
            scpt = f'display dialog "{content}" with title "{self.name} Info" buttons {{"Close"}} default button "Close" with icon note'
            subprocess.run(["osascript", "-e", scpt], check=False)
        elif IS_WIN:
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, content, f"{self.name} Info", 0)
            except:
                print(content)

    def set_startup(self, icon, _):
        # TODO: Add Linux support eventually?
        try:
            if IS_MAC: self._mac_autostart()
            if IS_WIN: self._win_autostart()
        except Exception as e:
            self.notify("Error", f"Startup failed: {e}")

    def _mac_autostart(self):
        plist_dest = os.path.expanduser(f"~/Library/LaunchAgents/com.{self.name.lower()}.plist")
        exe = sys.executable
        scr = os.path.realpath(__file__)
        
        # Boilerplate plist
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{self.name.lower()}</string>
    <key>ProgramArguments</key>
    <array><string>{exe}</string><string>{scr}</string></array>
    <key>RunAtLoad</key><true/>
</dict>
</plist>"""
        
        with open(plist_dest, "w") as f: f.write(xml)
        os.system(f"launchctl load {plist_dest}")
        self.notify("Config Updated", "Added to Login Items")

    def _win_autostart(self):
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE)
        cmd = f'"{sys.executable}" "{os.path.realpath(__file__)}"'
        winreg.SetValueEx(k, self.name, 0, winreg.REG_SZ, cmd)
        k.Close()
        self.notify("Config Updated", "Added to Windows Startup")

    def panic_button(self, icon=None, item=None):
        if not self._threats:
            self.notify("Shutter", "Nothing to kill.")
            return

        hit_count = 0
        for t in self._threats:
            # Strip extra labels like ' (Mic)' or '[Exe]'
            proc = t.split(' (')[0].replace('[Exe] ', '')
            
            if "HIDDEN" in proc or "Microphone" in proc: continue # skip system stuff

            print(f"[*] Attempting kill on: {proc}")
            try:
                if IS_MAC:
                    subprocess.run(["pkill", "-f", proc], check=False)
                elif IS_WIN:
                    tgt = proc if proc.endswith(".exe") else f"{proc}.exe"
                    subprocess.run(["taskkill", "/F", "/IM", tgt], check=False)
                
                hit_count += 1
                logging.warning(f"Panic kill: {proc}")
            except:
                print(f"Failed to kill {proc}")

        self.notify("Panic Result", f"Terminated {hit_count} processes.")

    def _scan_mac(self) -> List[str]:
        found = []
        
        # 1. Cam Check
        try:
            # lsof is slow but accurate
            out = subprocess.check_output("lsof -n -P | grep 'CoreMediaIO'", shell=True).decode()
            for l in out.splitlines():
                parts = l.split()
                if parts:
                    n = parts[0].replace(r'\x20', ' ').replace('_', ' ')
                    if "com.apple" not in n and n not in found:
                        found.append(f"{n} (Camera)")
        except: pass

        # 2. Mic Check (Hardware Flag)
        mic_on = False
        try:
            # Checking AppleHDA state
            out = subprocess.check_output(["ioreg", "-c", "AppleHDAEngineInput", "-r"]).decode()
            if '"IOAudioEngineState" = 1' in out: mic_on = True
        except: pass

        if mic_on:
            try:
                # Only grep CoreAudio if hardware is actually hot
                out = subprocess.check_output("lsof -n -P | grep 'CoreAudio'", shell=True).decode()
                for l in out.splitlines():
                    parts = l.split()
                    if parts:
                        n = parts[0].replace(r'\x20', ' ').replace('_', ' ')
                        # Whitelist common system daemons
                        safe = ["com.apple", "WindowServer", "loginwindow", "hidd",
                                "Notificat", "corespeec", "PowerChim", "systemsound", 
                                "ControlCenter", "Siri", "CallHistory", "AudioComponent"]
                        
                        if not any(x in n for x in safe) and n not in found:
                            found.append(f"{n} (Mic)")
            except: pass
            
            # If hardware is on but we found nothing...
            if not any("(Mic)" in x for x in found):
                found.append("⚠️ HIDDEN MIC USAGE")
        
        return found

    def _scan_win(self) -> List[str]:
        res = []
        try:
            import winreg
            # Registry locations for privacy settings
            locs = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam\NonPackaged",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\NonPackaged"
            ]
            
            for path in locs:
                try:
                    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
                    i = 0
                    while True:
                        try:
                            sub = winreg.EnumKey(k, i)
                            sk = winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{path}\\{sub}")
                            val, _ = winreg.QueryValueEx(sk, "LastUsedTimeStop")
                            
                            # 0 means currently active
                            if val == 0:
                                name = sub.split('#')[-1]
                                tag = " (Mic)" if "microphone" in path else " (Cam)"
                                if "NonPackaged" in path: name = f"[Exe] {name}"
                                
                                item = f"{name}{tag}"
                                if item not in res: res.append(item)
                        except OSError: break
                        i += 1
                except: continue
        except ImportError: pass
        return res

    def start_monitor(self, icon):
        print(f"[*] Monitor active. Logfile: {self.log_file}")
        logging.info("Service Started")
        
        while self._running:
            curr_threats = []
            
            if IS_MAC: curr_threats = self._scan_mac()
            elif IS_WIN: curr_threats = self._scan_win()

            self._threats = curr_threats
            active = len(curr_threats) > 0

            # --- VISUAL STATE LOGIC ---
            # Determine target color based on findings
            target_color = 'ok'
            if active:
                target_color = 'bad'
                # Check for suspicious hidden services
                if any("HIDDEN" in t for t in curr_threats): 
                    target_color = 'sketchy'

            # Always update icon to match current state (Fixes the "Green" bug)
            icon.icon = self._draw_icon(target_color)

            # --- NOTIFICATION LOGIC ---
            # Only alert on CHANGE from Safe -> Danger
            if active and not self._prev_state:
                txt = ", ".join(curr_threats)
                ts = time.strftime("%H:%M:%S")
                
                self._history.append(f"[{ts}] 🔴 {txt}")
                logging.warning(f"Detection: {txt}")
                self.notify("PRIVACY ALERT", f"Active: {txt}")
            
            # Log when we return to safe
            elif not active and self._prev_state:
                ts = time.strftime("%H:%M:%S")
                self._history.append(f"[{ts}] 🟢 Safe")
                logging.info("Clear")

            self._prev_state = active
            time.sleep(2)

    def quit(self, icon, _):
        self._running = False
        icon.stop()
        sys.exit(0)

    def run(self):
        # Build menu
        m = pystray.Menu(
            pystray.MenuItem("Dashboard", self.gui_dashboard),
            pystray.MenuItem("⚡ Kill Spy", self.panic_button),
            pystray.MenuItem("Run on Boot", self.set_startup),
            pystray.MenuItem("Exit", self.quit)
        )
        
        icon = pystray.Icon(self.name, self._draw_icon('ok'), "Shutter", m)
        
        # Monitor thread
        t = threading.Thread(target=self.start_monitor, args=(icon,), daemon=True)
        t.start()
        
        icon.run()

if __name__ == "__main__":
    app = ShutterApp()
    try:
        app.run()
    except KeyboardInterrupt:
        sys.exit(0) 