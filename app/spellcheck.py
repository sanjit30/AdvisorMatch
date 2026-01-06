import sqlite3
import re
from collections import Counter
import os

class DomainSpellChecker:
    def __init__(self, db_path):
        self.db_path = db_path
        self.WORDS = Counter()
        self.build_vocabulary()

    def build_vocabulary(self):
        if not os.path.exists(self.db_path):
            print(f"Warning: Database not found at {self.db_path}. Spell checker will be empty.")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Fetch interests from professors
            try:
                cursor.execute("SELECT interests FROM professors")
                for row in cursor.fetchall():
                    if row[0]:
                        self.process_text(row[0])
            except sqlite3.OperationalError:
                print("Warning: Could not fetch interests from professors table.")

            # Fetch titles from publications
            try:
                cursor.execute("SELECT title FROM publications")
                for row in cursor.fetchall():
                    if row[0]:
                        self.process_text(row[0])
            except sqlite3.OperationalError:
                print("Warning: Could not fetch titles from publications table.")
                    
            conn.close()
            print(f"Spell checker vocabulary size: {len(self.WORDS)}")
            
        except Exception as e:
            print(f"Error building vocabulary: {e}")

    def process_text(self, text):
        words = re.findall(r'\w+', text.lower())
        self.WORDS.update(words)

    def P(self, word): 
        "Probability of `word`."
        N = sum(self.WORDS.values())
        if N == 0: return 0
        return self.WORDS[word] / N

    def correction(self, word): 
        "Most probable spelling correction for word."
        # If the word is known, return it (to avoid over-correcting valid words)
        if word in self.WORDS:
            return word
        
        # If the word is unknown, look for candidates
        candidates = self.candidates(word)
        return max(candidates, key=self.P)

    def candidates(self, word): 
        "Generate possible spelling corrections for word."
        return (self.known([word]) or self.known(self.edits1(word)) or self.known(self.edits2(word)) or [word])

    def known(self, words): 
        "The subset of `words` that appear in the dictionary of WORDS."
        return set(w for w in words if w in self.WORDS)

    def edits1(self, word):
        "All edits that are one edit away from `word`."
        letters    = 'abcdefghijklmnopqrstuvwxyz'
        splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
        deletes    = [L + R[1:]               for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
        replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
        inserts    = [L + c + R               for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def edits2(self, word): 
        "All edits that are two edits away from `word`."
        return (e2 for e1 in self.edits1(word) for e2 in self.edits1(e1))

    def correct_text(self, text):
        "Correct all the words in a text."
        # Use regex to find words, preserving punctuation
        # We split by non-word characters
        tokens = re.split(r'(\W+)', text)
        corrected_tokens = []
        for token in tokens:
            # If it's a word (contains alphanumeric), correct it
            if re.match(r'^\w+$', token):
                # Preserve case? Norvig's usually works on lower.
                # Here we lower for correction but maybe we want to restore case?
                # For search queries, lowercasing is usually fine and expected.
                corrected = self.correction(token.lower())
                corrected_tokens.append(corrected)
            else:
                corrected_tokens.append(token)
        return "".join(corrected_tokens)
