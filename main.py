import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
import schedule
from datetime import datetime
from win10toast import ToastNotifier
import time
from tkinter.filedialog import asksaveasfilename
from openpyxl import Workbook

# Файл для хранения данных
data_file = "expenses.json"
toaster = ToastNotifier() # Уведомления для напоминаний

# Загрузка данных из файла
def load_data():
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"expenses": {}, "expense_types": [], "reminders": {}}

# Загружаем данные
data = load_data()

# Сохраняем данные в файл
def save_data(data):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Обновление таблицы затрат
def update_table(date):
    # Функция для выделения дат с напоминаниями
    def highlight_reminder_dates():
        # Clear existing tags
        calendar.calevent_remove("all")

        # Add events for reminders
        for reminder_date, reminders in data.get("reminders", {}).items():
            # Convert string date to datetime.date
            try:
                date_object = datetime.strptime(reminder_date, "%m/%d/%y").date()
                calendar.calevent_create(date_object, "Напоминание", "reminder")
            except ValueError:
                continue  # Skip invalid date formats

        # Style for reminders
        calendar.tag_config("reminder", background="red", foreground="white")

    # Очищаем таблицу
    for row in table.get_children():
        table.delete(row)

    total = 0 # Общая сумма
    # Вставляем строки с затратами
    for expense in data["expenses"].get(date, []):
        table.insert("", "end", values=(expense["type"], f"{expense['amount']:.2f}"))
        total += expense["amount"]

    # Вставляем итоговую строку
    table.insert("", "end", values=("Итого по дню:", f"{total:.2f}"))
    highlight_reminder_dates()  # Выделяем даты с напоминаниями

# Обновление выпадающего списка типов затрат
def update_expense_types_dropdown():
    expense_type_entry["values"] = data["expense_types"]

# Добавление новой записи о затратах
def add_expense():
    expense_type = expense_type_var.get()
    amount = amount_var.get()
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Ошибка", "Введите корректную сумму.")
        return

    current_date = calendar.get_date()
    expenses_for_date = data["expenses"].setdefault(current_date, [])

    # Если такой тип затрат уже есть, увеличиваем его сумму
    for expense in expenses_for_date:
        if expense["type"] == expense_type:
            expense["amount"] += amount
            break
    else:
        expenses_for_date.append({"type": expense_type, "amount": amount})

    save_data(data)
    update_table(current_date)
    expense_type_var.set("")  # Очищаем поле для типа затрат
    amount_var.set("")  # Очищаем поле для суммы

# Удаление выбранной строки из таблицы
def delete_selected_row():
    selected_item = table.selection()
    if not selected_item:
        messagebox.showerror("Ошибка", "Выберите строку для удаления.")
        return

    item = selected_item[0]
    row_values = table.item(item, "values")
    if row_values[0] == "Итого по дню:":
        messagebox.showerror("Ошибка", "Невозможно удалить строку с итогом.")
        return

    current_date = calendar.get_date()
    data["expenses"][current_date] = [
        expense for expense in data["expenses"].get(current_date, [])
        if not (expense["type"] == row_values[0] and float(row_values[1]) == expense["amount"])
    ]

    save_data(data)
    update_table(current_date)

# Окно для управления типами затрат
def open_expense_types_window():
    # Добавление нового типа затрат
    def add_expense_type():
        new_type = new_type_var.get().strip()
        if new_type and new_type not in data["expense_types"]:
            data["expense_types"].append(new_type)
            save_data(data)
            update_expense_types()
            update_expense_types_dropdown()
            new_type_var.set("")

    # Обновление списка типов затрат
    def update_expense_types():
        expense_types_listbox.delete(0, tk.END)
        for expense_type in data["expense_types"]:
            expense_types_listbox.insert(tk.END, expense_type)

    # Удаление типа затрат
    def delete_expense_type():
        selected_type_index = expense_types_listbox.curselection()
        if not selected_type_index:
            messagebox.showerror("Ошибка", "Выберите тип затрат для удаления.")
            return

        selected_type = expense_types_listbox.get(selected_type_index)

        # Подтверждение удаления
        def confirm_delete(action):
            if action == "delete_all":
                for date in data["expenses"]:
                    data["expenses"][date] = [e for e in data["expenses"][date] if e["type"] != selected_type]
            elif action == "delete_type":
                for date in data["expenses"]:
                    for expense in data["expenses"][date]:
                        if expense["type"] == selected_type:
                            expense["type"] = "Удалено"
            confirm_window.destroy()

            # Remove the type from the dictionary
            data["expense_types"].remove(selected_type)
            save_data(data)
            update_expense_types()
            update_expense_types_dropdown()
            update_table(calendar.get_date())

        confirm_window = tk.Toplevel(root)
        confirm_window.title("Подтверждение удаления")

        tk.Label(confirm_window, text=f"Удалить все записи, связанные с '{selected_type}'?").pack(pady=10)

        tk.Button(confirm_window, text="Удалить всё", command=lambda: confirm_delete("delete_all")).pack(pady=5)
        tk.Button(confirm_window, text="Удалить только тип", command=lambda: confirm_delete("delete_type")).pack(pady=5)
        tk.Button(confirm_window, text="Отмена", command=confirm_window.destroy).pack(pady=5)

    # Закрыть окно
    def close_window():
        save_data(data)
        expense_types_window.destroy()

    # Окно управления типами затрат
    expense_types_window = tk.Toplevel(root)
    expense_types_window.title("Словарь видов затрат")

    new_type_var = tk.StringVar()

    tk.Label(expense_types_window, text="Добавить новый вид затрат:").pack(pady=5)
    tk.Entry(expense_types_window, textvariable=new_type_var).pack(pady=5)
    tk.Button(expense_types_window, text="Добавить", command=add_expense_type).pack(pady=5)

    tk.Label(expense_types_window, text="Список видов затрат:").pack(pady=5)
    expense_types_listbox = tk.Listbox(expense_types_window, height=10)
    expense_types_listbox.pack(pady=5)

    tk.Button(expense_types_window, text="Удалить", command=delete_expense_type).pack(pady=5)
    tk.Button(expense_types_window, text="Закрыть", command=close_window).pack(pady=5)

    update_expense_types()

# Показ статистики затрат за выбранный период
def show_statistics():
    def calculate_statistics():
        start_date = start_calendar.get_date()
        end_date = end_calendar.get_date()
        stats = {}
        total = 0
        # Считаем затраты по категориям за выбранный период
        for date, expenses in data["expenses"].items():
            if start_date <= date <= end_date:
                for expense in expenses:
                    stats[expense["type"]] = stats.get(expense["type"], 0) + expense["amount"]
                    total += expense["amount"]

        # Обновляем таблицу с результатами
        for row in table.get_children():
            table.delete(row)

        for expense_type, amount in stats.items():
            table.insert("", "end", values=(expense_type, f"{amount:.2f}"))

        table.insert("", "end", values=("Итого:", f"{total:.2f}"))
        stats_window.destroy()

    # Окно для выбора периода статистики
    stats_window = tk.Toplevel(root)
    stats_window.title("Статистика затрат")

    tk.Label(stats_window, text="Выберите диапазон дат:").pack(pady=5)

    start_calendar = Calendar(stats_window, selectmode="day")
    start_calendar.pack(pady=5)
    end_calendar = Calendar(stats_window, selectmode="day")
    end_calendar.pack(pady=5)

    tk.Button(stats_window, text="ОК", command=calculate_statistics).pack(pady=10)
    tk.Button(stats_window, text="Отмена", command=stats_window.destroy).pack(pady=5)

# Управление напоминаниями
def manage_reminders():
    # Добавление нового напоминания
    def add_reminder():
        reminder_date = reminder_calendar.get_date()
        reminder_text = reminder_text_var.get().strip()

        hour = hour_var.get()
        minute = minute_var.get()
        reminder_time = f"{hour}:{minute}"

        if not reminder_text:
            messagebox.showerror("Ошибка", "Введите текст напоминания.")
            return

        if reminder_date not in data.get("reminders", {}):
            data.setdefault("reminders", {})[reminder_date] = []

        data["reminders"][reminder_date].append({"text": reminder_text, "time": reminder_time})
        save_data(data)
        reminder_window.destroy()
        update_table(calendar.get_date())
        check_and_schedule_reminders()

    # Удаление напоминаний
    def remove_reminder():
        selected_date = reminder_calendar.get_date()

        if selected_date in data.get("reminders", {}):
            data["reminders"].pop(selected_date)
            save_data(data)
            messagebox.showinfo("Успех", "Напоминания удалены для выбранной даты.")
        else:
            messagebox.showerror("Ошибка", "На выбранную дату нет напоминаний.")
        update_table(calendar.get_date())

    # Окно для управления напоминаниями
    reminder_window = tk.Toplevel(root)
    reminder_window.title("Управление напоминаниями")

    tk.Label(reminder_window, text="Выберите дату:").pack(pady=5)
    reminder_calendar = Calendar(reminder_window, selectmode="day")
    reminder_calendar.pack(pady=5)

    reminder_text_var = tk.StringVar()
    tk.Label(reminder_window, text="Текст напоминания:").pack(pady=5)
    tk.Entry(reminder_window, textvariable=reminder_text_var).pack(pady=5)

    # Time selection
    tk.Label(reminder_window, text="Время (часы и минуты):").pack(pady=5)
    time_frame = tk.Frame(reminder_window)
    time_frame.pack(pady=5)

    hour_var = tk.StringVar(value="00")
    minute_var = tk.StringVar(value="00")

    tk.Spinbox(time_frame, from_=0, to=23, textvariable=hour_var, width=3, format="%02.0f").pack(side="left")
    tk.Label(time_frame, text=":").pack(side="left")
    tk.Spinbox(time_frame, from_=0, to=59, textvariable=minute_var, width=3, format="%02.0f").pack(side="left")

    tk.Button(reminder_window, text="Добавить напоминание", command=add_reminder).pack(pady=10)
    tk.Button(reminder_window, text="Удалить напоминания для даты", command=remove_reminder).pack(pady=5)
    tk.Button(reminder_window, text="Закрыть", command=reminder_window.destroy).pack(pady=5)

# Экспорт данных в Excel
def export_expenses():
    # Сохранение данных в файл Excel
    def save_to_excel():
        start_date = start_calendar.get_date()
        end_date = end_calendar.get_date()

        filtered_data = {date: expenses for date, expenses in data["expenses"].items() if
                         start_date <= date <= end_date}

        file_path = asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Затраты"

        # Генерация заголовков
        sheet.append(["Дата"] + list(data["expense_types"]))

        # Заполнение строк данными
        for date, expenses in filtered_data.items():
            row = [date]
            expense_dict = {expense["type"]: expense["amount"] for expense in expenses}
            for expense_type in data["expense_types"]:
                row.append(expense_dict.get(expense_type, 0))
            sheet.append(row)

        workbook.save(file_path)
        stats_window.destroy()
        messagebox.showinfo("Успех", f"Файл сохранен: {file_path}")

    # Окно выбора диапазона дат
    stats_window = tk.Toplevel(root)
    stats_window.title("Экспорт в Excel")

    tk.Label(stats_window, text="Выберите диапазон дат:").pack(pady=5)

    start_calendar = Calendar(stats_window, selectmode="day")
    start_calendar.pack(pady=5)
    end_calendar = Calendar(stats_window, selectmode="day")
    end_calendar.pack(pady=5)

    tk.Button(stats_window, text="Экспортировать", command=save_to_excel).pack(pady=10)
    tk.Button(stats_window, text="Отмена", command=stats_window.destroy).pack(pady=5)


def send_reminder_notification(reminder_text):
    #Отправляет системное уведомление.
    toaster.show_toast("Напоминание", reminder_text, duration=10)
def check_and_schedule_reminders():
    #Проверяет напоминания на сегодня и добавляет их в планировщик.
    today = datetime.now().strftime("%m/%d/%y")
    reminders = data.get("reminders", {}).get(today, [])

    for reminder in reminders:
        reminder_time = reminder.get("time", "00:00")
        reminder_text = reminder.get("text", "Напоминание")

        # Парсим время напоминания
        try:
            reminder_hour, reminder_minute = map(int, reminder_time.split(":"))
            reminder_datetime = datetime.now().replace(
                hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0
            )
            # Если время еще не прошло, добавляем в расписание
            if reminder_datetime > datetime.now():
                schedule_time = reminder_datetime.strftime("%H:%M")
                schedule.every().day.at(schedule_time).do(send_reminder_notification, reminder_text)
        except ValueError:
            continue  # Пропускаем некорректные записи времени
def start_scheduler():
    """Запускает цикл обработки задач расписания."""
    while True:
        schedule.run_pending()
        time.sleep(1)

check_and_schedule_reminders()
schedule.every().day.at("00:00").do(check_and_schedule_reminders)
scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()

# Основное окно приложения
root = tk.Tk()
root.title("Учет затрат")

toolbar = tk.Menu(root)
root.config(menu=toolbar)

# Меню для работы с файлами
file_menu = tk.Menu(toolbar, tearoff=0)
file_menu.add_command(label="Словарь видов затрат", command=open_expense_types_window)
file_menu.add_command(label="Показать статистику", command=show_statistics)
file_menu.add_command(label="Экспорт данных", command=export_expenses)
file_menu.add_separator()
file_menu.add_command(label="Управление напоминаниями", command=manage_reminders)
file_menu.add_separator()
file_menu.add_command(label="Выход", command=root.quit)

toolbar.add_cascade(label="Меню", menu=file_menu)

# Календарь для выбора даты
calendar = Calendar(root, selectmode="day")
calendar.grid(row=1, column=0, padx=10, pady=10, sticky="n")
calendar.bind("<<CalendarSelected>>", lambda event: update_table(calendar.get_date()))

# Таблица для отображения расходов
columns = ("Вид затрат", "Цена")
table = ttk.Treeview(root, columns=columns, show="headings")
table.heading("Вид затрат", text="Вид затрат")
table.heading("Цена", text="Цена")
table.column("Вид затрат", width=150)
table.column("Цена", width=100)
table.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

# Поля ввода для добавления новых затрат
expense_type_var = tk.StringVar()
amount_var = tk.StringVar()

expense_type_label = tk.Label(root, text="Вид затрат:")
expense_type_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
expense_type_entry = ttk.Combobox(root, textvariable=expense_type_var)
expense_type_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
update_expense_types_dropdown()

amount_label = tk.Label(root, text="Сумма:")
amount_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
amount_entry = tk.Entry(root, textvariable=amount_var)
amount_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")

# Кнопки для добавления и удаления строк в таблице
add_button = tk.Button(root, text="Добавить", command=add_expense)
add_button.grid(row=4, column=1, padx=5, pady=5, sticky="w")

delete_button = tk.Button(root, text="Удалить", command=delete_selected_row)
delete_button.grid(row=4, column=1, padx=5, pady=5, sticky="e")

# Настройка изменения размера элементов интерфейса
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(1, weight=1)

# Инициализация таблицы с текущей датой
update_table(calendar.get_date())

# Запуск основного цикла приложения
root.mainloop()
