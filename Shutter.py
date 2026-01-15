import time
import threading
import platform
import subprocess
import sys
import re
from PIL import Image, ImageDraw
import pystray
from plyer import notification

# --- CONFIGURATION ---
APP_NAME = "Shutter"
SAFE_ICON_COLOR = "green"
WARN_ICON_COLOR = "red"

running = True
last_camera_state = False 

def create_icon(color):
    """Generates a simple 64x64 circle icon dynamically."""
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.rectangle((0, 0, width, height), fill=(255, 255, 255))
    dc.ellipse((10, 10, 54, 54), fill=color)
    return image

def send_mac_notification(title, message):
    """
    Forces a native macOS notification using AppleScript.
    This bypasses the broken 'plyer' library on newer Python versions.
    """
    safe_title = title.replace('"', '')
    safe_message = message.replace('"', '')
    
    # AppleScript command to display notification
    cmd = f'display notification "{safe_message}" with title "{safe_title}" sound name "Ping"'
    
    try:
        subprocess.run(["osascript", "-e", cmd], check=False)
    except Exception as e:
        print(f"[ERROR] Could not send notification: {e}")

def get_windows_camera_apps():
    apps = []
    if platform.system() != "Windows":
        return apps

    import winreg
    base_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
    ]
    
    for path in base_paths:
        try:
            h_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(h_key, i)
                    subkey_path = f"{path}\\{subkey_name}"
                    sub_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey_path)
                    
                    stop_time, _ = winreg.QueryValueEx(sub_key, "LastUsedTimeStop")
                    
                    if stop_time == 0:
                        readable_name = subkey_name
                        if "#" in readable_name:
                            readable_name = readable_name.split('#')[-1]
                        if "!" in readable_name:
                            readable_name = readable_name.split('!')[0]
                        if readable_name not in apps:
                            apps.append(readable_name)
                except OSError:
                    pass
                i += 1
        except Exception:
            pass
    return apps

def get_mac_camera_apps():
    """
    Uses 'lsof' to find which app holds the camera/mic handle.
    """
    detected_apps = []
    
    # 1. Fast Check: General Hardware Status
    try:
        cmd = ["ioreg", "-c", "AppleHDAEngineInput", "-r"]
        output = subprocess.check_output(cmd).decode("utf-8")
        if '"IOAudioEngineState" = 1' in output:
            # If we know mic is on but not WHICH app, we start with this:
            pass 
    except:
        pass

    # 2. Deep Check: Specific App Names via lsof
    try:
        # Search for CoreMediaIO (Camera) or AppleHDA (Mic) usage
        cmd = "lsof -n -P | grep -E 'CoreMediaIO|AppleHDA'"
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        
        for line in output.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) > 0:
                    raw_name = parts[0]
                    # CLEANUP: Remove weird characters like \x20 (spaces)
                    clean_name = raw_name.replace(r'\x20', ' ').replace('_', ' ')
                    
                    # Filter out system processes
                    if clean_name not in detected_apps and "com.apple" not in clean_name and "WindowServer" not in clean_name:
                        detected_apps.append(clean_name)
    except subprocess.CalledProcessError:
        pass 
    except Exception as e:
        print(f"Mac Check Error: {e}")

    return detected_apps

def monitor_loop(icon):
    global last_camera_state
    print("[DEBUG] Shutter Monitor Started... (Waiting for camera usage)")
    
    while running:
        active_apps = []
        
        if platform.system() == "Windows":
            active_apps = get_windows_camera_apps()
        elif platform.system() == "Darwin": # macOS
            active_apps = get_mac_camera_apps()

        is_active = len(active_apps) > 0

        # --- DEBUG PRINT ---
        if is_active:
            print(f"\r[!] DANGER: Camera/Mic used by: {active_apps}   ", end="", flush=True)
        else:
            print(f"\r[+] Secure.                                  ", end="", flush=True)
        # -------------------

        if is_active and not last_camera_state:
            # TRIGGER ALERT
            icon.icon = create_icon(WARN_ICON_COLOR)
            
            app_list = ", ".join(active_apps)
            if not app_list: 
                app_list = "Unknown App"
            
            # NOTIFICATION LOGIC
            title = "SPYWARE ALERT!"
            message = f"Camera/Mic is being used by: {app_list}"
            
            if platform.system() == "Darwin":
                send_mac_notification(title, message)
            else:
                try:
                    notification.notify(
                        title=title,
                        message=message,
                        app_name=APP_NAME,
                        timeout=5
                    )
                except Exception:
                    pass
            
        elif not is_active and last_camera_state:
            # RESET TO SAFE
            icon.icon = create_icon(SAFE_ICON_COLOR)

        last_camera_state = is_active
        time.sleep(2) 

def quit_app(icon, item):
    global running
    running = False
    icon.stop()
    sys.exit()

def main():
    icon_image = create_icon(SAFE_ICON_COLOR)
    menu = pystray.Menu(pystray.MenuItem("Quit", quit_app))
    
    icon = pystray.Icon(APP_NAME, icon_image, f"{APP_NAME}: Protected", menu)
    
    t = threading.Thread(target=monitor_loop, args=(icon,))
    t.daemon = True
    t.start()
    
    icon.run()

if __name__ == "__main__":
    main()