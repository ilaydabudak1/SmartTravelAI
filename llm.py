# llm.py — Heterojen model yönlendirici
#
# "Zor vakaya profesör bakar, rutin işi asistan yapar."
#   profil     → Claude Opus   (derin akıl yürütme, serbest metni yorumlama)
#   plan       → Claude Sonnet (düzenli JSON çıktı: yer listesi)
#   elestirmen → Claude Sonnet (planı denetleyen ikinci ajan)
#   maliyet    → Gemini 2.5 Flash (sayısal, kalem bazlı tahmin)
#   rota       → dil modeli yok
#
# Anahtar yoksa zincir: Claude → Gemini → None (ajan kural tabanlı yedeğe döner).
# SMARTTRAVEL_OFFLINE=1 tüm dış çağrıları kapatır (testler bunu kullanır).

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field

try:
    import anthropic as _anthropic
except Exception:                      # paket kurulu değilse sistem yine çalışır
    _anthropic = None

try:
    from google import genai as _genai
except Exception:
    _genai = None


ROL_MODELLERI = {
    "profil":     {"saglayici": "anthropic", "model": "claude-opus-5-5",   "effort": "high"},
    "plan":       {"saglayici": "anthropic", "model": "claude-sonnet-5-5", "effort": "medium"},
    "elestirmen": {"saglayici": "anthropic", "model": "claude-sonnet-5-5", "effort": "low"},
    "maliyet":    {"saglayici": "gemini",    "model": "gemini-2.5-flash",  "effort": None},
}
GEMINI_MODEL = "gemini-2.5-flash"


@dataclass
class CagriKaydi:
    rol: str
    model: str
    basarili: bool
    sure_sn: float
    not_: str = ""


@dataclass
class LLMYonlendirici:
    """Her ajan kendi rolüyle çağırır; yönlendirici modeli seçer, yedeğe düşer ve
    hangi modelin gerçekten kullanıldığını kaydeder (arayüzde şeffaflık için)."""
    kayitlar: list = field(default_factory=list)

    # -- erişilebilirlik -------------------------------------------------
    @staticmethod
    def cevrimdisi() -> bool:
        return os.getenv("SMARTTRAVEL_OFFLINE") == "1"

    @staticmethod
    def anthropic_var() -> bool:
        if _anthropic is None or LLMYonlendirici.cevrimdisi():
            return False
        return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
                    or os.getenv("ANTHROPIC_PROFILE"))

    @staticmethod
    def gemini_var() -> bool:
        return (_genai is not None and not LLMYonlendirici.cevrimdisi()
                and bool(os.getenv("GEMINI_API_KEY")))

    def durum(self) -> dict:
        """Hangi rolün hangi modelle çalışacağını gösterir."""
        out = {}
        for rol, cfg in ROL_MODELLERI.items():
            if cfg["saglayici"] == "anthropic" and self.anthropic_var():
                out[rol] = cfg["model"]
            elif self.gemini_var():
                out[rol] = GEMINI_MODEL + (" (yedek)" if cfg["saglayici"] == "anthropic" else "")
            else:
                out[rol] = "kural tabanlı (LLM yok)"
        return out

    # -- çağrı -----------------------------------------------------------
    def metin(self, rol: str, sistem: str, istem: str, max_tokens: int = 4000) -> str | None:
        cfg = ROL_MODELLERI.get(rol, ROL_MODELLERI["plan"])
        denemeler = []
        if cfg["saglayici"] == "anthropic":
            denemeler = [("anthropic", cfg["model"]), ("gemini", GEMINI_MODEL)]
        else:
            denemeler = [("gemini", cfg["model"]), ("anthropic", ROL_MODELLERI["plan"]["model"])]

        for saglayici, model in denemeler:
            if saglayici == "anthropic" and not self.anthropic_var():
                continue
            if saglayici == "gemini" and not self.gemini_var():
                continue
            t0 = time.perf_counter()
            try:
                if saglayici == "anthropic":
                    cevap = self._claude(model, sistem, istem, max_tokens, cfg.get("effort"))
                else:
                    cevap = self._gemini(model, sistem, istem)
                ok = bool(cevap and cevap.strip())
                self.kayitlar.append(CagriKaydi(rol, model, ok, round(time.perf_counter() - t0, 2)))
                if ok:
                    return cevap.strip()
            except Exception as e:  # ağ, kota, yetki — bir sonraki sağlayıcıya geç
                self.kayitlar.append(CagriKaydi(rol, model, False, round(time.perf_counter() - t0, 2),
                                                type(e).__name__))
        return None

    def json(self, rol: str, sistem: str, istem: str, max_tokens: int = 6000):
        """Modelden JSON ister ve ayrıştırır; ayrıştırılamazsa None."""
        cevap = self.metin(rol, sistem + "\nYanıtın YALNIZCA geçerli JSON olsun; açıklama ya da kod bloğu ekleme.",
                           istem, max_tokens)
        return json_ayikla(cevap)

    def kullanilan_model(self, rol: str) -> str:
        for k in reversed(self.kayitlar):
            if k.rol == rol and k.basarili:
                return k.model
        return "kural tabanlı"

    # -- sağlayıcılar ----------------------------------------------------
    @staticmethod
    def _claude(model: str, sistem: str, istem: str, max_tokens: int, effort: str | None) -> str:
        client = _anthropic.Anthropic(timeout=90.0, max_retries=1)
        istek = dict(
            model=model, max_tokens=max_tokens, system=sistem,
            messages=[{"role": "user", "content": istem}],
        )
        if effort:
            istek["output_config"] = {"effort": effort}
        try:
            # Güvenlik sınıflandırıcısı reddederse sunucu tarafında yedek modele geçer.
            yanit = client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **istek)
        except (TypeError, _anthropic.BadRequestError):
            yanit = client.messages.create(**istek)
        if getattr(yanit, "stop_reason", None) == "refusal":
            return ""
        return "".join(b.text for b in yanit.content if getattr(b, "type", "") == "text")

    @staticmethod
    def _gemini(model: str, sistem: str, istem: str) -> str:
        client = _genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        resp = client.models.generate_content(model=model, contents=f"{sistem}\n\n{istem}")
        return resp.text or ""


def json_ayikla(metin: str | None):
    """```json ... ``` sarmalı, baştaki/sondaki açıklamalar vb. olsa bile ilk JSON değerini çıkarır."""
    if not metin:
        return None
    s = metin.strip()
    s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
    s = re.sub(r"\s*```\s*$", "", s)
    try:
        return json.loads(s)
    except Exception:
        pass
    for ac, kapa in (("{", "}"), ("[", "]")):
        i, j = s.find(ac), s.rfind(kapa)
        if i != -1 and j > i:
            try:
                return json.loads(s[i:j + 1])
            except Exception:
                continue
    return None
