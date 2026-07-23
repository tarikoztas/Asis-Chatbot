"""Kural tabanlı Türkçe niyet eşleştirme motoru.

Kullanıcı mesajını normalize eder, intents.json'daki anahtar kelimelerle
skorlar ve en uygun sayfayı (veya öneri listesini) döndürür.
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

INTENTS_PATH = Path(__file__).parent / "intents.json"

# Doğrudan yanıt için gereken minimum skor
DIRECT_THRESHOLD = 2.0
# En yakın rakibin 2 katı skora ulaşan niyet, eşik altında da olsa doğrudan yanıtlanır
DOMINANCE_RATIO = 2.0
# Eşik altında kalındığında önerilecek maksimum sayfa sayısı
MAX_SUGGESTIONS = 3
# Tek başına "güçlü" sayılan anahtar kelime eşleşmesi (tam veya kök eşleşme)
STRONG_KEYWORD = 0.8
# Öneri listesine girmek için gereken minimum skor (çok zayıf sinyaller elenir)
MIN_SUGGESTION_SCORE = 0.5

# Türkçe büyük harfleri doğru küçültmek için (I -> ı, İ -> i)
_TR_LOWER = str.maketrans("IİÇĞÖŞÜ", "ıiçğöşü")


def normalize(text: str) -> str:
    """Metni Türkçe'ye duyarlı küçük harfe çevirir, noktalama işaretlerini temizler."""
    text = text.translate(_TR_LOWER).lower()
    text = re.sub(r"[^a-zçğıöşü0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _word_score(token: str, keyword: str) -> float:
    """Tek kelimelik anahtar kelime ile tek token arasındaki eşleşme skoru."""
    if token == keyword:
        return 1.0
    # Türkçe ek toleransı: "hakediş" <-> "hakedişini" (kök en az 4 harf)
    if len(keyword) >= 4 and len(token) >= 4:
        if token.startswith(keyword) or keyword.startswith(token):
            return 0.9
        # Yazım hatası toleransı: "hakedis" ~ "hakediş"
        if SequenceMatcher(None, token, keyword).ratio() >= 0.8:
            return 0.8
    return 0.0


def _keyword_score(tokens: list[str], keyword: str) -> float:
    """Bir anahtar kelimenin (tek veya çok kelimeli) mesaj içindeki skoru."""
    words = keyword.split()
    if len(words) == 1:
        return max((_word_score(t, words[0]) for t in tokens), default=0.0)
    # Çok kelimeli kalıp: her kelimenin en iyi eşleşmesinin ortalaması.
    # Kalıbın tamamı eşleşirse küçük bir bonus verilir (daha spesifik kalıp).
    scores = [max((_word_score(t, w) for t in tokens), default=0.0) for w in words]
    partial = sum(scores) / len(scores)
    if all(s > 0 for s in scores):
        return min(partial * 1.2, 1.5)
    # Kalıbın sadece bir kısmı eşleşti: zayıf sinyal
    return partial * 0.5


class IntentMatcher:
    def __init__(self, intents_path: Path = INTENTS_PATH):
        data = json.loads(intents_path.read_text(encoding="utf-8"))
        self.intents = data["intents"]
        # Anahtar kelimeleri bir kez normalize edip sakla
        for intent in self.intents:
            intent["_keywords"] = [normalize(k) for k in intent["keywords"]]

    def _score_all(self, message: str) -> list[tuple[float, float, dict]]:
        """Her niyet için (toplam skor, en güçlü tekil anahtar kelime skoru, niyet)."""
        tokens = normalize(message).split()
        if not tokens:
            return []
        scored = []
        for intent in self.intents:
            keyword_scores = [_keyword_score(tokens, kw) for kw in intent["_keywords"]]
            total = sum(keyword_scores)
            strongest = max(keyword_scores, default=0.0)
            scored.append((total, strongest, intent))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _pages(self) -> list[dict]:
        """Link içeren tüm niyetlerin sayfa bilgileri."""
        return [
            {"link": i["link"], "link_text": i["link_text"]}
            for i in self.intents
            if i["link"]
        ]

    def match(self, message: str) -> dict:
        no_match = {
            "reply": (
                "Üzgünüm, isteğinizi tam anlayamadım. "
                "Aşağıdaki sayfalardan birini seçebilir veya isteğinizi "
                "farklı kelimelerle yazabilirsiniz:"
            ),
            "link": None,
            "link_text": None,
            "suggestions": self._pages(),
        }

        scored = self._score_all(message)
        if not scored or scored[0][0] == 0:
            return no_match

        best_score, best_strong, best = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        dominant = best_score >= second_score * DOMINANCE_RATIO

        # Doğrudan yanıt: yüksek toplam skor, VEYA baskın ve yeterli skor,
        # VEYA baskın ve tek başına güçlü bir anahtar kelime eşleşmesi var
        is_direct = best_score >= DIRECT_THRESHOLD or (
            dominant and (best_score >= 1.0 or best_strong >= STRONG_KEYWORD)
        )
        if is_direct:
            return {
                "reply": best["reply"],
                "link": best["link"],
                "link_text": best["link_text"],
                "suggestions": [],
            }

        # Eşik altı: yeterince güçlü sinyali olan en yakın 3 sayfayı öner
        suggestions = [
            {"link": intent["link"], "link_text": intent["link_text"]}
            for score, _strong, intent in scored
            if score >= MIN_SUGGESTION_SCORE and intent["link"]
        ][:MAX_SUGGESTIONS]
        if not suggestions:
            return no_match
        return {
            "reply": (
                "Tam anlayamadım — şunlardan birini mi arıyorsunuz? "
                "Dilerseniz isteğinizi biraz daha detaylı yazın."
            ),
            "link": None,
            "link_text": None,
            "suggestions": suggestions,
        }
