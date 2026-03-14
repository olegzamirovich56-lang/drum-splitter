import os
os.environ["TK_SILENCE_DEPRECATION"] = "1"

import requests  # Нужно установить: pip install requests
import webbrowser
import json
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD

# Импортируем обновленные функции
from run_drumsep import separate, load_drum_model

class DrumSplitterApp:
    def __init__(self, root):
        self.root = root
        self.current_version = "1.1.0" 
        self.root.title("Drum Splitter Pro")
        self.root.geometry("580x550")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f7")

        # Конфигурация
        self.config_file = Path.home() / ".drumsplitter_config.json"
        self.config = self.load_config()
        
        self.processed_count = 0
        self.failed_count = 0
        self.is_model_ready = False

        self.setup_styles()
        self.build_ui()

        # Установка иконки
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            img = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(False, img)
        
        # Запуск фоновых задач
        threading.Thread(target=self.init_model, daemon=True).start()
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    # ВАЖНО: Этот метод должен быть ОТДЕЛЬНО, а не внутри __init__
    def check_for_updates(self):
        # Замените 'твой-логин' на ваш реальный ник на GitHub после создания репозитория
        url = "https://raw.githubusercontent.com/molzbeat/drum-splitter/main/version.json"
        
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            latest_version = data.get("version")
            download_url = data.get("url")

            # Сравнение версий
            if latest_version > self.current_version:
                if messagebox.askyesno("Update Available", 
                    f"New version {latest_version} is available! Download now?"):
                    webbrowser.open(download_url)
        except Exception as e:
            print(f"Update check failed: {e}")

    def load_config(self):
        # ... далее ваш код без изменений ...
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {"output": str(Path.home() / "Desktop")}

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam') # Используем более современную тему 'clam'
        self.style.configure("TProgressbar", thickness=4, foreground='#4A90E2', background='#4A90E2')
        self.style.configure("Action.TButton", font=("Arial", 11))

    def build_ui(self):
        # Заголовок
        tk.Label(self.root, text="Drum Splitter", font=("Arial", 22, "bold"), 
                 bg="#f5f5f7", fg="#1d1d1f").pack(pady=(20, 5))
        
        self.model_status_label = tk.Label(self.root, text="Initializing AI engine...", 
                                          font=("Arial", 9), bg="#f5f5f7", fg="#f39c12")
        self.model_status_label.pack()

        # Зона Drop
        self.drop_area = tk.Frame(self.root, bg="#ffffff", highlightbackground="#d9d9d9", 
                                 highlightthickness=2, width=400, height=160)
        self.drop_area.pack(pady=20)
        self.drop_area.pack_propagate(False)

        # Регистрация Drag-and-Drop
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind("<<Drop>>", self.handle_drop)
        self.drop_area.dnd_bind("<<DragEnter>>", self.on_drag_enter)
        self.drop_area.dnd_bind("<<DragLeave>>", self.on_drag_leave)

        tk.Label(self.drop_area, text="🥁", font=("Arial", 32), bg="#ffffff").pack(pady=(15, 5))
        tk.Label(self.drop_area, text="DROP DRUM LOOP HERE", font=("Arial", 12, "bold"), 
                 fg="#333", bg="#ffffff").pack()
        tk.Label(self.drop_area, text=".wav  •  .mp3  •  .flac", font=("Arial", 10), 
                 fg="#888", bg="#ffffff").pack(pady=5)

        # Кнопки управления
        btn_frame = tk.Frame(self.root, bg="#f5f5f7")
        btn_frame.pack(pady=10)

        self.select_btn = ttk.Button(btn_frame, text="Select File", command=self.choose_file, width=15)
        self.select_btn.grid(row=0, column=0, padx=5)

        self.output_btn = ttk.Button(btn_frame, text="Change Output", command=self.choose_output, width=15)
        self.output_btn.grid(row=0, column=1, padx=5)

        # Инфо об экспорте
        tk.Label(self.root, text="Exporting to:", font=("Arial", 9, "bold"), bg="#f5f5f7", fg="#555").pack(pady=(10, 0))
        self.output_path_label = tk.Label(self.root, text=self.config["output"], font=("Arial", 9), 
                                         fg="#777", bg="#f5f5f7", wraplength=400)
        self.output_path_label.pack()

        # Прогресс
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=(20, 5))

        self.status_label = tk.Label(self.root, text="Ready", font=("Arial", 10), bg="#f5f5f7", fg="#333")
        self.status_label.pack()

        self.log_label = tk.Label(self.root, text="Processed: 0  |  Failed: 0", font=("Arial", 10, "bold"), 
                                 bg="#f5f5f7", fg="#111")
        self.log_label.pack(pady=15)

    # --- ЛОГИКА ---

    def init_model(self):
        try:
            load_drum_model()
            self.is_model_ready = True
            self.root.after(0, lambda: self.model_status_label.config(text="AI Engine Ready", fg="#27ae60"))
        except Exception as e:
            self.root.after(0, lambda: self.model_status_label.config(text="Engine Error", fg="#c0392b"))

    def handle_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        self.on_drag_leave(None)
        for f in files:
            self.start_processing(f)

    def choose_file(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.flac")])
        if path: self.start_processing(path)

    def choose_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.config["output"] = folder
            self.save_config()
            self.output_path_label.config(text=folder)

    def start_processing(self, filepath):
        if not self.is_model_ready:
            messagebox.showwarning("Wait", "AI model is still loading. Please wait a few seconds.")
            return
        
        filepath = filepath.strip("{}")
        threading.Thread(target=self.process_task, args=(filepath,), daemon=True).start()

    def process_task(self, filepath):
        self.root.after(0, lambda: self.status_label.config(text=f"Processing: {Path(filepath).name}..."))
        self.root.after(0, lambda: self.progress.config(value=10))
        
        try:
            separate(filepath, self.config["output"])
            self.processed_count += 1
            status = "Finished"
            val = 100
        except Exception as e:
            print(f"Error: {e}")
            self.failed_count += 1
            status = "Error during processing"
            val = 0

        self.root.after(0, lambda: self.update_ui_after_task(status, val))

    def update_ui_after_task(self, status, val):
        self.progress.config(value=val)
        self.status_label.config(text=status)
        self.log_label.config(text=f"Processed: {self.processed_count}  |  Failed: {self.failed_count}")
        self.root.after(2000, lambda: self.progress.config(value=0))

    # Эффекты
    def on_drag_enter(self, event):
        self.drop_area.config(highlightbackground="#4A90E2", bg="#eef5ff")

    def on_drag_leave(self, event):
        self.drop_area.config(highlightbackground="#d9d9d9", bg="#ffffff")

if __name__ == "__main__":
    
    # Правильный порядок инициализации для предотвращения лишних окон
    # Исправляем имя приложения в системном меню macOS
    if os.uname().sysname == 'Darwin':
        try:
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle()
            if bundle:
                info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if info:
                    info['CFBundleName'] = "Drum Splitter"
        except ImportError:
            pass # Если библиотека pyobjc не установлена, просто пропускаем

    # ... далее ваш код
    root = TkinterDnD.Tk()
    app = DrumSplitterApp(root)
    root.mainloop()