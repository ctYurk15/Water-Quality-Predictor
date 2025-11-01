from tkinter import ttk

# Кольори (спільні)
BG_MAIN  = "#D5E8D4"   # загальний фон
BG_PANEL = "#CFE3C9"   # права панель
BLUE_BG  = "#DAE8FC"   # сині кнопки/модалки
RED_BG   = "#F8CECC"
PURPLE_BG= "#E1D5E7"

def init_styles():
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("BaseView.TFrame", background=BG_PANEL)
    style.configure("Head.TLabel", font=("", 16, "bold"), background=BG_PANEL, foreground="#333")
    style.configure("List.TFrame", background=BG_PANEL)
    style.configure("Item.TLabel", background=BG_PANEL, foreground="#333")
    style.configure("TButton", padding=6)
