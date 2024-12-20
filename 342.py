import json
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
from win10toast import ToastNotifier
import schedule
import time
from datetime import datetime
from win10toast import ToastNotifier
import time

# Initialize data storage file
data_file = "expenses.json"
toaster = ToastNotifier()
def load_data():
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"expenses": {}, "expense_types": [], "reminders": {}}

# Load initial data
data = load_data()

def save_data(data):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)



def update_table(date):
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
    for row in table.get_children():
        table.delete(row)

    total = 0
    for expense in data["expenses"].get(date, []):
        table.insert("", "end", values=(expense["type"], f"{expense['amount']:.2f}"))
        total += expense["amount"]

    # Add a summary row
    table.insert("", "end", values=("Итого по дню:", f"{total:.2f}"))
    highlight_reminder_dates()




def update_expense_types_dropdown():
    expense_type_entry["values"] = data["expense_types"]

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

    # Check if expense type already exists for the date
    for expense in expenses_for_date:
        if expense["type"] == expense_type:
            expense["amount"] += amount
            break
    else:
        expenses_for_date.append({"type": expense_type, "amount": amount})

    save_data(data)
    update_table(current_date)
    expense_type_var.set("")
    amount_var.set("")

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

def open_expense_types_window():
    def add_expense_type():
        new_type = new_type_var.get().strip()
        if new_type and new_type not in data["expense_types"]:
            data["expense_types"].append(new_type)
            save_data(data)
            update_expense_types()
            update_expense_types_dropdown()
            new_type_var.set("")

    def update_expense_types():
        expense_types_listbox.delete(0, tk.END)
        for expense_type in data["expense_types"]:
            expense_types_listbox.insert(tk.END, expense_type)

    def delete_expense_type():
        selected_type_index = expense_types_listbox.curselection()
        if not selected_type_index:
            messagebox.showerror("Ошибка", "Выберите тип затрат для удаления.")
            return

        selected_type = expense_types_listbox.get(selected_type_index)

        # Custom confirmation dialog
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

    def close_window():
        save_data(data)
        expense_types_window.destroy()

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

def show_statistics():
    def calculate_statistics():
        start_date = start_calendar.get_date()
        end_date = end_calendar.get_date()

        stats = {}
        total = 0
        for date, expenses in data["expenses"].items():
            if start_date <= date <= end_date:
                for expense in expenses:
                    stats[expense["type"]] = stats.get(expense["type"], 0) + expense["amount"]
                    total += expense["amount"]

        for row in table.get_children():
            table.delete(row)

        for expense_type, amount in stats.items():
            table.insert("", "end", values=(expense_type, f"{amount:.2f}"))

        table.insert("", "end", values=("Итого:", f"{total:.2f}"))
        stats_window.destroy()

    stats_window = tk.Toplevel(root)
    stats_window.title("Статистика затрат")

    tk.Label(stats_window, text="Выберите диапазон дат:").pack(pady=5)

    start_calendar = Calendar(stats_window, selectmode="day")
    start_calendar.pack(pady=5)
    end_calendar = Calendar(stats_window, selectmode="day")
    end_calendar.pack(pady=5)

    tk.Button(stats_window, text="ОК", command=calculate_statistics).pack(pady=10)
    tk.Button(stats_window, text="Отмена", command=stats_window.destroy).pack(pady=5)

#####
# Function to handle reminders
# Function to handle reminders with date and time

def manage_reminders():
    def add_reminder():
        reminder_date = reminder_calendar.get_date()
        reminder_text = reminder_text_var.get().strip()
        is_monthly = monthly_var.get()

        hour = hour_var.get()
        minute = minute_var.get()
        reminder_time = f"{hour}:{minute}"

        if not reminder_text:
            messagebox.showerror("Ошибка", "Введите текст напоминания.")
            return

        if reminder_date not in data.get("reminders", {}):
            data.setdefault("reminders", {})[reminder_date] = []

        data["reminders"][reminder_date].append({"text": reminder_text, "time": reminder_time, "monthly": is_monthly})
        save_data(data)
        reminder_window.destroy()
        update_table(calendar.get_date())

    def remove_reminder():
        selected_date = reminder_calendar.get_date()

        if selected_date in data.get("reminders", {}):
            data["reminders"].pop(selected_date)
            save_data(data)
            messagebox.showinfo("Успех", "Напоминания удалены для выбранной даты.")
        else:
            messagebox.showerror("Ошибка", "На выбранную дату нет напоминаний.")
        update_table(calendar.get_date())

    # Reminder management window
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

    monthly_var = tk.BooleanVar()
    tk.Checkbutton(reminder_window, text="Повторять ежемесячно", variable=monthly_var).pack(pady=5)

    tk.Button(reminder_window, text="Добавить напоминание", command=add_reminder).pack(pady=10)
    tk.Button(reminder_window, text="Удалить напоминания для даты", command=remove_reminder).pack(pady=5)
    tk.Button(reminder_window, text="Закрыть", command=reminder_window.destroy).pack(pady=5)

#####


# Main application window
root = tk.Tk()
root.title("Учет затрат")

# Toolbar setup
toolbar = tk.Menu(root)
root.config(menu=toolbar)

file_menu = tk.Menu(toolbar, tearoff=0)
file_menu.add_command(label="Словарь видов затрат", command=open_expense_types_window)
file_menu.add_command(label="Показать статистику", command=show_statistics)
file_menu.add_separator()
file_menu.add_command(label="Выход", command=root.quit)

# Add "Manage Reminders" option in toolbar menu
file_menu.add_command(label="Управление напоминаниями", command=manage_reminders)


toolbar.add_cascade(label="Меню", menu=file_menu)

# Date and calendar
calendar = Calendar(root, selectmode="day")
calendar.grid(row=1, column=0, padx=10, pady=10, sticky="n")
calendar.bind("<<CalendarSelected>>", lambda event: update_table(calendar.get_date()))

# Expense table
columns = ("Вид затрат", "Цена")
table = ttk.Treeview(root, columns=columns, show="headings")
table.heading("Вид затрат", text="Вид затрат")
table.heading("Цена", text="Цена")
table.column("Вид затрат", width=150)
table.column("Цена", width=100)
table.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

# Input fields for adding expenses
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

# Add and delete buttons
add_button = tk.Button(root, text="Добавить", command=add_expense)
add_button.grid(row=4, column=1, padx=5, pady=5, sticky="w")

delete_button = tk.Button(root, text="Удалить", command=delete_selected_row)
delete_button.grid(row=4, column=1, padx=5, pady=5, sticky="e")

# Configure resizing
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(1, weight=1)

# Initial table update
print(calendar.get_date())
update_table(calendar.get_date())

# Start the main loop
root.mainloop()
