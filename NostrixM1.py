import os, re, json, time, torch
from bs4 import BeautifulSoup
from curl_cffi import requests as stealth_requests
from transformers import AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer

class NostrixM1:
    def __init__(self, query):
        self.query = query
        # M4 Specific: Metal Performance Shaders (MPS)
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.base_model = "distilgpt2"
        
        print(f"[*] INITIALIZING NOSTRIX CORE ON {self.device}...")
        
        # FIX 1: Explicitly set pad_token to avoid infinite generation loops
        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(self.base_model).to(self.device)
        self.model.config.pad_token_id = self.model.config.eos_token_id
        
        # Optimizer for Neural Sync
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=5e-5)
        
        # Semantic Indexer (MiniLM is extremely fast on M4)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device=self.device)
        
        self.text_cache = []
        self.vector_cache = None

    def ids_algorithm(self, text):
        """ Information Density Scoring: Measures fact-to-word ratio """
        words = text.split()
        if len(words) < 15: return 0
        nums = len(re.findall(r'\d+', text))
        tech = len(re.findall(r'(mach|lb|kg|kn|mph|ft|m|hp|kw|thrust|v|ghz|radar|stealth|alloy|composite)', text, re.I))
        return (nums + tech) / len(words)

    def mine_ore(self):
        """ Stealth Technical Extraction """
        print(f"[!] INFILTRATING: {self.query.upper()}")
        # Using DDG HTML for low-latency/stealth
        s_url = f"https://html.duckduckgo.com/html/?q={self.query.replace(' ', '+')}+technical+specifications"
        
        try:
            res = stealth_requests.get(s_url, impersonate="chrome120", timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            # Decrypt DDG redirect URLs
            links = []
            for a in soup.select('a.result__a'):
                if 'uddg=' in a['href']:
                    clean_url = a['href'].split('uddg=')[1].split('&')[0].replace('%3A', ':').replace('%2F', '/')
                    links.append(clean_url)
            
            for url in links[:5]:
                print(f"    [MINING] {url[:50]}...")
                r = stealth_requests.get(url, impersonate="chrome120", timeout=7)
                s = BeautifulSoup(r.text, "html.parser")
                for j in s(["script", "style", "nav", "footer"]): j.decompose()
                
                # Apply IDS Algorithm to paragraphs
                for p in s.get_text(separator="\n").split("\n"):
                    p = p.strip()
                    if self.ids_algorithm(p) > 0.12:
                        self.text_cache.append(re.sub(r'\[\d+\]', '', p)) # Clean citations
            
            print(f"[*] SECURED {len(self.text_cache)} TECHNICAL NODES.")
        except Exception as e:
            print(f"[!] MINING FAILED: {e}")

    def neural_sync(self):
        """ Online Weights Realignment """
        if not self.text_cache: return
        print("[*] SYNCING NEURAL WEIGHTS TO LOCAL ORE...")
        self.model.train()
        for chunk in self.text_cache[:15]:
            inputs = self.tokenizer(chunk, return_tensors="pt", truncation=True, max_length=128).to(self.device)
            self.optimizer.zero_grad()
            outputs = self.model(**inputs, labels=inputs["input_ids"])
            outputs.loss.backward()
            self.optimizer.step()

    def build_vector_vault(self):
        """ RAM-Only Vector Indexing """
        if not self.text_cache: return
        print("[*] INDEXING SEMANTIC VAULT...")
        self.vector_cache = self.embedder.encode(self.text_cache, convert_to_tensor=True)

    def query_sovereign(self, user_prompt):
        """ Multi-Factor RAG Generation """
        if self.vector_cache is None: return "No data mined."
        
        # 1. Retrieve most relevant context
        q_vec = self.embedder.encode([user_prompt], convert_to_tensor=True)
        scores = torch.nn.functional.cosine_similarity(q_vec, self.vector_cache)
        context = self.text_cache[torch.argmax(scores).item()]

        # 2. Construct fact-based prompt
        input_text = f"Context: {context[:500]}\n\nUser: {user_prompt}\nNostrix-M1 Technical Response:"
        inputs = self.tokenizer(input_text, return_tensors="pt").to(self.device)
        
        # FIX 2: Added explicit repetition penalties and length limits
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=80,
                repetition_penalty=1.5,
                no_repeat_ngram_size=3,
                temperature=0.2,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id
            )
        
        raw_out = self.tokenizer.decode(out[0], skip_special_tokens=True)
        return raw_out.split("Technical Response:")[-1].strip()

    def purge(self):
        """ Zero-Footprint Memory Clear """
        print("\n[!] PURGING UNIFIED MEMORY...")
        self.text_cache = []
        self.vector_cache = None
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

# --- RUNTIME ---
if __name__ == "__main__":
    target = input("TARGET SYSTEM TO MINE >> ")
    engine = NostrixM1(target)
    engine.mine_ore()
    
    if engine.text_cache:
        engine.neural_sync()
        engine.build_vector_vault()
        
        while True:
            query = input("\n[ASK NOSTRIX] (or 'exit') >> ")
            if query.lower() == 'exit': break
            print(f"\n[INTELLIGENCE]: {engine.query_sovereign(query)}")
        
        engine.purge()
    else:
        print("[!] MINING YIELDED 0 RESULTS. ABORTING.")
