

import yfinance as yf

class STOCKENGINE:
    def __init__(self):
        self.portfolio = {}
        self.watchlist = {}

    # Simple logger
    def log(self, msg):
        print(msg)

    def save_portfolio(self):
        pass  # placeholder (can connect DB/file later)

    # ---------------- SIGNAL PREDICTION ----------------
    def predict_signal(self, ticker):
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="6mo")

            if hist.empty:
                return 0, "NO DATA"

            close = hist["Close"]

            if len(close) < 5:
                return close.iloc[-1], "HOLD"

            m20 = (close.iloc[-1] / close.iloc[-20] - 1) if len(close) >= 20 else 0
            m50 = (close.iloc[-1] / close.iloc[-50] - 1) if len(close) >= 50 else 0

            score = sum([m20 > 0.05, m50 > 0.08])

            if score >= 2:
                signal = "BUY"
            elif score == 0:
                signal = "SELL"
            else:
                signal = "HOLD"

            future = close.iloc[-1] * (1 + m20)

            return future, signal

        except:
            return 0, "ERROR"

    # ---------------- BUY ----------------
    def buy(self, ticker, qty):
        price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]

        if ticker not in self.portfolio:
            self.portfolio[ticker] = {"qty": 0, "avg": 0}

        p = self.portfolio[ticker]
        new_qty = p["qty"] + qty

        p["avg"] = ((p["avg"] * p["qty"]) + price * qty) / new_qty
        p["qty"] = new_qty

        self.save_portfolio()
        self.log(f"Bought {qty} {ticker} @ {price:.2f}")

    # ---------------- PORTFOLIO ----------------
    def show_portfolio(self):
        self.log("=== PORTFOLIO ===")

        for t, p in self.portfolio.items():
            pred, sig = self.predict_signal(t)

            base = p["avg"] if p["avg"] > 0 else 1
            ratio = max(min(pred / base, 2), 0)  # clamp between 0–2
            bar = "█" * int(ratio * 10)

            self.log(f"{t} | Qty:{p['qty']} | Avg:{p['avg']:.2f} | Signal:{sig} | Pred:{pred:.2f} {bar}")

    # ---------------- WATCHLIST ----------------
    def track(self, ticker):
        pred, sig = self.predict_signal(ticker)
        self.watchlist[ticker.upper()] = {"pred": pred, "sig": sig}
        self.log(f"Tracking {ticker.upper()} | Signal:{sig} | Pred:{pred:.2f}")

    def show_watchlist(self):
        self.log("=== WATCHLIST ===")

        for t, d in self.watchlist.items():
            base = self.portfolio.get(t, {"avg": 1})["avg"]
            ratio = max(min(d["pred"] / base, 2), 0)
            bar = "█" * int(ratio * 10)

            self.log(f"{t} | Pred:{d['pred']:.2f} | Signal:{d['sig']} {bar}")

    # ---------------- TECHNICALS ----------------
    def technicals(self, ticker):
        t = yf.Ticker(ticker)
        hist = t.history(period="6mo")

        if hist.empty:
            self.log("No data")
            return

        close = hist["Close"]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma50 = close.rolling(50).mean().iloc[-1]

        self.log(f"{ticker.upper()} | Close:{close.iloc[-1]:.2f} | 20MA:{ma20:.2f} | 50MA:{ma50:.2f}")

    # ---------------- UPDATE WATCHLIST ----------------
    def update_watchlist(self):
        for t in self.watchlist:
            try:
                price = yf.Ticker(t).history(period="1d")["Close"].iloc[-1]
                self.watchlist[t]["price"] = price
            except:
                self.watchlist[t]["price"] = 0
