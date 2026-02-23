import customtkinter as ctk
import os
import subprocess
import sys
import tkinter.messagebox as messagebox
import requests
from datetime import datetime, timezone

# ==================== FIREBASE CONFIG ====================
PROJECT_ID = "zerocrow22a01"
API_KEY = "AIzaSyClDD1hKoBCA5MI4AYw_Z0-oGYkI4wwh5c"
collection0 = "user_requests"                            # Register
collection1 = "sample"                                    # Login app collection (also need to create firestore rules for this)
initialize_file="sample.py"                               # Main application file to run after login

# Firestore REST Paths
def firestore_get_url(collection, doc_id):
    return f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/{collection}/{doc_id}?key={API_KEY}"

def firestore_set_url(collection, doc_id):
    return f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/{collection}/{doc_id}?key={API_KEY}"


# ==================== GET MOTHERBOARD SERIAL (Linux/Windows) ====================
def get_motherboard_serial():
    """Attempt to determine the board serial number on Linux or Windows.

    On Linux we try dmidecode first (requires sudo), then fall back to
    reading /sys/class/dmi files.  On Windows we first call wmic and then
    (`powershell`) as a fallback.  Placeholder values and empty strings are
    ignored to avoid OEM defaults.
    """
    try:
        if sys.platform.startswith("win"):
            # ---- Windows path ----
            # Method 1: wmic utility (most Win10+ have it)
            try:
                output = subprocess.check_output(
                    ["wmic", "baseboard", "get", "serialnumber"],
                    text=True
                ).strip().splitlines()
                if len(output) >= 2:
                    sn = output[1].strip()
                    if sn and sn.lower() not in [
                        "to be filled by o.e.m.",
                        "none",
                        "o.e.m.",
                        "not specified",
                        "default string",
                    ]:
                        return sn
            except Exception:
                pass

            # Method 2: powershell WMI query as a secondary fallback
            try:
                result = subprocess.check_output(
                    [
                        "powershell",
                        "-Command",
                        "(Get-WmiObject Win32_BaseBoard).SerialNumber",
                    ],
                    text=True,
                ).strip()
                if result and result.lower() not in [
                    "to be filled by o.e.m.",
                    "none",
                    "o.e.m.",
                    "not specified",
                    "default string",
                ]:
                    return result
            except Exception:
                pass

            return "UNKNOWN_SERIAL"
        else:
            # ---- Linux path ----
            # Method 1: dmidecode
            try:
                result = subprocess.check_output(
                    ["sudo", "dmidecode", "-s", "baseboard-serial-number"],
                    text=True,
                ).strip()
                if result and result.lower() not in [
                    "to be filled by o.e.m.",
                    "none",
                    "o.e.m.",
                    "not specified",
                    "default string",
                ]:
                    return result
            except Exception:
                pass

            # Method 2: Read from sys filesystem
            paths = [
                "/sys/class/dmi/id/board_serial",
                "/sys/class/dmi/id/product_serial",
                "/sys/class/dmi/id/chassis_serial",
            ]
            for path in paths:
                if os.path.exists(path):
                    with open(path) as f:
                        serial = f.read().strip()
                        if serial and serial.lower() not in [
                            "to be filled by o.e.m.",
                            "none",
                            "0",
                            "default string",
                        ]:
                            return serial

            return "UNKNOWN_SERIAL"
    except Exception as e:
        print(f"Error reading serial: {e}")
        return "UNKNOWN_SERIAL"


MOTHERBOARD_SN = get_motherboard_serial()

if MOTHERBOARD_SN == "UNKNOWN_SERIAL":
    print("\nCould not detect motherboard serial number.")
    if sys.platform.startswith("win"):
        print("Try running 'wmic baseboard get serialnumber' or ensure the script is elevated.")
    else:
        print("Run: sudo dmidecode -s baseboard-serial-number")


# ==================== GUI APP ====================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Software Login")
        self.geometry("400x500")
        self.resizable(False, False)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(pady=20, padx=20, fill="both", expand=True)
        self.tabview.add("Login")
        self.tabview.add("Register")

        self.setup_login_tab()
        self.setup_register_tab()

    # ==================== LOGIN TAB ====================
    def setup_login_tab(self):
        frame = self.tabview.tab("Login")
        ctk.CTkLabel(frame, text="Click Login to Access Software", font=("Helvetica", 16)).pack(pady=60)
        ctk.CTkLabel(frame, text=f"Device ID: {MOTHERBOARD_SN}", font=("Courier", 10)).pack(pady=10)

        login_btn = ctk.CTkButton(
            frame, text="LOGIN", height=50, font=("Helvetica", 18, "bold"),
            command=self.check_login
        )
        login_btn.pack(pady=30, fill="x", padx=50)

    # ==================== REGISTER TAB ====================
    def setup_register_tab(self):
        frame = self.tabview.tab("Register")
        ctk.CTkLabel(frame, text="Request Access", font=("Helvetica", 18)).pack(pady=20)
        ctk.CTkLabel(frame, text="Enter your email to request access:").pack(pady=10)

        self.email_entry = ctk.CTkEntry(frame, placeholder_text="your@email.com", width=300)
        self.email_entry.pack(pady=20)

        ctk.CTkLabel(
            frame, text=f"Your Device ID:\n{MOTHERBOARD_SN}",
            font=("Courier", 12), justify="center"
        ).pack(pady=30)

        ctk.CTkButton(frame, text="Send Request", command=self.send_request).pack(pady=10)

    # ==================== SEND REGISTRATION REQUEST (REST API) ====================
    def send_request(self):
        email = self.email_entry.get().strip()
        if not email or "@" not in email or "." not in email:
            messagebox.showerror("Error", "Please enter a valid email!")
            return

        url = firestore_set_url(collection0, MOTHERBOARD_SN)

        data = {
            "fields": {
                "email": {"stringValue": email},
                "motherboard_sn": {"stringValue": MOTHERBOARD_SN},
                "project": {"stringValue": collection1},
                "requested_at": {"timestampValue": datetime.now(timezone.utc).isoformat()}            }
        }

        try:
            resp = requests.patch(url, json=data)
            if resp.status_code in (200, 201):
                messagebox.showinfo("Success",
                    f"Request sent successfully!\n\n"
                    f"Device ID: {MOTHERBOARD_SN}\n\n"
                    "You will be activated soon.")
                self.email_entry.delete(0, "end")
            elif resp.status_code == 403:
                messagebox.showerror(
                    "Firestore Permission Denied",
                    "Registration write was blocked by Firestore rules for 'user_requests'.\n"
                    "Update rules to allow this create operation."
                )
            else:
                messagebox.showerror("Error", f"Failed to send request:\n{resp.text}")
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed:\n{str(e)}")

    # ==================== CHECK LOGIN (REST API) ====================
    def check_login(self):
        url = firestore_get_url(collection1, MOTHERBOARD_SN)

        try:
            resp = requests.get(url)

            if resp.status_code == 200:
                self.destroy()
                self.run_main_app()

            elif resp.status_code == 404:
                messagebox.showerror(
                    "Access Denied",
                    f"This device is not activated yet.\n\n"
                    f"Device ID: {MOTHERBOARD_SN}\n\n"
                    "Please use 'Register' tab and wait for approval."
                )
            elif resp.status_code == 403:
                messagebox.showerror(
                    "Firestore Permission Denied",
                    f"Login check is blocked by Firestore rules.\n\n"
                    f"Path: /{collection1}/{MOTHERBOARD_SN}\n"
                    "Rules must allow read access for this check."
                )

            else:
                messagebox.showerror("Error", f"Failed to check login.\n{resp.text}")

        except Exception as e:
            messagebox.showerror("Error", f"Connection failed:\n{str(e)}")

    # ==================== RUN MAIN APP ====================
    def run_main_app(self):
        main_app_path = os.path.join(os.path.dirname(__file__), initialize_file)
        if os.path.exists(main_app_path):
            subprocess.Popen([sys.executable, main_app_path])
        else:
            messagebox.showerror("Error", "Source not found!")


if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()
