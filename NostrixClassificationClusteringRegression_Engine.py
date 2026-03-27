import re
import numpy as np
from bs4 import BeautifulSoup
from curl_cffi import requests as stealth_requests
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVC
import torch
import sys

class NCCREngine:
    def __init__(self, target_query):
        self.query = target_query
        # M4 Optimization: Check for Metal Performance Shaders
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        
        # --- THE TRIPLE THREAT MODELS ---
        self.classifier = SVC(kernel='rbf', probability=True)  
        self.clusterer = KMeans(n_clusters=3, n_init='auto')   
        self.regressor = LinearRegression()                   
        
        # --- DATA VAULT ---
        self.token_matrix = [] 
        self.raw_metadata = [] 

    def smart_mining_search(self):
        """ [SMART MINING]: Appends data-specific parameters to search tables/metrics """
        print(f"\n[*] NCCR SMART MINING INITIATED: {self.query.upper()}")
        enhanced_query = f"{self.query} technical specifications table metrics data"
        url = f"https://html.duckduckgo.com/html/?q={enhanced_query.replace(' ', '+')}"
        
        try:
            res = stealth_requests.get(url, impersonate="chrome120", timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            # Extract and clean redirect URLs
            links = []
            for a in soup.select('a.result__a'):
                if 'uddg=' in a['href']:
                    clean_url = a['href'].split('uddg=')[1].split('&')[0].replace('%3A', ':').replace('%2F', '/')
                    links.append(clean_url)
            return links[:5]
        except Exception as e:
            print(f"[!] SEARCH FAILED: {e}")
            return []

    def perfect_token_creation(self, html_content):
        """ [TOKENIZATION]: Extracts numbers and structures them into Feature Vectors """
        soup = BeautifulSoup(html_content, "html.parser")
        for j in soup(["script", "style", "nav", "footer"]): j.decompose()
        
        # Look for numerical patterns in the text
        lines = soup.get_text(separator="\n").split("\n")
        for line in lines:
            # Regex for integers and floats
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", line)
            # We need at least 2 numbers to form an (X, Y) relationship for Regression/Clustering
            if len(nums) >= 2:
                try:
                    features = [float(n) for n in nums[:2]]
                    self.token_matrix.append(features)
                    self.raw_metadata.append(line.strip()[:100]) # Store snippet
                except ValueError:
                    continue

    def execute_logic_stack(self):
        """ Executes the Tri-Logic Gate on the Token Matrix """
        if len(self.token_matrix) < 5:
            print(f"[!] INSUFFICIENT ORE. ONLY FOUND {len(self.token_matrix)} TOKENS.")
            return None

        X = np.array(self.token_matrix)
        
        # 1. CLUSTERING: Find hidden patterns in the data
        print("[*] EXECUTING K-MEANS CLUSTERING...")
        clusters = self.clusterer.fit_predict(X)
        
        # 2. REGRESSION: Predict Y-values from X-values
        print("[*] EXECUTING LINEAR REGRESSION...")
        self.regressor.fit(X[:, 0].reshape(-1, 1), X[:, 1])
        prediction = self.regressor.predict([[X[-1, 0]]])
        
        # 3. CLASSIFICATION: Use SVM to categorize data points
        print("[*] EXECUTING SVM CLASSIFICATION...")
        self.classifier.fit(X, clusters)

        return {
            "nodes": len(X),
            "clusters": clusters,
            "next_pred": prediction[0],
            "score": self.regressor.score(X[:, 0].reshape(-1, 1), X[:, 1])
        }

    def run(self):
        urls = self.smart_mining_search()
        if not urls:
            print("[!] NO TARGETS FOUND. ABORTING.")
            return

        for u in urls:
            try:
                print(f"    [MINING ORE] {u[:60]}...")
                r = stealth_requests.get(u, impersonate="chrome120", timeout=7)
                self.perfect_token_creation(r.text)
            except:
                continue
        
        results = self.execute_logic_stack()
        if results:
            print("\n" + "█"*50)
            print(" NCCR ENGINE: INTELLIGENCE REPORT")
            print("█"*50)
            print(f"TARGET: {self.query.upper()}")
            print(f"TOTAL TOKENS MINED: {results['nodes']}")
            print(f"REGRESSION SCORE (R²): {results['score']:.4f}")
            print(f"PREDICTED NEXT DATA POINT: {results['next_pred']:.2f}")
            print("█"*50)
            print("[STATUS] PURGING LOCAL RAM CACHE... DONE.")

# --- TERMINAL INTERFACE ---
if __name__ == "__main__":
    print("--- NOSTRIX NCCR LOGIC ENGINE V200.2 ---")
    
    # Get query from terminal input
    terminal_query = input("\nENTER MINING TARGET (e.g. 'Bitcoin price history' or 'F-22 weight') >> ")
    
    if terminal_query.strip():
        ashwin_nccr = NCCREngine(terminal_query)
        ashwin_nccr.run()
    else:
        print("[!] EMPTY QUERY. SYSTEM SHUTDOWN.")
