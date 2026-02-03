# -*- coding: utf-8 -*-
import os
import threading
import time
import re
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import pygame
from gtts import gTTS
import google.generativeai as genai
import pyperclip
from PIL import Image
import speech_recognition as sr
import matplotlib
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
import numpy as np




# Бібліотеки для PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

os.environ["PYTHONIOENCODING"] = "utf-8"

# --- НАЛАШТУВАННЯ ---
API_KEY = "AIzaSyAOs87Jeqx_KSp4Xhzf35-eo2OgPqKEWMg"
MODEL_NAME = 'gemini-2.5-flash'

genai.configure(api_key=API_KEY.strip())

# --- БАЗА ПРОМПТІВ (ЖОРСТКИЙ ФІЛЬТР: ТІЛЬКИ JAVA+PYTHON) ---
SUBJECT_PROMPTS = {
    "Фізика": (
        "⚠️ НІКОЛИ НЕ ПИШИ LaTeX! ТІЛЬКИ Unicode символи: μ π λ ² ½ ∞ → × ÷ √ ∫ ∑ ∂"
        "НЕ ПИШИ: \\mu, $...$, \\frac{}, \\to, \\sqrt{}, \\int. Пиши: μ, π, ½, →, √, ∫"
        "ПРИКЛАДИ: E=½mv², F=ma, Gμν+Λgμν=8πTμν, v=√(2gh)"
        "Для графіків пиши рівняння типу: y=x**2, sin(x), x**2+2*x+1"

        "Ти — суворий ШІ-репетитор з ФІЗИКИ. "
        "Твоє завдання: відповідати ТІЛЬКИ на питання про механіку, електрику, оптику, термодинаміку, "
        "квантову фізику, астрономію. Формули Unicode."
        "ВСЕ ІНШЕ (код, історія, література) — ВІДМОВИ: 'Я тільки Фізика. Питай про закони Ньютона!'"
    ),

    "Програмування (Java/Python)": (
        "⚠️ ТИ — Senior Developer. ТІЛЬКИ JAVA та PYTHON. НІЧОГО ІНШОГО."
        "Відповідай ТІЛЬКИ на: синтаксис Java/Python, алгоритми, ООП, паттерни, дебагінг, data structures."
        "Java: класи, спадкування, інтерфейси, Spring, collections."
        "Python: функції, класи, списки, словники, pandas, numpy."

        "❌ ЗАБОРОНЕНО: C++, JavaScript, HTML/CSS, SQL, історія, біологія."
        "❌ Якщо питають НЕ Java/Python — ВІДМОВИ: "
        "'❌ Я налаштований ТІЛЬКИ на Java та Python. Питай про класи Java чи функції Python.'"

        "Код ЗАВЖДИ в ```java або ```python."
    ),
    "Математика": (
        "Ти — математик. ТІЛЬКИ: рівняння, геометрія, тригонометрія, інтеграли, матриці."
        "ВСЕ ІНШЕ — ВІДМОВИ: 'Це не математика. Давай розвяжемо рівняння!'"
        "Для графіків пиши рівняння типу: y=x**2, sin(x), x**2+2*x+1"
    ),
    "Універсальний Тьютор": (
    "⚠️ ТИ — ШКІЛЬНИЙ ТЬЮТОР. ТІЛЬКИ ШКІЛЬНІ ПРЕДМЕТИ 5-11 класів."
    "✅ Дозволено: Фізика, Математика, Програмування, Хімія, Біологія, Історія, "
    "Література, Англійська, Географія, Українська мова."
    
    "❌ ЗАБОРОНЕНО (ВІДМОВЛЯЙ): "
    "• Політика, релігія, спорт, музика, кіно, кулінарія, автомобілі, "
    "• бізнес, криптовалюта, ставки, азартні ігри, "
    "• жарти, меми, нецензурна лексика, особисті проблеми."
    
    "❌ На нешкільні теми відповідай: "
    "'❌ Я відповідаю ТІЛЬКИ на шкільні предмети. Запитай про фізику, математику чи історію!'"
),
}

# Реєстрація шрифту для PDF
try:
    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    pdfmetrics.registerFont(TTFont('ArialUA', font_path))
    HAS_FONT = True
except:
    HAS_FONT = False


# --- ВІКНО ВИБОРУ ПРЕДМЕТУ ---
class SubjectSelector:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Academy - Вибір предмету")
        self.root.geometry("400x350")
        self.root.configure(bg="#0f172a")

        tk.Label(self.root, text="Оберіть предмет для навчання:",
                 font=("Segoe UI", 14, "bold"), bg="#0f172a", fg="white").pack(pady=20)

        style = ttk.Style()
        style.configure("TButton", font=("Segoe UI", 11), padding=6)

        # Кнопки для кожного предмету
        for subject in SUBJECT_PROMPTS.keys():
            btn = tk.Button(self.root, text=subject, font=("Segoe UI", 11),
                            bg="#334155", fg="white", width=30,
                            command=lambda s=subject: self.select_subject(s))
            btn.pack(pady=5)

        self.selected_subject = None
        self.root.mainloop()

    def select_subject(self, subject):
        self.selected_subject = subject
        self.root.destroy()  # Закриваємо це вікно і йдемо далі


# --- ГОЛОВНИЙ КЛАС ---
class ProfessionalTutorV45:
    def __init__(self, root, subject_name, system_instruction):
        self.root = root
        self.root.title(f"AI Academy v5.0 | Предмет: {subject_name}")  # Показуємо предмет у заголовку
        self.root.geometry("1000x950")
        self.root.configure(bg="#020617")

        self.level, self.xp = self.load_progress()
        self.is_waiting = False
        self.last_code_snippet = ""
        self.chat_history_for_pdf = []
        self.current_image = None
        self.plot_frame = None
        self.canvas = None

        self.system_instruction = system_instruction

        pygame.mixer.init()
        self.setup_ui()
        threading.Thread(target=self.connect_ai, daemon=True).start()

    def load_progress(self):
        if os.path.exists("progress.txt"):
            try:
                with open("progress.txt", "r") as f:
                    data = f.read().split(",")
                    return int(data[0]), int(data[1])
            except:
                pass
        return 1, 0

    def save_progress(self):
        with open("progress.txt", "w") as f:
            f.write(f"{self.level},{self.xp}")

    def setup_ui(self):
        # Header
        self.header = tk.Frame(self.root, bg="#1e293b", height=80)
        self.header.pack(fill=tk.X)
        self.info_label = tk.Label(self.header, text=f"РІВЕНЬ: {self.level} | XP: {self.xp}/100",
                                   fg="#38bdf8", bg="#1e293b", font=("Consolas", 14, "bold"))
        self.info_label.pack(pady=10)

        # Chat
        self.chat_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, bg="#0f172a",
                                                   fg="#f1f5f9", font=("Segoe UI", 12), borderwidth=0)
        self.chat_area.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        self.chat_area.tag_config("user", foreground="#60a5fa", font=("Segoe UI", 12, "bold"))
        self.chat_area.tag_config("tutor", foreground="#4ade80", font=("Segoe UI", 12, "bold"))
        self.chat_area.tag_config("code_block", background="#000000", foreground="#5eead4", font=("Consolas", 11))

        # Buttons Panel
        self.bottom_panel = tk.Frame(self.root, bg="#020617")
        self.bottom_panel.pack(fill=tk.X, padx=20, pady=20)

        self.entry = tk.Text(self.bottom_panel, font=("Arial", 13), bg="#1e293b", fg="white", height=3, padx=10,
                             pady=10)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.entry.bind("<Control-v>", self.handle_paste)
        self.entry.bind("<Control-V>", self.handle_paste)
        self.entry.bind("<Return>", self.handle_return)

        self.btn_frame = tk.Frame(self.bottom_panel, bg="#020617")
        self.btn_frame.pack(side=tk.RIGHT, padx=(15, 0))

        self.img_btn = tk.Button(self.btn_frame, text="📷 ФОТО", command=self.upload_image,
                                 bg="#f59e0b", fg="white", width=18)
        self.img_btn.pack(pady=2)


        self.mic_btn = tk.Button(self.btn_frame, text="🎤 ГОЛОС", command=self.start_voice_input,
                                bg="#ef4444", fg="white", width=18)
        self.mic_btn.pack(pady=2)

        self.plot_btn = tk.Button(self.btn_frame, text="📊 ГРАФІК", command=self.plot_graph, 
                                 bg="#8b5cf6", fg="white", width=18)
        self.plot_btn.pack(pady=2)



        self.copy_btn = tk.Button(self.btn_frame, text="КОПІЮВАТИ КОД", command=self.copy_last_code, bg="#10b981",
                                  fg="white", width=18, state='disabled')
        self.copy_btn.pack(pady=2)

        self.pdf_btn = tk.Button(self.btn_frame, text="ЗБЕРЕГТИ PDF", command=self.save_pdf, bg="#a855f7", fg="white",
                                 width=18)
        self.pdf_btn.pack(pady=2)

        self.send_btn = tk.Button(self.btn_frame, text="ВІДПРАВИТИ", command=self.send_message, bg="#38bdf8",
                                  fg="black", width=18, height=2, font=("Arial", 10, "bold"))
        self.send_btn.pack(pady=2)

    def clean_latex(self, text):
        # 1. Спочатку прибираємо позначки формул
        text = re.sub(r'[\$\\()\\[\\]]', '', text)  # Видаляємо $, \, (, ), [, ]

        # 2. Замінюємо найпоширеніші грецькі літери (простіший підхід)
        replacements = {
            '\\mu': 'μ', '\\nu': 'ν', '\\pi': 'π', '\\lambda': 'λ', '\\Lambda': 'Λ',
            '\\rho': 'ρ', '\\sigma': 'σ', '\\theta': 'θ', '\\alpha': 'α', '\\beta': 'β',
            '\\gamma': 'γ', '\\delta': 'δ', '\\Delta': 'Δ', '\\omega': 'ω', '\\phi': 'φ',
            '\\infty': '∞', '\\approx': '≈', '\\neq': '≠', '\\leq': '≤', '\\geq': '≥',
            '\\to': '→', '\\rightarrow': '→', '\\times': '×', '\\div': '÷', '\\cdot': '·'
        }

        # 3. Замінюємо ВСЮ підрядку
        for latex, unicode_char in replacements.items():
            text = text.replace(latex, unicode_char)

        # 4. Степені (найчастіша проблема)
        text = text.replace('^2', '²').replace('^3', '³').replace('^4', '⁴')

        # 5. Фракції (найпоширеніше у фізиці)
        text = text.replace('1/2', '½').replace('\\frac{1}{2}', '½')

        return text

    def upload_image(self):
        file_path = filedialog.askopenfilename(
            title="Оберіть фото задачі або коду",
            filetypes=[("Images", "*.jpg;*.png;*.jpeg;*.webp;*.bmp")]
        )
        if file_path:
            try:
                self.current_image = Image.open(file_path)
                self.img_btn.config(bg="#059669", text="✅ ФОТО ГОТОВО")
                messagebox.showinfo("Успіх!", "Фото додано! Тепер напишіть питання.")
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося відкрити: {e}")
                self.current_image = None

    def reset_image_btn(self):
        self.current_image = None
        self.img_btn.config(bg="#f59e0b", text="📷 ФОТО")

    def handle_paste(self, event=None):
        try:
            self.entry.insert(tk.INSERT, pyperclip.paste())
        except:
            pass
        return "break"

    def handle_return(self, event):
        if not (event.state & 0x0001):
            self.send_message()
            return "break"

    def display_message(self, sender, text):
        if sender == "Тьютор":
            text = self.clean_latex(text)

        self.chat_area.configure(state='normal')
        tag = "user" if sender == "Ви" else "tutor"
        self.chat_area.insert(tk.END, f"\n{sender}: ", tag)

        parts = re.split(r'```(.*?)```', text, flags=re.DOTALL)
        pdf_msg_parts = []

        for i, part in enumerate(parts):
            if i % 2 == 1:
                code = re.sub(r'^[a-zA-Z+#]+\n', '', part.strip())
                self.chat_area.insert(tk.END, f"\n{code}\n", "code_block")
                self.last_code_snippet = code
                self.copy_btn.config(state='normal')
                pdf_msg_parts.append({"type": "code", "content": code})
            else:
                clean = part.replace("*", "")
                self.chat_area.insert(tk.END, clean)
                pdf_msg_parts.append({"type": "text", "content": clean})

        self.chat_history_for_pdf.append({"sender": sender, "parts": pdf_msg_parts})
        self.chat_area.configure(state='disabled')
        self.chat_area.yview(tk.END)

    def save_pdf(self):
        doc = SimpleDocTemplate("lesson_AI.pdf", pagesize=A4)
        story = []
        f_name = 'ArialUA' if HAS_FONT else 'Helvetica'

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='UA_Normal', fontName=f_name, fontSize=11, leading=14))
        styles.add(ParagraphStyle(name='UA_Code', fontName='Courier', fontSize=10, backColor=HexColor('#e5e7eb'),
                                  leftIndent=10))

        story.append(Paragraph(f"<b>Конспект уроку - {self.root.title()}</b>", styles['UA_Normal']))
        story.append(Spacer(1, 12))

        for msg in self.chat_history_for_pdf:
            story.append(Paragraph(f"<b>{msg['sender']}:</b>", styles['UA_Normal']))
            for p in msg['parts']:
                style = styles['UA_Code'] if p['type'] == 'code' else styles['UA_Normal']
                story.append(Paragraph(p['content'].replace('\n', '<br/>'), style))
            story.append(Spacer(1, 10))

        try:
            doc.build(story)
            messagebox.showinfo("PDF", "Збережено у lesson_AI.pdf")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))


    def start_voice_input(self):
        threading.Thread(target=self.recognize_speech, daemon=True).start()

    def recognize_speech(self):
        r = sr.Recognizer()
        self.mic_btn.config(text="🔴 СЛУХАЮ...", bg="#dc2626")
        self.entry.delete("1.0", tk.END)
        self.entry.insert(tk.END, "🎤 Слухаю...")

        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=5, phrase_time_limit=10)

                self.entry.delete("1.0", tk.END)
                self.entry.insert(tk.END, "⏳ Обробка...")

                text = r.recognize_google(audio, language="uk-UA")

                self.entry.delete("1.0", tk.END)
                self.entry.insert(tk.END, text)
        except Exception as e:
            self.entry.delete("1.0", tk.END)
            self.entry.insert(tk.END, f"Помилка: {str(e)}")
            print(f"MIC ERROR: {e}")
        finally:
            self.mic_btn.config(text="🎤 ГОЛОС", bg="#ef4444")



    def send_message(self):
        content = self.entry.get("1.0", tk.END).strip()
        if not content or self.is_waiting: return
        self.display_message("Ви", content)
        self.entry.delete("1.0", tk.END)
        self.set_lock(True)
        threading.Thread(target=self.run_ai, args=(content,), daemon=True).start()

    def run_ai(self, text):
        try:
            if self.current_image:
                response = self.chat.send_message([text, self.current_image])
                self.root.after(0, self.reset_image_btn)
            else:
                response = self.chat.send_message(text)

            self.root.after(0, self.display_message, "Тьютор", response.text)
            self.add_xp(25 if self.current_image else 20)
        except Exception as e:
            self.root.after(0, self.display_message, "Система", f"Помилка: {str(e)}")
        finally:
            self.root.after(0, self.set_lock, False)

    def set_lock(self, lock):
        self.is_waiting = lock
        self.entry.config(state='disabled' if lock else 'normal')
        self.send_btn.config(text="ДУМАЮ..." if lock else "ВІДПРАВИТИ")

    def add_xp(self, amount):
        self.xp += amount
        if self.xp >= 100:
            self.xp = 0
            self.level += 1
        self.info_label.config(text=f"РІВЕНЬ: {self.level} | XP: {self.xp}/100")
        self.save_progress()

    def copy_last_code(self):
        pyperclip.copy(self.last_code_snippet)
        messagebox.showinfo("OK", "Код скопійовано!")

    def connect_ai(self):
        try:
            self.model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=self.system_instruction)
            self.chat = self.model.start_chat(history=[])
            res = self.chat.send_message("Привітайся коротко.")
            self.root.after(0, self.display_message, "Тьютор", res.text)
        except:
            pass

    def plot_graph(self):
        """Показує панель для побудови графіків"""
        if self.plot_frame:
            self.plot_frame.destroy()
        
        # Створюємо нову панель для графіків зверху чату
        self.plot_frame = tk.Frame(self.root, bg="#1e293b", height=300)
        self.plot_frame.pack(fill=tk.X, padx=20, pady=(10,5))
        
        tk.Label(self.plot_frame, text="📝 Напиши рівняння для графіка (приклад: y=x**2 або sin(x))", 
                bg="#1e293b", fg="white", font=("Arial", 11)).pack(pady=5)
        
        plot_entry = tk.Entry(self.plot_frame, font=("Consolas", 12), width=40)
        plot_entry.pack(pady=5)
        plot_entry.insert(0, "y = x**2")  # Приклад
        
        plot_btn = tk.Button(self.plot_frame, text="📈 ПУБЛИТИ", 
                           command=lambda: self.execute_plot(plot_entry.get()),
                           bg="#10b981", fg="white")
        plot_btn.pack(pady=5)
        
        close_btn = tk.Button(self.plot_frame, text="❌ ЗАКРИТИ", 
                            command=self.close_plot, bg="#ef4444", fg="white")
        close_btn.pack(pady=5)

    def execute_plot(self, equation):
        """Виконує код графіка"""
        try:
            self.plot_frame.destroy()
            
            # Створюємо нове вікно для графіка
            graph_window = tk.Toplevel(self.root)
            graph_window.title(f"Графік: {equation}")
            graph_window.geometry("800x600")

            # Створюємо графік
            fig = Figure(figsize=(10, 6), dpi=100)
            ax = fig.add_subplot(111)
            
            # Безпечне виконання рівняння
            x = np.linspace(-10, 10, 400)
            
            # Очищуємо від "y=" на початку, якщо користувач ввів повне рівняння
            clean_eq = re.sub(r'^\s*y\s*=\s*', '', equation, flags=re.IGNORECASE)

            # Замінюємо юнікод степені на Python-синтаксис
            clean_eq = clean_eq.replace('²', '**2').replace('³', '**3').replace('⁴', '**4') \
                               .replace('^', '**')

            # Додаємо множення між цифрою та змінною/дужкою (наприклад, 2x -> 2*x, 3(x+1) -> 3*(x+1))
            clean_eq = re.sub(r'(\d)([a-zA-Z(])', r'\1*\2', clean_eq)
            
            # Замінюємо поширені математичні позначення на numpy-функції
            expr = clean_eq.lower().replace('sin', 'np.sin').replace('cos', 'np.cos') \
                             .replace('tan', 'np.tan').replace('exp', 'np.exp') \
                             .replace('sqrt', 'np.sqrt') \
                             .replace('pi', 'np.pi')

            # Якщо користувач ввів ln(x), замінюємо на np.log(x)
            expr = expr.replace('ln', 'np.log')
            
            # Обчислюємо значення y
            y = eval(expr, {"np": np, "x": x})
            
            ax.plot(x, y)
            ax.grid(True, alpha=0.3)
            ax.set_title(f"y = {clean_eq}")
            
            # Вставляємо в нове вікно
            canvas = FigureCanvasTkAgg(fig, master=graph_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # Додаємо панель інструментів (Zoom, Pan, Save)
            toolbar = NavigationToolbar2Tk(canvas, graph_window)
            toolbar.update()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Додаємо повідомлення в чат
            self.display_message("Графік", f"📊 Графік {equation} відкрито в окремому вікні")
            
        except Exception as e:
            messagebox.showerror("Помилка графіка", f"Не можу побудувати: {str(e)}\nПриклад: y=x**2 або sin(x)")

    def close_plot(self):
        """Закриває панель графіків"""
        if self.plot_frame:
            self.plot_frame.destroy()
            self.plot_frame = None


if __name__ == "__main__":

    selector = SubjectSelector()


    if selector.selected_subject:
        selected_prompt = SUBJECT_PROMPTS[selector.selected_subject]

        root = tk.Tk()
        # Передаємо і root, і назву предмету, і сам промпт
        app = ProfessionalTutorV45(root, selector.selected_subject, selected_prompt)
        root.mainloop()
