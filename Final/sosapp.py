#!/usr/bin/env python3
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

DB_NAME = "sos_department.db"

# ---------------------------- DATABASE SETUP ----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        father_name TEXT,
        mother_name TEXT,
        place TEXT,
        age INTEGER,
        medical_conditions TEXT,
        contact1 TEXT NOT NULL,
        contact2 TEXT,
        contact3 TEXT,
        other_info TEXT
    )''')
    
    # Devices table
    c.execute('''CREATE TABLE IF NOT EXISTS devices (
        device_id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_name TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )''')
    
    # Alerts table (optional, for future use)
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
        alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NOT NULL,
        alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
    )''')
    
    conn.commit()
    conn.close()

def add_sample_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        # User 1
        c.execute('''INSERT INTO users 
            (full_name, father_name, mother_name, place, age, medical_conditions,
             contact1, contact2, contact3, other_info)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            ("Amit Sharma", "Rajesh Sharma", "Sunita Sharma", "Mumbai", 28,
             "No known allergies", "+91 98765 43210", "+91 98765 43211",
             "+91 98765 43212", "Works night shift - call carefully"))
        uid1 = c.lastrowid
        c.execute("INSERT INTO devices (device_name, user_id) VALUES (?,?)", ("SOS-1001", uid1))
        
        # User 2
        c.execute('''INSERT INTO users 
            (full_name, father_name, mother_name, place, age, medical_conditions,
             contact1, contact2, contact3, other_info)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            ("Priya Verma", "Anil Verma", "Geeta Verma", "Delhi", 45,
             "Diabetic, BP medication", "+91 99999 88888", "+91 99999 88889",
             "+91 99999 88880", "Emergency contact: brother +91 9988776655"))
        uid2 = c.lastrowid
        c.execute("INSERT INTO devices (device_name, user_id) VALUES (?,?)", ("SOS-1002", uid2))
        
        # Extra device without user? No – device must have user. So done.
    conn.commit()
    conn.close()

# ---------------------------- DATABASE OPERATIONS ----------------------------
def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, full_name, place, age, contact1 FROM users ORDER BY user_id")
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''SELECT full_name, father_name, mother_name, place, age, medical_conditions,
                        contact1, contact2, contact3, other_info
                 FROM users WHERE user_id = ?''', (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_user_and_device(data, device_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO users 
            (full_name, father_name, mother_name, place, age, medical_conditions,
             contact1, contact2, contact3, other_info)
            VALUES (?,?,?,?,?,?,?,?,?,?)''', data)
        user_id = c.lastrowid
        c.execute("INSERT INTO devices (device_name, user_id) VALUES (?,?)", (device_name, user_id))
        conn.commit()
        return True, user_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def update_user(user_id, data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''UPDATE users SET
        full_name=?, father_name=?, mother_name=?, place=?, age=?, medical_conditions=?,
        contact1=?, contact2=?, contact3=?, other_info=?
        WHERE user_id=?''', (*data, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_devices_by_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT device_id, device_name, registered_at FROM devices WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_device_to_user(user_id, device_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO devices (device_name, user_id) VALUES (?,?)", (device_name, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_device(device_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM devices WHERE device_id=?", (device_id,))
    conn.commit()
    conn.close()

# ---------------------------- MAIN SEARCH APP ----------------------------
class SOSLookupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Emergency SOS - Device Lookup")
        self.root.geometry("700x550")
        
        # Top frame with search and admin button
        top_frame = ttk.Frame(root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="Device Name:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        self.device_name_var = tk.StringVar()
        self.entry = ttk.Entry(top_frame, textvariable=self.device_name_var, width=25, font=("Arial", 12))
        self.entry.pack(side=tk.LEFT, padx=5)
        self.entry.bind("<Return>", lambda e: self.search())
        
        self.search_btn = ttk.Button(top_frame, text="Search", command=self.search)
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        self.admin_btn = ttk.Button(top_frame, text="Admin Panel", command=self.open_admin)
        self.admin_btn.pack(side=tk.RIGHT, padx=10)
        
        # Result display
        result_frame = ttk.Frame(root, padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_widget = tk.Text(result_frame, wrap=tk.WORD, font=("Courier", 11), relief=tk.SUNKEN)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready. Enter device name (e.g., SOS-1001) and press Enter.")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(5,2))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def search(self):
        device_name = self.device_name_var.get().strip()
        if not device_name:
            messagebox.showwarning("Input Error", "Please enter a device name.")
            return
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''SELECT u.full_name, u.father_name, u.mother_name, u.place, u.age,
                            u.medical_conditions, u.contact1, u.contact2, u.contact3, u.other_info
                     FROM devices d JOIN users u ON d.user_id = u.user_id
                     WHERE d.device_name = ?''', (device_name,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(tk.END, f"❌ Device '{device_name}' not found.\n")
            self.status_var.set(f"Device '{device_name}' not found.")
            return
        
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(tk.END, f"📟 DEVICE: {device_name}\n" + "="*60 + "\n\n")
        fields = ["Full Name", "Father's Name", "Mother's Name", "Place", "Age",
                  "Medical Conditions", "Contact 1", "Contact 2", "Contact 3", "Other Information"]
        for label, val in zip(fields, row):
            if val:
                self.text_widget.insert(tk.END, f"{label:18}: {val}\n")
            else:
                self.text_widget.insert(tk.END, f"{label:18}: —\n")
        self.status_var.set(f"Displaying data for device {device_name}")
    
    def open_admin(self):
        AdminWindow(self.root)

# ---------------------------- ADMIN WINDOW ----------------------------
class AdminWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Admin Panel - User & Device Management")
        self.win.geometry("900x600")
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.win)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Manage Users
        self.users_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.users_frame, text="Manage Users")
        self.setup_users_tab()
        
        # Tab 2: Manage Devices
        self.devices_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.devices_frame, text="Manage Devices")
        self.setup_devices_tab()
        
        # Refresh data
        self.refresh_user_list()
        self.refresh_device_list()
    
    def setup_users_tab(self):
        # Treeview for users
        columns = ("ID", "Full Name", "Place", "Age", "Contact1")
        self.user_tree = ttk.Treeview(self.users_frame, columns=columns, show="headings")
        for col in columns:
            self.user_tree.heading(col, text=col)
            self.user_tree.column(col, width=100)
        self.user_tree.column("ID", width=50)
        self.user_tree.column("Full Name", width=150)
        self.user_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Buttons frame
        btn_frame = ttk.Frame(self.users_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Add User + Device", command=self.add_user_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Edit Selected", command=self.edit_user_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_user_list).pack(side=tk.LEFT, padx=5)
        
        # Bind selection to show devices
        self.user_tree.bind("<<TreeviewSelect>>", self.on_user_select)
        
        # Label for showing devices of selected user
        self.device_label = ttk.Label(self.users_frame, text="Devices for selected user:")
        self.device_label.pack(anchor=tk.W, pady=(10,0))
        self.device_listbox = tk.Listbox(self.users_frame, height=4)
        self.device_listbox.pack(fill=tk.X, pady=5)
    
    def refresh_user_list(self):
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        users = get_all_users()
        for u in users:
            self.user_tree.insert("", tk.END, values=u)
    
    def on_user_select(self, event):
        selection = self.user_tree.selection()
        if not selection:
            return
        user_id = self.user_tree.item(selection[0])['values'][0]
        devices = get_devices_by_user(user_id)
        self.device_listbox.delete(0, tk.END)
        for d in devices:
            self.device_listbox.insert(tk.END, f"{d[1]} (ID:{d[0]}) registered: {d[2]}")
    
    def add_user_dialog(self):
        dialog = tk.Toplevel(self.win)
        dialog.title("Add New User + Device")
        dialog.geometry("500x550")
        dialog.grab_set()
        
        fields = [
            ("Full Name*", "full_name"), ("Father's Name", "father_name"),
            ("Mother's Name", "mother_name"), ("Place", "place"), ("Age", "age"),
            ("Medical Conditions", "medical_conditions"), ("Contact 1*", "contact1"),
            ("Contact 2", "contact2"), ("Contact 3", "contact3"), ("Other Info", "other_info")
        ]
        entries = {}
        row = 0
        for label, key in fields:
            ttk.Label(dialog, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(dialog, width=40)
            entry.grid(row=row, column=1, padx=5, pady=2)
            entries[key] = entry
            row += 1
        
        ttk.Label(dialog, text="Device Name*:", font=("", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        device_entry = ttk.Entry(dialog, width=40)
        device_entry.grid(row=row, column=1, padx=5, pady=5)
        
        def save():
            data = []
            for _, key in fields:
                val = entries[key].get().strip()
                if key in ["full_name", "contact1"] and not val:
                    messagebox.showerror("Error", f"{key.replace('_',' ').title()} is required.")
                    return
                if key == "age":
                    try:
                        val = int(val) if val else None
                    except:
                        messagebox.showerror("Error", "Age must be a number.")
                        return
                data.append(val)
            device_name = device_entry.get().strip()
            if not device_name:
                messagebox.showerror("Error", "Device Name is required.")
                return
            success, result = add_user_and_device(tuple(data), device_name)
            if success:
                messagebox.showinfo("Success", f"User added with ID {result}\nDevice '{device_name}' linked.")
                dialog.destroy()
                self.refresh_user_list()
            else:
                messagebox.showerror("Error", f"Failed: {result}")
        
        ttk.Button(dialog, text="Save", command=save).grid(row=row+1, column=0, columnspan=2, pady=10)
    
    def edit_user_dialog(self):
        selection = self.user_tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a user to edit.")
            return
        user_id = self.user_tree.item(selection[0])['values'][0]
        user_data = get_user_by_id(user_id)
        if not user_data:
            return
        
        dialog = tk.Toplevel(self.win)
        dialog.title(f"Edit User ID {user_id}")
        dialog.geometry("500x550")
        dialog.grab_set()
        
        fields = [
            ("Full Name", "full_name"), ("Father's Name", "father_name"),
            ("Mother's Name", "mother_name"), ("Place", "place"), ("Age", "age"),
            ("Medical Conditions", "medical_conditions"), ("Contact 1", "contact1"),
            ("Contact 2", "contact2"), ("Contact 3", "contact3"), ("Other Info", "other_info")
        ]
        entries = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(dialog, width=40)
            entry.grid(row=i, column=1, padx=5, pady=2)
            entry.insert(0, user_data[i] if user_data[i] is not None else "")
            entries[key] = entry
        
        def save():
            new_data = []
            for _, key in fields:
                val = entries[key].get().strip()
                if key == "full_name" and not val:
                    messagebox.showerror("Error", "Full Name is required.")
                    return
                if key == "age":
                    try:
                        val = int(val) if val else None
                    except:
                        messagebox.showerror("Error", "Age must be a number.")
                        return
                new_data.append(val)
            update_user(user_id, tuple(new_data))
            messagebox.showinfo("Success", "User updated.")
            dialog.destroy()
            self.refresh_user_list()
        
        ttk.Button(dialog, text="Update", command=save).grid(row=len(fields), column=0, columnspan=2, pady=10)
    
    def delete_user(self):
        selection = self.user_tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Select a user to delete.")
            return
        user_id = self.user_tree.item(selection[0])['values'][0]
        if messagebox.askyesno("Confirm", f"Delete user ID {user_id} and ALL linked devices & alerts?\nThis cannot be undone."):
            delete_user(user_id)
            self.refresh_user_list()
            self.device_listbox.delete(0, tk.END)
            messagebox.showinfo("Deleted", "User and associated devices deleted.")
    
    # ---------------------- DEVICES TAB ----------------------
    def setup_devices_tab(self):
        columns = ("Device ID", "Device Name", "User ID", "Full Name", "Registered")
        self.device_tree = ttk.Treeview(self.devices_frame, columns=columns, show="headings")
        for col in columns:
            self.device_tree.heading(col, text=col)
            self.device_tree.column(col, width=120)
        self.device_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        btn_frame = ttk.Frame(self.devices_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_device_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Add Device to User", command=self.add_device_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Device", command=self.delete_device).pack(side=tk.LEFT, padx=5)
    
    def refresh_device_list(self):
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''SELECT d.device_id, d.device_name, u.user_id, u.full_name, d.registered_at
                     FROM devices d JOIN users u ON d.user_id = u.user_id
                     ORDER BY d.device_id''')
        rows = c.fetchall()
        conn.close()
        for r in rows:
            self.device_tree.insert("", tk.END, values=r)
    
    def add_device_dialog(self):
        dialog = tk.Toplevel(self.win)
        dialog.title("Add Device to Existing User")
        dialog.geometry("400x150")
        dialog.grab_set()
        
        ttk.Label(dialog, text="User ID:").grid(row=0, column=0, padx=5, pady=5)
        user_id_entry = ttk.Entry(dialog)
        user_id_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(dialog, text="Device Name:").grid(row=1, column=0, padx=5, pady=5)
        device_entry = ttk.Entry(dialog)
        device_entry.grid(row=1, column=1, padx=5, pady=5)
        
        def save():
            try:
                uid = int(user_id_entry.get())
            except:
                messagebox.showerror("Error", "User ID must be a number.")
                return
            dev_name = device_entry.get().strip()
            if not dev_name:
                messagebox.showerror("Error", "Device name required.")
                return
            if add_device_to_user(uid, dev_name):
                messagebox.showinfo("Success", f"Device {dev_name} added to user {uid}")
                dialog.destroy()
                self.refresh_device_list()
                self.refresh_user_list()
            else:
                messagebox.showerror("Error", "Device name already exists or user not found.")
        
        ttk.Button(dialog, text="Add", command=save).grid(row=2, column=0, columnspan=2, pady=10)
    
    def delete_device(self):
        selection = self.device_tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Select a device to delete.")
            return
        dev_id = self.device_tree.item(selection[0])['values'][0]
        if messagebox.askyesno("Confirm", f"Delete device ID {dev_id}?\nAlerts linked to this device will also be deleted."):
            delete_device(dev_id)
            self.refresh_device_list()
            self.refresh_user_list()

# ---------------------------- MAIN ----------------------------
if __name__ == "__main__":
    init_db()
    add_sample_data()
    root = tk.Tk()
    app = SOSLookupApp(root)
    root.mainloop()
