import tkinter as tk
from datetime import datetime
from theme import BLUE_BG, BG_MAIN, RED_BG

class LoadingWindow:
    """
    Модалка завантаження:
        loading_text - текст, що показувати під час завантаження
    """
    def __init__(self, master, loading_text):
        self.master = master

        self.top = tk.Toplevel(master)
        self.top.title("Загрузка...")
        self.top.transient(master); self.top.grab_set()
        self.top.configure(bg=BLUE_BG); self.top.resizable(False, False)

        w, h = 300, 70
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        self.text_container = tk.Label(self.top, text=loading_text, bg=BLUE_BG)
        self.text_container.grid(row=0, column=0, sticky="w", padx=8, pady=8)

    def change_text(self, text):
        self.text_container.config(text=text)