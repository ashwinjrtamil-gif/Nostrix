# nostrix_stock_engine.py
import sys, os, sqlite3, math, time
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QTabWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QTextCursor
import yfinance as yf
from curl_cffi import requests as stealth_requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

# ---------------- CONFIG ----------------
DB_FILE = "portfolio.db"
MODEL = SentenceTransformer('all-MiniLM-L6-v2')

# ---------------- DATABASE ----------------
def ensure_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""CREATE TABLE portfolio (ticker TEXT PRIMARY KEY, qty INTEGER, avg REAL)""")
        conn.commit(); conn.close()

def log_to_db(ticker, qty, avg):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO portfolio VALUES (?, ?, ?)", (ticker, qty, avg))
    conn.commit(); conn.close()

def load_portfolio():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT ticker, qty, avg FROM portfolio")
    data = {t:{"qty":q,"avg":a} for t,q,a in c.fetchall()}
    conn.close()
    return data

# ---------------- TERMINAL ----------------
class NostrixTerminal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOSTRIX v44 Ultimate Stock Engine")
        self.resize(1400, 900)

        ensure_db()
        self.portfolio = load_portfolio()
        self.watchlist = {}
        self.nnre_results = []
        self.text_cache = []
        self.tokens_allocated = {}
        self.buffer = ""
        self.history = []
        self.history_pos = -1
        self.prompt = "nostrix> "

        # UI
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(False)
        self.terminal.setStyleSheet("background:black;color:white;font-family:Courier;font-size:14px;")
        self.tabs.addTab(self.terminal, "Terminal")

        self.web_view = QWebEngineView()
        self.tabs.addTab(self.web_view, "Browser")

        self.terminal.installEventFilter(self)
        self.log("NOSTRIX v44 Ultimate Ready | type /help\n"+self.prompt)

    # ---------------- LOG ----------------
    def log(self,msg,prompt=True):
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)
        self.terminal.insertPlainText(msg+"\n")
        if prompt: self.terminal.insertPlainText(self.prompt)
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)

    # ---------------- EVENT FILTER ----------------
    def eventFilter(self,obj,event):
        if obj==self.terminal and event.type()==QEvent.Type.KeyPress:
            key=event.key()
            modifiers=event.modifiers()
            if (modifiers & Qt.KeyboardModifier.ControlModifier) and key in [Qt.Key.Key_C, Qt.Key.Key_V]:
                return False
            if key==Qt.Key.Key_Backspace:
                self.buffer=self.buffer[:-1]; self.update_line(); return True
            elif key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                self.history.append(self.buffer); self.history_pos=len(self.history)
                self.execute(self.buffer); self.buffer=""; self.update_line(); return True
            elif key==Qt.Key.Key_Up:
                if self.history and self.history_pos>0: self.history_pos-=1; self.buffer=self.history[self.history_pos]; self.update_line()
                return True
            elif key==Qt.Key.Key_Down:
                if self.history and self.history_pos<len(self.history)-1: self.history_pos+=1; self.buffer=self.history[self.history_pos]; self.update_line()
                else: self.buffer=""; self.update_line()
                return True
            elif key < 0x10000:
                self.buffer+=event.text(); self.update_line(); return True
        return super().eventFilter(obj,event)

    def update_line(self):
        lines=self.terminal.toPlainText().splitlines()
        if lines and lines[-1].startswith(self.prompt):
            lines[-1]=self.prompt+self.buffer; self.terminal.setPlainText("\n".join(lines))
        else: self.terminal.append(self.prompt+self.buffer)
        self.terminal.moveCursor(QTextCursor.MoveOperation.End)

    # ---------------- COMMAND EXECUTION ----------------
    def execute(self,cmd):
        cmd=cmd.strip()
        if not cmd: return
        self.log(self.prompt+cmd,False)
        parts=cmd.split()
        base=parts[0].lower()
        args=parts[1:]
        try:
            if base=="/help": self.help()
            elif base=="/search": self.nnre_search(" ".join(args))
            elif base=="/mine": self.mine(" ".join(args))
            elif base=="/show": self.show_chunks()
            elif base=="/buy": self.buy(args[0],int(args[1]))
            elif base=="/portfolio": self.show_portfolio()
            elif base=="/track": self.track(args[0])
            elif base=="/watchlist": self.show_watchlist()
            elif base=="/chart": self.show_chart(args[0])
            elif base=="/calc": self.calc(" ".join(args))
            elif base=="/convert": self.unit_convert(" ".join(args))
            elif base=="/open": self.open_page(" ".join(args))
            elif base=="/clear": self.terminal.clear(); self.log(self.prompt,False)
            else: self.log("Unknown command")
        except Exception as e:
            self.log(f"ERROR: {e}")

    # ---------------- HELP ----------------
    def help(self):
        self.log("""
/help → show commands
/search [query] → NNRE ranking news
/mine [query] → scrape pages + chunks
/show → display mined chunks
/buy [ticker] [qty] → buy stock
/portfolio → show portfolio
/track [ticker] → track ticker
/watchlist → show watchlist
/chart [ticker] → show price chart
/calc [expression] → calculator
/convert [value from_currency to_currency] → unit/currency converter
/open [url|index] → open webpage inside terminal
/clear → clear terminal
""")

    # ---------------- NNRE SEARCH ----------------
    def nnre_search(self,query):
        self.log(f"NNRE Search: {query}")
        try:
            r = stealth_requests.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=10)
            soup = BeautifulSoup(r.text,"html.parser")
            results = soup.select(".result")[:10]
            scored=[]
            query_emb = MODEL.encode(query)
            for res in results:
                a=res.select_one("a.result__a")
                if not a: continue
                title=a.get_text().strip()
                href=a.get("href")
                url = href.split('uddg=')[1].split('&')[0].replace('%3A', ':').replace('%2F','/') if 'uddg=' in href else href
                score = float(util.cos_sim(query_emb, MODEL.encode(title))[0][0])
                scored.append({"title":title,"url":url,"score":score})
            scored.sort(key=lambda x: x["score"],reverse=True)
            self.nnre_results=scored
            for i,r in enumerate(scored,1):
                bar="█"*int(r["score"]*10)
                self.log(f"[{i}] {r['title']}\n{bar} {r['score']:.2f}\n{r['url']}",False)
        except Exception as e:
            self.log(f"[!] Search failed: {e}")

    # ---------------- MINING ----------------
    def mine(self,query):
        self.log(f"[*] MINING: {query}")
        s_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ','+')}"
        try:
            res = stealth_requests.get(s_url, impersonate="chrome120", timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            links = [a['href'].split('uddg=')[1].split('&')[0].replace('%3A', ':').replace('%2F','/') 
                     for a in soup.select('a.result__a') if 'uddg=' in a['href']]
            self.text_cache=[]
            for url in links[:5]:
                try:
                    r = stealth_requests.get(url, impersonate="chrome120", timeout=10)
                    s = BeautifulSoup(r.text,"html.parser")
                    for j in s(["script","style","nav","footer"]): j.decompose()
                    text = s.get_text("\n").split("\n")
                    nodes = [p.strip() for p in text if len(p.strip())>50]
                    self.text_cache.extend(nodes[:5])
                    self.log(f"    [MINED] {url[:50]}... ({len(nodes[:5])} nodes)")
                    time.sleep(0.5)
                except Exception as e:
                    self.log(f"    [FAIL] {url[:50]}... {e}")
            self.log(f"[*] MINED {len(self.text_cache)} chunks")
        except Exception as e:
            self.log(f"[!] MINING FAILED: {e}")

    # ---------------- SHOW MINED CHUNKS ----------------
    def show_chunks(self):
        if not self.text_cache:
            self.log("[*] No mined chunks yet")
            return
        self.log("<b>MINED CHUNKS</b>")
        for i, chunk in enumerate(self.text_cache,1):
            snippet = chunk[:200].replace("\n"," ") + ("..." if len(chunk)>200 else "")
            self.log(f"[{i}] {snippet}", False)

    # ---------------- STOCK / PORTFOLIO ----------------
    def predict_signal(self,ticker):
        t=yf.Ticker(ticker)
        hist=t.history(period="6mo")["Close"]
        if len(hist)<5: return 0,"HOLD"
        m20=hist.iloc[-1]/hist.iloc[-20]-1 if len(hist)>20 else 0
        m50=hist.iloc[-1]/hist.iloc[-50]-1 if len(hist)>50 else 0
        score=sum([m20>0.05,m50>0.08])
        signal="HOLD"; signal="BUY" if score>=2 else ("SELL" if score==0 else "HOLD")
        future=hist.iloc[-1]*(1+m20)
        return future,signal

    def buy(self,ticker,qty):
        price=yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
        if ticker not in self.portfolio: self.portfolio[ticker]={"qty":0,"avg":0}
        p=self.portfolio[ticker]; new_qty=p["qty"]+qty; p["avg"]=((p["avg"]*p["qty"])+price*qty)/new_qty; p["qty"]=new_qty
        log_to_db(ticker,p["qty"],p["avg"])
        self.log(f"Bought {qty} {ticker} @ {price:.2f}")

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
            self.log(f"{t} | Pred:{d['pred']:.2f} | Signal:{d['sig']} {bar}")

    # ---------------- CHART ----------------
    def show_chart(self,ticker):
        t=yf.Ticker(ticker)
        hist=t.history(period="6mo")["Close"]
        plt.figure(figsize=(8,4))
        plt.plot(hist.index,hist.values)
        plt.title(f"{ticker} Price Chart")
        plt.grid(True)
        buf = BytesIO()
        plt.savefig(buf, format='png'); buf.seek(0)
        img = Image.open(buf)
        img.show()

    # ---------------- CALC ----------------
    def calc(self,expr):
        try: result=eval(expr,{"__builtins__":None, "math":math})
        except: result="ERROR"
        self.log(f"Calc: {expr} = {result}")

    # ---------------- UNIT/CURRENCY CONVERT ----------------
    def unit_convert(self,expr):
        try:
            expr = expr.replace("$","USD").replace("€","EUR").replace(" ","")
            if "to" in expr.lower():
                val, rest = expr.lower().split("to")
                val_num = float(''.join(filter(str.isdigit, val)))
                from_cur = ''.join(filter(str.isalpha,val)).upper()
                to_cur = rest.upper()
                if from_cur=="USD" and to_cur=="EUR": self.log(f"{val_num} USD = {val_num*0.91} EUR")
                elif from_cur=="EUR" and to_cur=="USD": self.log(f"{val_num} EUR = {val_num*1.1} USD")
                else: self.log(f"Unsupported conversion {from_cur} to {to_cur}")
            elif "km" in expr.lower():
                val=float(''.join(filter(str.isdigit, expr))); self.log(f"{val} km = {val*0.621371} miles")
            else:
                self.log("Unsupported conversion")
        except:
            self.log("ERROR")

    # ---------------- OPEN PAGE ----------------
    def open_page(self,url_or_index):
        try:
            idx = int(url_or_index)-1
            if self.nnre_results and 0 <= idx < len(self.nnre_results):
                url = self.nnre_results[idx]["url"]
            else:
                url = url_or_index
        except:
            url = url_or_index
        if not url.startswith("http"): url="https://"+url
        self.web_view.load(url)
        self.tabs.setCurrentWidget(self.web_view)
        self.log(f"[*] Opening {url} in browser tab")


# ---------------- RUN ----------------
if __name__=="__main__":
    app=QApplication(sys.argv)
    win=NostrixTerminal()
    win.show()
    sys.exit(app.exec())
