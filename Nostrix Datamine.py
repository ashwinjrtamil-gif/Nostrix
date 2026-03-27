import sys, json, numpy as np
import yfinance as yf
from curl_cffi import requests as stealth_requests
from bs4 import BeautifulSoup
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QTimer, QEvent

# ---------------- TRUST SOURCES ----------------
TRUST_SOURCES = ["wikipedia.org","reuters.com","bloomberg.com","investopedia.com","sec.gov","nytimes.com"]

# ---------------- MAIN ----------------
class NostrixTerminal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOSTRIX v36 TERMINAL")
        self.resize(1400, 900)

        # ---------------- DATA ----------------
        self.portfolio = self.load_portfolio()
        self.watchlist = {}
        self.search_results = []

        # ---------------- UI ----------------
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.terminal = QTextBrowser()
        self.terminal.setStyleSheet("background:black;color:white;font-family:Consolas; font-size:14px;")
        self.terminal.setOpenLinks(False)
        self.terminal.anchorClicked.connect(self.handle_click)
        layout.addWidget(self.terminal)

        self.terminal.installEventFilter(self)

        self.input_buffer = ""
        self.prompt = "> "
        self.log("NOSTRIX v36 READY | type /help\n" + self.prompt)

        # Watchlist update
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_watchlist)
        self.timer.start(5000)

    # ---------------- LOG ----------------
    def log(self,msg,append_prompt=True):
        self.terminal.append(msg)
        if append_prompt: self.terminal.append(self.prompt)

    # ---------------- EVENT FILTER FOR INLINE INPUT ----------------
    def eventFilter(self, obj, event):
        if obj == self.terminal and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Backspace:
                if len(self.input_buffer) > 0:
                    self.input_buffer = self.input_buffer[:-1]
                    self.update_terminal_input()
                return True
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                self.execute(self.input_buffer)
                self.input_buffer = ""
                self.update_terminal_input()
                return True
            elif key < 0x10000:
                self.input_buffer += event.text()
                self.update_terminal_input()
                return True
        return super().eventFilter(obj, event)

    def update_terminal_input(self):
        cursor = self.terminal.textCursor()
        cursor.movePosition(cursor.End)
        self.terminal.moveCursor(cursor.End)
        lines = self.terminal.toPlainText().splitlines()
        if lines and lines[-1].startswith(self.prompt):
            lines[-1] = self.prompt + self.input_buffer
            self.terminal.setPlainText("\n".join(lines))
        else:
            self.terminal.append(self.prompt + self.input_buffer)
        self.terminal.moveCursor(self.terminal.textCursor().End)

    # ---------------- COMMAND EXECUTION ----------------
    def execute(self,raw):
        raw = raw.strip()
        if not raw: return
        self.log(f"{self.prompt}{raw}",append_prompt=False)
        parts = raw.split(); cmd = parts[0].lower(); args = parts[1:]
        try:
            if cmd=="/help": self.show_help()
            elif cmd=="/search": self.search(" ".join(args))
            elif cmd=="/buy": self.buy(args[0],int(args[1]))
            elif cmd=="/portfolio": self.show_portfolio()
            elif cmd=="/track": self.track(args[0])
            elif cmd=="/tech": self.technicals(args[0])
            elif cmd=="/ask": self.ask_ai(" ".join(args))
            elif cmd=="/clear": self.terminal.clear(); self.log(self.prompt,append_prompt=False)
            elif cmd=="/watchlist": self.show_watchlist()
            else: self.log("Unknown command")
        except Exception as e: self.log(f"ERROR: {e}")

    # ---------------- HELP ----------------
    def show_help(self):
        self.log("""
<b>AVAILABLE COMMANDS</b>

🔍 SEARCH
/search [query] → Semantic NNR search

💰 PORTFOLIO
/buy [ticker] [qty] → Buy stock
/portfolio → View holdings & signals
/track [ticker] → Add to watchlist with prediction
/watchlist → View tracked tickers

📊 MARKET
/tech [ticker] → Technical indicators (MA, RSI, MACD)

🤖 AI
/ask [query] → Local AI-style scrape & summarize

🛠 SYSTEM
/help → Show this help
/clear → Clear terminal
""")

    # ---------------- STORAGE ----------------
    def save_portfolio(self):
        with open("portfolio.json","w") as f: json.dump(self.portfolio,f)
    def load_portfolio(self):
        try: f=open("portfolio.json","r"); data=json.load(f); f.close(); return data
        except: return {}

    # ---------------- STOCK ENGINE ----------------
    def predict_signal(self,ticker):
        t=yf.Ticker(ticker); hist=t.history(period="6mo"); close=hist["Close"]
        if len(close)<5: return 0,"HOLD"
        m20=close.iloc[-1]/close.iloc[-20]-1 if len(close)>20 else 0
        m50=close.iloc[-1]/close.iloc[-50]-1 if len(close)>50 else 0
        score=sum([m20>0.05,m50>0.08])
        signal="HOLD"; signal="BUY" if score>=2 else ("SELL" if score==0 else "HOLD")
        future=close.iloc[-1]*(1+m20)
        return future,signal
    def buy(self,ticker,qty):
        price=yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
        if ticker not in self.portfolio: self.portfolio[ticker]={"qty":0,"avg":0}
        p=self.portfolio[ticker]; new_qty=p["qty"]+qty; p["avg"]=((p["avg"]*p["qty"])+price*qty)/new_qty; p["qty"]=new_qty
        self.save_portfolio(); self.log(f"Bought {qty} {ticker} @ {price:.2f}")
    def show_portfolio(self):
        self.log("<b>PORTFOLIO</b>")
        for t,p in self.portfolio.items():
            pred,sig=self.predict_signal(t)
            bar="█"*int((pred/p['avg'])*10)
            self.log(f"{t} | Qty:{p['qty']} | Avg:{p['avg']:.2f} | Signal:{sig} | Pred:{pred:.2f} {bar}")

    def track(self,ticker):
        pred,sig=self.predict_signal(ticker)
        self.watchlist[ticker.upper()]={"pred":pred,"sig":sig}
        self.log(f"Tracking {ticker.upper()} | Signal:{sig} | Pred:{pred:.2f}")

    def show_watchlist(self):
        self.log("<b>WATCHLIST</b>")
        for t,d in self.watchlist.items():
            bar="█"*int((d['pred']/self.portfolio.get(t,{'avg':1})['avg'])*10)
            self.log(f"{t} | Current Pred:{d['pred']:.2f} | Signal:{d['sig']} {bar}")

    def technicals(self,ticker):
        t=yf.Ticker(ticker); hist=t.history(period="6mo"); close=hist["Close"]
        ma20=close.rolling(20).mean().iloc[-1]; ma50=close.rolling(50).mean().iloc[-1]
        self.log(f"{ticker.upper()} TECH | Close:{close.iloc[-1]:.2f} | 20MA:{ma20:.2f} | 50MA:{ma50:.2f}")

    # ---------------- WATCHLIST UPDATE ----------------
    def update_watchlist(self):
        for t in self.watchlist:
            price=yf.Ticker(t).history(period="1d")["Close"].iloc[-1]
            self.watchlist[t]["price"]=price

    # ---------------- LOCAL AI-SIMULATION ----------------
    def smart_summary(self,text):
        sentences=[s.strip() for s in text.split(".") if len(s.strip())>40]
        scored=[(s,sum(1 for w in s.split() if len(w)>6)) for s in sentences]
        scored.sort(key=lambda x:x[1],reverse=True)
        return ". ".join([s[0] for s in scored[:5]])
    def ask_ai(self,query):
        self.log(f"AI Query: {query}\nThinking...")
        try:
            r=stealth_requests.get("https://html.duckduckgo.com/html/",params={"q":query})
            soup=BeautifulSoup(r.text,"html.parser")
            results=soup.select(".result")[:3]
            content=""
            for res in results:
                a=res.select_one("a.result__a")
                if not a: continue
                url=a.get("href")
                try:
                    page=stealth_requests.get(url,timeout=5)
                    psoup=BeautifulSoup(page.text,"html.parser")
                    paragraphs=psoup.find_all("p")
                    for p in paragraphs:
                        txt=p.get_text().strip()
                        if len(txt)>80: content+=txt+" "
                except: continue
            if not content: self.log("No data found."); return
            summary=self.smart_summary(content)
            self.log(f"AI Answer:\n{summary[:1500]}")
        except Exception as e: self.log(f"AI ERROR: {e}")

    # ---------------- CLICK HANDLER ----------------
    def handle_click(self,url):
        self.log(f"Clicked link: {url.toString()}")

# ---------------- RUN ----------------
if __name__=="__main__":
    app=QApplication(sys.argv)
    win=NostrixTerminal()
    win.show()
    sys.exit(app.exec())