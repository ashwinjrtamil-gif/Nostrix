

from curl_cffi import requests as stealth_requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util
from urllib.parse import urlparse
import numpy as np

class NNREngine:
    def __init__(self):
        # Lightweight + fast embedding model
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # Trusted domains boost
        self.trust_sources = [
            "wikipedia.org",
            "reuters.com",
            "bloomberg.com",
            "investopedia.com",
            "sec.gov",
            "nytimes.com"
        ]


    def search(self, query, limit=10):
        url = "https://html.duckduckgo.com/html/"
        res = stealth_requests.get(url, params={"q": query})
        soup = BeautifulSoup(res.text, "html.parser")

        results = []
        for r in soup.select(".result")[:limit]:
            a = r.select_one("a.result__a")
            snippet = r.select_one(".result__snippet")

            if not a:
                continue

            title = a.get_text().strip()
            link = a.get("href")
            desc = snippet.get_text().strip() if snippet else ""

            results.append({
                "title": title,
                "url": link,
                "desc": desc
            })

        return results


    def trust_score(self, url):
        domain = urlparse(url).netloc
        for t in self.trust_sources:
            if t in domain:
                return 1.2  # boost
        return 1.0

   
    def data_density(self, text):
        words = text.split()
        if not words:
            return 0
        unique = len(set(words))
        return unique / len(words)

   
    def rank(self, query, results):
        if not results:
            return []

        query_emb = self.model.encode(query)

        ranked = []
        for r in results:
            text = r["title"] + " " + r["desc"]

            try:
                emb = self.model.encode(text)
                similarity = float(util.cos_sim(query_emb, emb)[0][0])
            except:
                similarity = 0

            trust = self.trust_score(r["url"])
            density = self.data_density(text)

        
            score = (similarity * 0.6) + (trust * 0.25) + (density * 0.15)

            ranked.append({
                "title": r["title"],
                "url": r["url"],
                "desc": r["desc"],
                "score": score,
                "similarity": similarity,
                "trust": trust,
                "density": density
            })

   
        ranked.sort(key=lambda x: x["score"], reverse=True)

        return ranked

   
    def hybrid_rank(self, query, results):
        """
        Keeps DuckDuckGo order but attaches NNRE scores.
        Useful for UI display.
        """
        if not results:
            return []

        query_emb = self.model.encode(query)

        output = []
        for r in results:
            text = r["title"] + " " + r["desc"]

            try:
                emb = self.model.encode(text)
                similarity = float(util.cos_sim(query_emb, emb)[0][0])
            except:
                similarity = 0

            trust = self.trust_score(r["url"])
            density = self.data_density(text)

            score = (similarity * 0.6) + (trust * 0.25) + (density * 0.15)

            output.append({
                **r,
                "score": score
            })

        return output

    
    def query(self, query, limit=10, mode="ranked"):
        """
        mode:
        - 'ranked' → full NNRE rerank
        - 'hybrid' → keep DDG order + show score
        """
        raw = self.search(query, limit)

        if mode == "ranked":
            return self.rank(query, raw)
        else:
            return self.hybrid_rank(query, raw)


if __name__ == "__main__":
    nnre = NNREngine()
    results = nnre.query("Artificial Intelligence", mode="ranked")

    for i, r in enumerate(results, 1):
        bar = "█" * int(r["score"] * 10)
        print(f"[{i}] {r['title']}")
        print(f"{bar} {r['score']:.2f}")
        print(r["url"])
        print()
