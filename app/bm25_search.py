import sqlite3
import re
import numpy as np
from rank_bm25 import BM25Okapi

class BM25Searcher:
    def __init__(self, db_path):
        self.db_path = db_path
        self.bm25 = None
        self.papers = []
        self.build_index()

    def build_index(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch minimal fields needed for search and display
            cursor.execute("SELECT paper_id, title, year, citation_count, venue, url FROM publications")
            rows = cursor.fetchall()
            
            self.papers = []
            corpus = []
            
            for row in rows:
                if not row['title']:
                    continue
                    
                # Store paper metadata needed by api.py
                self.papers.append({
                    'paper_id': row['paper_id'],
                    'title': row['title'],
                    'year': row['year'],
                    'citations': row['citation_count'],
                    'venue': row['venue'],
                    'url': row['url']
                })
                
                # Tokenize title for BM25
                # Using simple regex tokenization
                tokens = self.tokenize(row['title'])
                corpus.append(tokens)
            
            if corpus:
                self.bm25 = BM25Okapi(corpus)
                print(f"BM25 index built with {len(corpus)} papers.")
            else:
                print("Warning: No papers found to build BM25 index.")
                
            conn.close()
            
        except Exception as e:
            print(f"Error building BM25 index: {e}")
            import traceback
            traceback.print_exc()

    def tokenize(self, text):
        return re.findall(r'\w+', text.lower())

    def search(self, query, top_k=20):
        if not self.bm25:
            return []
            
        tokenized_query = self.tokenize(query)
        # Get scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top k indices efficiently using numpy
        # argsort returns indices that would sort the array
        # We want descending order
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0:
                paper = self.papers[idx].copy()
                paper['score'] = score
                results.append(paper)
                
        return results
