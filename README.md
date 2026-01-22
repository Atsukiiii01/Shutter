# 👁️ Shutter - Privacy Guard

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey?style=for-the-badge)](https://github.com/yourusername/shutter)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Shutter** is a lightweight, background privacy tool that alerts you immediately when an application attempts to access your **Camera** or **Microphone**. 

It runs silently in your system tray and provides native desktop notifications with the exact name of the app spying on you (e.g., *"Zoom"*, *"Google Chrome"*, or *"Unknown"*).

---

## 🚀 Features

* **🕵️ Real-Time Detection:** instantly detects active microphone or camera usage.
* **🔎 Forensic Identification:** Identifies the *specific application name* using the hardware (Windows & macOS).
* **🔔 Native Alerts:** Sends system-level desktop notifications.
* **👻 Silent Mode:** Runs in the system tray (background) without cluttering your taskbar.
* **🎨 Dynamic Icon:** System tray icon changes from **Green (Safe)** to **Red (Danger)** instantly.

---

## 🛠️ Installation

### Prerequisites
* Python 3.10 or higher
* Git

### 1. Clone the Repository
```bash
git clone https://github.com/Atsukiiii01/Shutter.git
cd Shutter
2. Install Dependencies
Bash

pip install -r requirements.txt
(Note: If you are on macOS, use pip3 instead of pip)

💻 Usage
Run the application using Python:

Bash

python Shutter.py
What to Expect:
A Green Circle icon will appear in your System Tray (Windows: Bottom right / macOS: Top right).

The terminal will show [DEBUG] Shutter Monitor Started....

Open an app like Zoom, Discord, or Camera.

The icon will turn Red, and you will receive a notification: "SPYWARE ALERT! Camera/Mic is being used by: Zoom".

🍎 macOS Specifics (Important)
macOS has strict privacy sandboxing.

Permissions: You must allow your Terminal (or VS Code) access to Microphone and Accessibility in System Settings > Privacy & Security.

Running: If the GUI does not appear, try running with:

Bash

pythonw Shutter.py
📦 Building an Executable
To turn this python script into a standalone app (.exe or .app) that you can share with friends:

Windows:

Bash

pyinstaller --onefile --noconsole --icon=icon.ico --name "Shutter" main.py

macOS:

Bash

pyinstaller --onefile --windowed --name "Shutter" main.py

## ⚠️ Important Disclaimer: Educational Use Only

**Please read this section carefully before using the software.**

This tool is developed and distributed for **educational and research purposes only**. It is intended to help developers, researchers, and students understand secuirty and privacy.

* **Authorized Use:** This tool should only be used on systems where you have explicit permission or ownership.
* **Liability:** The developer(s) of Shutter are not responsible for any misuse of this software or any damage caused by using this tool. The user assumes all responsibility for complying with local laws and regulations.

## 🔒 Privacy Policy: No Data Collection

We believe in transparency and privacy.

* **No Logging:** Shutter does not collect, store, or transmit any personal data, system logs, or usage statistics.
* **No External Connections:** This tool operates entirely locally on your machine. It does not connect to any remote command-and-control servers, cloud storage, or third-party APIs unless explicitly configured by the user within the source code.
* **Source Code Transparency:** As an open-source project, you are encouraged to review the code to verify that no data exfiltration mechanisms exist.