import tkinter as tk
from tkinter import ttk, messagebox
import os
from dotenv import load_dotenv
from service.crypto import TripleDES
from service.telegram_service import send_to_telegram
from Crypto.Random import get_random_bytes


class TripleDESPage(tk.Frame):
    def __init__(self, parent, controller, crypto: TripleDES, bot_token: str):
        super().__init__(parent, bg="#f0f2f5")
        self.controller = controller
        self.crypto = crypto
        self.bot_token = bot_token
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

        ttk.Label(frame, text="Telegram Chat ID:").pack(anchor="w", pady=(5, 5))
        self.chat_id_entry = ttk.Entry(frame, font=("Segoe UI", 10))
        self.chat_id_entry.pack(fill="x", pady=(0, 10))

        info_label = ttk.Label(frame, text="📌 Untuk mendapatkan Chat ID, kirim pesan ke @userinfobot di Telegram.", font=("Segoe UI", 9), foreground="gray")
        info_label.pack(anchor="w", pady=(0, 10))

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="🔒 Enkripsi", command=self.encrypt_text).grid(row=0, column=0, padx=10)
        ttk.Button(button_frame, text="🔓 Dekripsi", command=self.decrypt_text).grid(row=0, column=1, padx=10)
        ttk.Button(button_frame, text="📩 Kirim ke Telegram", command=self.send_encrypted_to_telegram).grid(row=0, column=2, padx=10)

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
            self.output_text.insert(tk.END, f"\n\n[INFO] Waktu enkripsi: {self.crypto.last_encrypt_time:.6f} detik")
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
            self.output_text.insert(tk.END, f"\n\n[INFO] Waktu dekripsi: {self.crypto.last_decrypt_time:.6f} detik")
        except Exception as e:
            messagebox.showerror("Kesalahan Dekripsi", str(e))

    def send_encrypted_to_telegram(self):
        try:
            mode = self.mode_var.get()
            text = self.input_text.get("1.0", tk.END).strip()
            chat_id = self.chat_id_entry.get().strip()

            if not text or not chat_id:
                raise ValueError("Pesan dan Chat ID harus diisi.")

            result = self.crypto.encrypt(text, mode)
            full_message = f"🔐 Enkripsi ({mode}):\n{result}"
            send_to_telegram(self.bot_token, chat_id, full_message)
            messagebox.showinfo("Sukses", "Pesan terenkripsi berhasil dikirim ke Telegram!")
        except Exception as e:
            messagebox.showerror("Gagal Kirim Telegram", str(e))


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

        load_dotenv()
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

        key1, key2, key3 = get_random_bytes(8), get_random_bytes(8), get_random_bytes(8)
        crypto = TripleDES(key1, key2, key3)

        for F in (HomePage,):
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.place(relwidth=1, relheight=1)

        triple_des_page = TripleDESPage(self.container, self, crypto, bot_token)
        self.frames[TripleDESPage] = triple_des_page
        triple_des_page.place(relwidth=1, relheight=1)

        self.show_frame(HomePage)

    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        frame.tkraise()


if __name__ == "__main__":
    app = App()
    app.mainloop()
