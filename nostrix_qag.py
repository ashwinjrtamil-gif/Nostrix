import json
import spacy
import wikipedia
import re
from difflib import SequenceMatcher

# --- CORE SETUP ---
try:
    nlp = spacy.load("en_core_web_sm")
except:
    import os
    os.system("python3 -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class NostrixQUG:
    def __init__(self):
        self.ram_vault = []
        self.qw_map = {"PERSON": "Who", "ORG": "Which entity", "PRODUCT": "Which system", "DATE": "When"}

    def _optimize_query(self, text):
        """Query Optimization: Fixes 'Space x' -> 'SpaceX' and removes noise."""
        text = text.lower().replace("space x", "spacex")
        doc = nlp(text)
        return [t.lemma_ for t in doc if not t.is_stop and not t.is_punct]

    def mine(self, target):
        print(f"[*] NostrixQUG Mining: {target}...")
        try:
            pages = wikipedia.search(target, results=3)
            for p_title in pages:
                p = wikipedia.page(p_title, auto_suggest=False)
                paras = [para for para in p.content.split('\n\n') if len(para.split()) > 20]
                for context in paras:
                    doc = nlp(context)
                    for sent in doc.sents:
                        if sent.ents:
                            ent = sent.ents[0]
                            qw = self.qw_map.get(ent.label_, "What")
                            q_text = sent.text.replace(ent.text, "____").strip()
                            self.ram_vault.append({
                                "instruction": f"Based on the text, {qw} is {q_text}?",
                                "input": context,
                                "output": ent.text
                            })
                            break
            print(f"[✓] {len(self.ram_vault)} pairs staged in RAM.")
        except Exception as e: print(f"[!] Error: {e}")

    def ask(self, query):
        """Closest Answer Logic: Ranks results by fuzzy similarity to query tokens."""
        keywords = self._optimize_query(query)
        scored_results = []
        for item in self.ram_vault:
            # Score based on keyword presence in context/output
            score = sum(1 for k in keywords if k in item['input'].lower() or k in item['output'].lower())
            if score > 0:
                scored_results.append((score, item))
        
        # Sort by highest match score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return scored_results[:3]

    def export(self):
        with open("nostrix_alpaca_final.json", "w") as f:
            json.dump(self.ram_vault, f, indent=4)
        print(f"[RELEASE] {len(self.ram_vault)} samples saved to nostrix_alpaca_final.json")

# --- EXECUTION ---
if __name__ == "__main__":
    nos = NostrixQUG()
    print("NostrixQUG v1.0 | Commands: mine [topic], ask [query], export, exit")
    while True:
        cmd = input("\n[NostrixQUG] >> ").strip().split(" ", 1)
        if cmd[0] == "exit": break
        elif cmd[0] == "mine": nos.mine(cmd[1])
        elif cmd[0] == "export": nos.export()
        elif cmd[0] == "ask":
            res = nos.ask(cmd[1])
            for s, m in res:
                print(f"\n[Match Score: {s}]\nContext: {m['input'][:150]}...\nQ: {m['instruction']}\nA: {m['output']}")