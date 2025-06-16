import tkinter as tk
from tkinter import ttk, messagebox
from Crypto.Cipher import DES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64


# ================= 3DES Core =================
class TripleDES:
    def __init__(self, key1: bytes, key2: bytes, key3: bytes):
        self.key1 = key1
        self.key2 = key2
        self.key3 = key3
        self.block_size = DES.block_size

    def encrypt(self, plaintext: str, mode: str) -> str:
        data = pad(plaintext.encode(), self.block_size)
        iv = get_random_bytes(self.block_size)

        if mode == 'EDE':
            data = self._encrypt(data, self.key1, iv)
            data = self._decrypt(data, self.key2, iv)
            data = self._encrypt(data, self.key3, iv)
        elif mode == 'EED':
            data = self._encrypt(data, self.key1, iv)
            data = self._encrypt(data, self.key2, iv)
            data = self._decrypt(data, self.key3, iv)
        elif mode == 'DEE':
            data = self._decrypt(data, self.key1, iv)
            data = self._encrypt(data, self.key2, iv)
            data = self._encrypt(data, self.key3, iv)
        elif mode == 'DED':
            data = self._decrypt(data, self.key1, iv)
            data = self._encrypt(data, self.key2, iv)
            data = self._decrypt(data, self.key3, iv)
        else:
            raise ValueError("Invalid mode")

        return base64.b64encode(iv + data).decode()

    def decrypt(self, ciphertext: str, mode: str) -> str:
        raw = base64.b64decode(ciphertext)
        iv, data = raw[:self.block_size], raw[self.block_size:]

        if mode == 'EDE':
            data = self._decrypt(data, self.key3, iv)
            data = self._encrypt(data, self.key2, iv)
            data = self._decrypt(data, self.key1, iv)
        elif mode == 'EED':
            data = self._encrypt(data, self.key3, iv)
            data = self._decrypt(data, self.key2, iv)
            data = self._decrypt(data, self.key1, iv)
        elif mode == 'DEE':
            data = self._decrypt(data, self.key3, iv)
            data = self._decrypt(data, self.key2, iv)
            data = self._encrypt(data, self.key1, iv)
        elif mode == 'DED':
            data = self._encrypt(data, self.key3, iv)
            data = self._decrypt(data, self.key2, iv)
            data = self._encrypt(data, self.key1, iv)
        else:
            raise ValueError("Invalid mode")

        return unpad(data, self.block_size).decode()

    def _encrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        return DES.new(key, DES.MODE_CBC, iv).encrypt(data)

    def _decrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        return DES.new(key, DES.MODE_CBC, iv).decrypt(data)


# ================= GUI App with Navigation =================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("3DES Encryption App")
        self.geometry("750x600")
        self.configure(bg="#f0f2f5")

        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TCombobox", padding=4)
        style.theme_use("clam")

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}

        for F in (HomePage, TripleDESPage):
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.place(relwidth=1, relheight=1)

        self.show_frame(HomePage)

    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        frame.tkraise()


# ================= Home Page =================
class HomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f0f2f5")
        self.controller = controller

        title = ttk.Label(self, text="🔐 3DES Encryption App", font=("Segoe UI", 18, "bold"))
        title.pack(pady=40)

        subtitle = ttk.Label(self, text="Silakan pilih menu", font=("Segoe UI", 12))
        subtitle.pack(pady=10)

        ttk.Button(self, text="📝 Mulai Enkripsi / Dekripsi", width=30,
                   command=lambda: controller.show_frame(TripleDESPage)).pack(pady=20)


# ================= Triple DES Page =================
class TripleDESPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f0f2f5")
        self.controller = controller

        self.key1 = get_random_bytes(8)  # static bytes
        self.key2 = get_random_bytes(8)
        self.key3 = get_random_bytes(8)
        self.crypto = TripleDES(self.key1, self.key2, self.key3)

        self._create_widgets()

    def _create_widgets(self):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Input Text:").pack(anchor="w", pady=(5, 5))
        self.input_text = tk.Text(frame, height=5, font=("Segoe UI", 10))
        self.input_text.pack(fill="x", pady=(0, 10))

        ttk.Label(frame, text="Pilih Mode 3DES:").pack(anchor="w", pady=(5, 5))
        self.mode_var = tk.StringVar(value="EDE")
        mode_combo = ttk.Combobox(frame, textvariable=self.mode_var,
                                  values=["EDE", "EED", "DEE", "DED"], state="readonly")
        mode_combo.pack(pady=(0, 10))

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="🔒 Enkripsi", command=self.encrypt_text).grid(row=0, column=0, padx=10)
        ttk.Button(button_frame, text="🔓 Dekripsi", command=self.decrypt_text).grid(row=0, column=1, padx=10)

        ttk.Label(frame, text="Hasil Output:").pack(anchor="w", pady=(15, 5))
        self.output_text = tk.Text(frame, height=10, font=("Segoe UI", 10), bg="#f9f9f9")
        self.output_text.pack(fill="both", expand=True)

        ttk.Button(self, text="← Kembali ke Menu", command=lambda: self.controller.show_frame(HomePage)).pack(pady=10)

    def encrypt_text(self):
        try:
            mode = self.mode_var.get()
            text = self.input_text.get("1.0", tk.END).strip()
            if not text:
                raise ValueError("Input kosong.")
            result = self.crypto.encrypt(text, mode)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, result)
        except Exception as e:
            messagebox.showerror("Kesalahan Enkripsi", str(e))

    def decrypt_text(self):
        try:
            mode = self.mode_var.get()
            text = self.input_text.get("1.0", tk.END).strip()
            if not text:
                raise ValueError("Input kosong.")
            result = self.crypto.decrypt(text, mode)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, result)
        except Exception as e:
            messagebox.showerror("Kesalahan Dekripsi", str(e))


# ================= Run Application =================
if __name__ == "__main__":
    app = App()
    app.mainloop()
