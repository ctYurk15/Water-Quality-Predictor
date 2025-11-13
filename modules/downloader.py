from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import shutil, threading, os

def trigger_file_download(file_path, container):
    SRC_REL = Path(file_path)

    src = Path(__file__).resolve().parent.parent / SRC_REL
    if not src.exists():
        messagebox.showerror("Помилка", f"Файл не знайдено:\n{src}", parent=self)
        return

    # діалог "Зберегти як…"
    dst_path = filedialog.asksaveasfilename(
        parent=container,
        title="Зберегти файл як…",
        initialdir=os.path.expanduser("~"),
        initialfile=src.name,
        defaultextension=src.suffix,
        filetypes=[("Усі файли", "*.*")],
        confirmoverwrite=False,
    )
    if not dst_path:
        return  # користувач скасував

    dst = Path(dst_path)
    if dst.exists():
        if not messagebox.askyesno("Підтвердіть перезапис", f"Файл уже існує:\n{dst}\nПерезаписати?", parent=container):
            return

    # копіюємо у фоні, щоб не блокувати GUI

    def worker():
        err = None
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)  # копіює з метаданими
        except Exception as e:
            err = e
        finally:
            def finish():
                if err:
                    messagebox.showerror("Помилка", str(err), parent=container)
                else:
                    messagebox.showinfo("Готово", f"Збережено:\n{dst}", parent=container)
            container.after(0, finish)

    threading.Thread(target=worker, daemon=True).start()