# NostrixStockEngine.py
import sqlite3
import yfinance as yf
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image
import math
import os

DB_FILE = "portfolio.db"

class NostrixStockEngine:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.portfolio = {}
        self.watchlist = {}
        self.ensure_db()
        self.load_portfolio()

    # ---------------- DATABASE ----------------
    def ensure_db(self):
        if not os.path.exists(self.db_file):
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            c.execute("""CREATE TABLE portfolio (ticker TEXT PRIMARY KEY, qty INTEGER, avg REAL)""")
            conn.commit()
            conn.close()

    def log_to_db(self, ticker, qty, avg):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO portfolio VALUES (?, ?, ?)", (ticker, qty, avg))
        conn.commit()
        conn.close()

    def load_portfolio(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT ticker, qty, avg FROM portfolio")
        self.portfolio = {t: {"qty": q, "avg": a} for t, q, a in c.fetchall()}
        conn.close()

    # ---------------- STOCK SIGNAL ----------------
    def predict_signal(self, ticker):
        t = yf.Ticker(ticker)
        hist = t.history(period="6mo")["Close"]
        if len(hist) < 5:
            return 0, "HOLD"
        m20 = hist.iloc[-1]/hist.iloc[-20]-1 if len(hist) > 20 else 0
        m50 = hist.iloc[-1]/hist.iloc[-50]-1 if len(hist) > 50 else 0
        score = sum([m20>0.05, m50>0.08])
        sig = "BUY" if score >= 2 else ("SELL" if score == 0 else "HOLD")
        future = hist.iloc[-1] * (1 + m20)
        return future, sig

    # ---------------- PORTFOLIO OPERATIONS ----------------
    def buy(self, ticker, qty):
        price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
        p = self.portfolio.get(ticker, {"qty": 0, "avg": 0})
        new_qty = p["qty"] + qty
        new_avg = ((p["avg"] * p["qty"]) + price * qty) / new_qty
        self.portfolio[ticker] = {"qty": new_qty, "avg": new_avg}
        self.log_to_db(ticker, new_qty, new_avg)
        return f"Bought {qty} {ticker} @ {price:.2f}"

    def show_portfolio(self):
        output = []
        for t, p in self.portfolio.items():
            pred, sig = self.predict_signal(t)
            bar = "█" * int((pred / p["avg"]) * 10)
            output.append(f"{t} | Qty:{p['qty']} | Avg:{p['avg']:.2f} | Signal:{sig} | Pred:{pred:.2f} {bar}")
        return "\n".join(output)

    def track(self, ticker):
        pred, sig = self.predict_signal(ticker)
        self.watchlist[ticker.upper()] = {"pred": pred, "sig": sig}
        return f"Tracking {ticker.upper()} | Signal:{sig} | Pred:{pred:.2f}"

    def show_watchlist(self):
        output = []
        for t, d in self.watchlist.items():
            avg = self.portfolio.get(t, {"avg": 1})["avg"]
            bar = "█" * int((d["pred"] / avg) * 10)
            output.append(f"{t} | Pred:{d['pred']:.2f} | Signal:{d['sig']} {bar}")
        return "\n".join(output)

    # ---------------- CHARTING ----------------
    def show_chart(self, ticker):
        t = yf.Ticker(ticker)
        hist = t.history(period="6mo")["Close"]
        plt.figure(figsize=(8, 4))
        plt.plot(hist.index, hist.values)
        plt.title(f"{ticker} Chart")
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img = Image.open(buf)
        img.show()

    # ---------------- UTILITY ----------------
    def calc(self, expr):
        try:
            return eval(expr, {"__builtins__": None, "math": math})
        except Exception:
            return "ERROR"

    def unit_convert(self, value, frm, to):
        frm, to = frm.upper(), to.upper()
        if frm == "USD" and to == "EUR": return value * 0.91
        if frm == "EUR" and to == "USD": return value * 1.1
        return f"Unsupported conversion {frm} -> {to}"
