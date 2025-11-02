import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ttkbootstrap import Style
from datetime import date, datetime
import matplotlib.pyplot as plt
import pandas as pd

class ExpenseDB:
    def __init__(self, db_name="expenses.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            amount REAL,
            date TEXT,
            description TEXT
        )
        """)
        self.conn.commit()

    def add_expense(self, category, amount, d, desc):
        self.cursor.execute(
            "INSERT INTO expenses (category, amount, date, description) VALUES (?, ?, ?, ?)",
            (category, amount, d, desc)
        )
        self.conn.commit()

    def fetch_all(self):
        self.cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
        return self.cursor.fetchall()

    def fetch_filtered(self, category=None, start_date=None, end_date=None):
        query = "SELECT * FROM expenses WHERE 1=1"
        params = []
        if category and category != "All":
            query += " AND category=?"
            params.append(category)
        if start_date:
            query += " AND date>=?"
            params.append(start_date)
        if end_date:
            query += " AND date<=?"
            params.append(end_date)
        query += " ORDER BY date DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def delete_expense(self, expense_id):
        self.cursor.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        self.conn.commit()

    def get_summary(self):
        self.cursor.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
        return self.cursor.fetchall()

    def get_stats(self):
        today = str(date.today())
        self.cursor.execute("SELECT SUM(amount) FROM expenses WHERE date=?", (today,))
        today_total = self.cursor.fetchone()[0] or 0

        month_prefix = today[:7]
        self.cursor.execute("SELECT SUM(amount) FROM expenses WHERE date LIKE ?", (f"{month_prefix}%",))
        month_total = self.cursor.fetchone()[0] or 0

        self.cursor.execute("SELECT SUM(amount) FROM expenses")
        all_total = self.cursor.fetchone()[0] or 0

        return today_total, month_total, all_total


class ExpenseTrackerApp:
    def __init__(self, root):
        self.db = ExpenseDB()
        self.root = root
        self.root.title("💵 Expense Dashboard")
        self.root.geometry("1200x750")

        self.style = Style(theme="flatly")
        self.create_ui()
        self.load_data()
        self.update_stats()

    def create_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)

        header = ttk.Label(main_frame, text="💰 Expense Dashboard", font=("Helvetica", 22, "bold"))
        header.pack(pady=10)

        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill="x", pady=10)
        self.stat_today = ttk.Label(stats_frame, text="", font=("Helvetica", 14))
        self.stat_month = ttk.Label(stats_frame, text="", font=("Helvetica", 14))
        self.stat_total = ttk.Label(stats_frame, text="", font=("Helvetica", 14))
        self.stat_today.pack(side="left", padx=20)
        self.stat_month.pack(side="left", padx=20)
        self.stat_total.pack(side="left", padx=20)

        form_frame = ttk.Labelframe(main_frame, text="Add Expense", padding=10)
        form_frame.pack(fill="x", pady=10)

        self.category_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.date_var = tk.StringVar(value=str(date.today()))
        self.desc_var = tk.StringVar()

        categories = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Others"]
        ttk.Label(form_frame, text="Category:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Combobox(form_frame, textvariable=self.category_var, values=categories, state="readonly").grid(row=0, column=1, pady=5)
        ttk.Label(form_frame, text="Amount:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        ttk.Entry(form_frame, textvariable=self.amount_var).grid(row=0, column=3, pady=5)
        ttk.Label(form_frame, text="Date (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(form_frame, textvariable=self.date_var).grid(row=1, column=1, pady=5)
        ttk.Label(form_frame, text="Description:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        ttk.Entry(form_frame, textvariable=self.desc_var, width=40).grid(row=1, column=3, pady=5)

        ttk.Button(form_frame, text="Add Expense", bootstyle="success", command=self.add_expense).grid(row=2, column=0, pady=10)
        ttk.Button(form_frame, text="Export to Excel", bootstyle="info", command=self.export_excel).grid(row=2, column=1, pady=10)
        ttk.Button(form_frame, text="Clear", bootstyle="secondary", command=self.clear_fields).grid(row=2, column=2, pady=10)
        ttk.Button(form_frame, text="Delete Selected", bootstyle="danger", command=self.delete_selected).grid(row=2, column=3, pady=10)

        filter_frame = ttk.Labelframe(main_frame, text="Filters", padding=10)
        filter_frame.pack(fill="x", pady=10)

        self.filter_category = tk.StringVar(value="All")
        self.filter_start = tk.StringVar()
        self.filter_end = tk.StringVar()

        ttk.Label(filter_frame, text="Category:").grid(row=0, column=0, padx=5)
        ttk.Combobox(filter_frame, textvariable=self.filter_category,
                     values=["All", "Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"],
                     state="readonly").grid(row=0, column=1, padx=5)
        ttk.Label(filter_frame, text="Start Date:").grid(row=0, column=2, padx=5)
        ttk.Entry(filter_frame, textvariable=self.filter_start).grid(row=0, column=3, padx=5)
        ttk.Label(filter_frame, text="End Date:").grid(row=0, column=4, padx=5)
        ttk.Entry(filter_frame, textvariable=self.filter_end).grid(row=0, column=5, padx=5)
        ttk.Button(filter_frame, text="Apply Filter", bootstyle="primary", command=self.apply_filter).grid(row=0, column=6, padx=10)
        ttk.Button(filter_frame, text="Show Charts", bootstyle="warning", command=self.show_charts).grid(row=0, column=7, padx=10)

        table_frame = ttk.Labelframe(main_frame, text="Expense Records", padding=10)
        table_frame.pack(fill="both", expand=True)

        columns = ("ID", "Category", "Amount", "Date", "Description")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=150)
        self.tree.pack(fill="both", expand=True)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=y_scroll.set)
        y_scroll.pack(side="right", fill="y")

        self.status = ttk.Label(main_frame, text="Connected to database.", anchor="w")
        self.status.pack(fill="x", pady=(5, 0))

    def add_expense(self):
        category = self.category_var.get()
        amount = self.amount_var.get()
        d = self.date_var.get()
        desc = self.desc_var.get()

        if not category or not amount:
            messagebox.showerror("Error", "Please fill all required fields.")
            return

        try:
            float(amount)
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Check your amount and date format (YYYY-MM-DD).")
            return

        self.db.add_expense(category, float(amount), d, desc)
        self.clear_fields()
        self.load_data()
        self.update_stats()

    def load_data(self, filtered_data=None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = filtered_data if filtered_data else self.db.fetch_all()
        for row in rows:
            self.tree.insert("", tk.END, values=row)
        self.status.config(text=f"Loaded {len(rows)} records.")

    def apply_filter(self):
        data = self.db.fetch_filtered(
            category=self.filter_category.get(),
            start_date=self.filter_start.get(),
            end_date=self.filter_end.get()
        )
        self.load_data(filtered_data=data)

    def clear_fields(self):
        self.category_var.set("")
        self.amount_var.set("")
        self.date_var.set(str(date.today()))
        self.desc_var.set("")

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select an expense to delete.")
            return
        confirm = messagebox.askyesno("Confirm", "Delete selected record(s)?")
        if confirm:
            for sel in selected:
                expense_id = self.tree.item(sel)["values"][0]
                self.db.delete_expense(expense_id)
            self.load_data()
            self.update_stats()

    def show_charts(self):
        data = self.db.get_summary()
        if not data:
            messagebox.showinfo("No Data", "No expenses to chart.")
            return

        categories = [d[0] for d in data]
        amounts = [d[1] for d in data]

        fig, ax = plt.subplots(1, 2, figsize=(10, 5))

        ax[0].pie(amounts, labels=categories, autopct="%1.1f%%", startangle=140)
        ax[0].set_title("By Category")

        ax[1].bar(categories, amounts)
        ax[1].set_title("Spending per Category")
        ax[1].set_ylabel("Amount")

        plt.tight_layout()
        plt.show()

    def export_excel(self):
        data = self.db.fetch_all()
        if not data:
            messagebox.showinfo("No Data", "Nothing to export.")
            return

        df = pd.DataFrame(data, columns=["ID", "Category", "Amount", "Date", "Description"])
        file = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
        if file:
            df.to_excel(file, index=False)
            messagebox.showinfo("Exported", f"Data exported successfully to {file}")

    def update_stats(self):
        today_total, month_total, all_total = self.db.get_stats()
        self.stat_today.config(text=f"Today: ₹{today_total:.2f}")
        self.stat_month.config(text=f"This Month: ₹{month_total:.2f}")
        self.stat_total.config(text=f"All Time: ₹{all_total:.2f}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ExpenseTrackerApp(root)
    root.mainloop()
