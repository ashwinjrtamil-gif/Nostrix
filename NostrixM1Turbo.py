import os, re, torch
from bs4 import BeautifulSoup
from curl_cffi import requests as stealth_requests
from transformers import AutoTokenizer, AutoModelForCausalLM, LogitsProcessorList, NoRepeatNGramLogitsProcessor

class NostrixM1_Precisor:
    def __init__(self, query):
        self.query = query
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        
        # MODEL CORE: High-Precision Loading
        self.tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # FP16 Precision for M4 Neural Engine acceleration
        self.model = AutoModelForCausalLM.from_pretrained(
            "distilgpt2", 
            torch_dtype=torch.float16 if self.device.type == "mps" else torch.float32,
            low_cpu_mem_usage=True
        ).to(self.device)
        
        self.vault = []

    def precision_mine(self):
        """ Algorithmic Extraction: Only keeps high-entropy technical data """
        print(f"[!] INFILTRATING: {self.query.upper()}")
        url = f"https://html.duckduckgo.com/html/?q={self.query.replace(' ', '+')}+technical+data"
        
        try:
            res = stealth_requests.get(url, impersonate="chrome120", timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            links = [a['href'].split('uddg=')[1].split('&')[0].replace('%3A', ':').replace('%2F', '/') 
                     for a in soup.select('a.result__a') if 'uddg=' in a['href']][:4]

            for link in links:
                r = stealth_requests.get(link, impersonate="chrome120", timeout=5)
                # DataChukz Logic: Extract clean text only
                text = BeautifulSoup(r.text, "html.parser").get_text(separator=" ")
                # Find paragraphs with numbers and technical units
                matches = re.findall(r'[^.!?]*(\d+|mach|thrust|lb|kg|kn)[^.!?]*[.!?]', text, re.I)
                self.vault.extend(list(set(matches))) # Deduplicate immediately
        except Exception as e: print(f"[!] MINE ERROR: {e}")

    def generate_non_repetitive(self, user_input):
        """ 
        The 'Precisor' Logic: 
        Uses Logit Warping to kill repetitions before they are even predicted.
        """
        context = " ".join(self.vault[:5]) # Take top 5 technical nodes
        prompt = f"TECHNICAL_DATA: {context}\n\nQUERY: {user_input}\nPRECISION_ANALYSIS:"
        
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=700).to(self.device)
        
        # NON-REPETITIVE FEATURE SUITE:
        # 1. repetition_penalty: Punishes already used tokens.
        # 2. no_repeat_ngram_size: Hard-blocks any 3-word sequence from repeating.
        # 3. top_p: Nucleus sampling to keep the 'Model Intelligence' focused on high-probability facts.
        
        with torch.no_grad():
            output_tokens = self.model.generate(
                **inputs,
                max_new_tokens=120,
                do_sample=True,
                temperature=0.4,       # Low temp for high precision
                top_p=0.92,            # Nucleus sampling
                repetition_penalty=2.5, # Aggressive penalty for repeated ideas
                no_repeat_ngram_size=3, # Hard stop on phrase loops
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        raw_response = self.tokenizer.decode(output_tokens[0], skip_special_tokens=True)
        return raw_response.split("PRECISION_ANALYSIS:")[-1].strip()

# --- BOOT ---
if __name__ == "__main__":
    m1 = NostrixM1_Precisor("F-22 Raptor F119 Engine")
    m1.precision_mine()
    
    print(f"[*] NOSTRIX-M1 TURBO READY | {len(m1.vault)} NODES CACHED")
    while True:
        u = input("\n[INPUT] >> ")
        if u.lower() == 'exit': break
        print(f"\n[INTELLIGENCE]: {m1.generate_non_repetitive(u)}")
