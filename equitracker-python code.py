import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from datetime import datetime

# PostgreSQL connection details (update with your credentials)
DB_HOST = "localhost"
DB_NAME = "postgres"  # e.g., "equitracker_db"
DB_USER = "postgres"
DB_PASS = "dca4311417"
DB_PORT = 5432

# Connect to PostgreSQL
def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS,port=DB_PORT)

# Fetch and update data for a single stock (updates current_price and last_updated)
def fetch_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol + ".NS")  # Assuming NSE symbols
        info = stock.info
        current_price = info.get('currentPrice', 0)
        last_updated = datetime.now()
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE companies SET current_price=%s, last_updated=%s WHERE symbol=%s",
                  (current_price, last_updated, symbol))
        conn.commit()
        conn.close()
        return current_price
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch data for {symbol}: {str(e)}")
        return None

# Get stock history for graph
def get_stock_history(symbol):
    try:
        stock = yf.Ticker(symbol + ".NS")
        hist = stock.history(period="1mo")
        return hist['Close']
    except:
        return pd.Series()

# Generate insights based on DB data
def generate_insights(pe_ratio, pb_ratio, dividend_yield, market_cap_inr_crore):
    insights = []
    if pe_ratio and pe_ratio < 15:
        insights.append(("Undervalued (Low P/E) – Potential Buy", "green"))
    elif pe_ratio and pe_ratio > 30:
        insights.append(("Overvalued (High P/E) – Consider Sell", "red"))
    else:
        insights.append(("Fairly Valued P/E", "blue"))
    
    if pb_ratio and pb_ratio < 2:
        insights.append(("Attractive Valuation (Low P/B)", "green"))
    elif pb_ratio and pb_ratio > 5:
        insights.append(("Expensive (High P/B)", "red"))
    
    if dividend_yield and dividend_yield > 2:
        insights.append(("High Dividend Yield – Income Focus", "green"))
    elif dividend_yield and dividend_yield < 1:
        insights.append(("Low Dividend Yield", "orange"))
    
    if market_cap_inr_crore and market_cap_inr_crore > 500000:
        insights.append(("Large Cap – Stable Investment", "green"))
    return insights

# Main App Class with Multi-Page Navigation
class EquiTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EquiTracker")
        self.root.geometry("1100x850")
        self.root.configure(bg="#f5f5f5")
        self.root.resizable(True, True)
        
        # Style Configuration
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 10, "bold"), background="#007bff", foreground="#ffffff", borderwidth=1)
        style.map("TButton", background=[("active", "#0056b3")])
        style.configure("TEntry", font=("Arial", 12), borderwidth=2, relief="flat")
        # Updated style for Back button: Black text on white background
        style.configure("Back.TButton", font=("Arial", 10, "bold"), background="#ffffff", foreground="#000000", borderwidth=1)
        style.map("Back.TButton", background=[("active", "#f0f0f0")])  # Light gray on hover
        
        # Main Container
        self.container = tk.Frame(root, bg="#f5f5f5")
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # Homepage Frame
        self.homepage_frame = tk.Frame(self.container, bg="#f5f5f5")
        self.create_homepage()
        
        # Details Frame
        self.details_frame = tk.Frame(self.container, bg="#f5f5f5")
        self.create_details_page()
        
        # Show Homepage Initially
        self.show_homepage()
        
        self.selected_symbol = None
    
    def create_homepage(self):
        # Centered Layout
        center_frame = tk.Frame(self.homepage_frame, bg="#f5f5f5")
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # App Title
        app_title = tk.Label(center_frame, text="EquiTracker", font=("Arial", 36, "bold"), bg="#f5f5f5", fg="#333333")
        app_title.pack(pady=(0, 30))
        
        # Search Container
        search_container = tk.Frame(center_frame, bg="#f5f5f5")
        search_container.pack(pady=20)
        search_icon = tk.Label(search_container, text="🔍", font=("Arial", 16), bg="#f5f5f5", fg="#007bff")
        search_icon.pack(side=tk.LEFT, padx=(0, 10))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_container, textvariable=self.search_var, font=("Arial", 14), width=40)
        self.search_entry.pack(side=tk.LEFT)
        self.search_entry.insert(0, "Search for stocks...")
        self.search_entry.bind("<FocusIn>", self.clear_placeholder)
        self.search_entry.bind("<FocusOut>", self.add_placeholder)
        self.search_entry.bind("<KeyRelease>", self.update_suggestions)
        
        # Suggestions Listbox
        self.suggestions_listbox = tk.Listbox(center_frame, height=8, bg="#ffffff", fg="#333333", font=("Arial", 12),
                                              selectbackground="#007bff", selectforeground="#ffffff", relief="flat", borderwidth=1,
                                              highlightbackground="#cccccc", highlightthickness=1)
        self.suggestions_listbox.pack(pady=20, fill=tk.X)
        self.suggestions_listbox.bind("<<ListboxSelect>>", self.select_suggestion)
    
    def create_details_page(self):
        # Back Button with Black Text on White Background
        back_button = ttk.Button(self.details_frame, text="← Back to Home", style="Back.TButton", command=self.show_homepage)
        back_button.pack(pady=10, padx=20, anchor=tk.W)
        
        # Display Frame
        display_frame = tk.Frame(self.details_frame, bg="#f5f5f5", relief="groove", bd=1)
        display_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Details Label
        self.details_label = tk.Label(display_frame, text="", bg="#f5f5f5", fg="#333333", font=("Arial", 12), justify=tk.LEFT, anchor="w", wraplength=1000)
        self.details_label.pack(fill=tk.X, pady=10, padx=10)
        
        # Graph Canvas
        self.figure = plt.Figure(figsize=(7, 4), dpi=100, facecolor="#f5f5f5")
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=display_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Insights Label
        self.insights_label = tk.Label(display_frame, text="", bg="#f5f5f5", fg="#333333", font=("Arial", 12), justify=tk.LEFT, anchor="w", wraplength=1000)
        self.insights_label.pack(fill=tk.X, pady=10, padx=10)
    
    def show_homepage(self):
        self.details_frame.pack_forget()
        self.homepage_frame.pack(fill=tk.BOTH, expand=True)
        self.selected_symbol = None
        self.details_label.config(text="")
        self.insights_label.config(text="")
        self.ax.clear()
        self.canvas.draw()
    
    def show_details_page(self):
        self.homepage_frame.pack_forget()
        self.details_frame.pack(fill=tk.BOTH, expand=True)
    
    def clear_placeholder(self, event):
        if self.search_entry.get() == "Search for stocks...":
            self.search_entry.delete(0, tk.END)
    
    def add_placeholder(self, event):
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search for stocks...")
    
    def update_suggestions(self, event):
        query = self.search_var.get().lower()
        if query == "search for stocks...":
            return
        if not query:
            self.suggestions_listbox.delete(0, tk.END)
            return
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT symbol, name FROM companies WHERE LOWER(name) LIKE %s OR LOWER(symbol) LIKE %s LIMIT 10",
                  (f"%{query}%", f"%{query}%"))
        results = c.fetchall()
        conn.close()
        
        self.suggestions_listbox.delete(0, tk.END)
        for symbol, name in results:
            self.suggestions_listbox.insert(tk.END, f"{name} ({symbol})")
    
    def select_suggestion(self, event):
        selection = self.suggestions_listbox.get(self.suggestions_listbox.curselection())
        self.selected_symbol = selection.split("(")[-1].strip(")")
        
        # Fetch data and switch to details page
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name, industry, founded, headquarters, description, current_price, market_cap_inr_crore, pe_ratio, pb_ratio, dividend_yield FROM companies WHERE symbol=%s",
                  (self.selected_symbol,))
        row = c.fetchone()
        conn.close()
        
        if row:
            name, industry, founded, headquarters, description, current_price, market_cap_inr_crore, pe_ratio, pb_ratio, dividend_yield = row
            details = (f"Company: {name} ({self.selected_symbol})\n"
                       f"Industry: {industry}\n"
                       f"Founded: {founded}\n"
                       f"Headquarters: {headquarters}\n"
                       f"Description: {description}\n"
                       f"Current Price: ₹{current_price}\n"
                       f"Market Cap: ₹{market_cap_inr_crore} Cr\n"
                       f"P/E Ratio: {pe_ratio}\n"
                       f"P/B Ratio: {pb_ratio}\n"
                       f"Dividend Yield: {dividend_yield}%")
            self.details_label.config(text=details)
            
            # Graph
            self.ax.clear()
            hist = get_stock_history(self.selected_symbol)
            if not hist.empty:
                hist.plot(ax=self.ax, color="#007bff")
                self.ax.set_title(f"{name} Price History (Last 30 Days)", fontsize=14, color="#333333")
                self.ax.set_xlabel("Date", fontsize=12, color="#333333")
                self.ax.set_ylabel("Price (₹)", fontsize=12, color="#333333")
                self.ax.tick_params(colors="#333333")
            self.canvas.draw()
            
            # Insights
            insights = generate_insights(pe_ratio, pb_ratio, dividend_yield, market_cap_inr_crore)
            insight_text = "Insights:\n"
            for text, color in insights:
                insight_text += f"• {text}\n"
            self.insights_label.config(text=insight_text, fg=color)
        
        # Switch to details page
        self.show_details_page()

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = EquiTrackerApp(root)
    root.mainloop()