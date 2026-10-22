from collections import Counter

from agents import MBTIAgent


def test_yirmi_soru_iki_secenek_dengeli():
    sorular = MBTIAgent.SORULAR
    assert len(sorular) == 20
    assert all(len(s) == 5 and s[1] and s[2] for s in sorular)          # soru, A, B, kutup A, kutup B
    boyut = Counter("".join(sorted(a + b)) for *_, a, b in sorular)
    assert boyut == {"EI": 5, "NS": 5, "FT": 5, "JP": 5}
    # Şık dengesi: her boyutta A şıkkı iki kutba 3/2 dağılır
    for kutup in ("EI", "SN", "TF", "JP"):
        a_dagilim = sorted(Counter(a for *_, a, b in sorular if {a, b} == set(kutup)).values())
        assert a_dagilim == [2, 3], kutup


def test_kullanicinin_ornek_maddeleri_testte():
    metinler = " ".join(s[1] + " " + s[2] for s in MBTIAgent.SORULAR)
    assert "gözlemlemeyi ve analiz etmeyi tercih ederim" in metinler
    assert "veri toplar ve analiz ederim" in metinler
    assert "fikir ve kavramlarla ilgilenirim" in metinler


def test_puanlama():
    m = MBTIAgent()
    assert m._determine_mbti(["A"] * 20) == "ESTJ"
    assert m._determine_mbti(["B"] * 20) == "INFP"
    assert m._determine_mbti(["A", "B"] * 10) == "ENTP"
    assert m._determine_mbti({f"q{i}": "B) metin" for i in range(1, 21)}) == "INFP"
    # Her soruda E/S/T/J kutbunu seçen kişi her zaman ESTJ çıkmalı (şık sırası fark etmeksizin)
    estj = ["A" if a in "ESTJ" else "B" for *_, a, b in m.SORULAR]
    assert m._determine_mbti(estj) == "ESTJ"


def test_tip_profili_ve_16_tip():
    assert len(MBTIAgent.TIPLER) == 16
    r = MBTIAgent().tip_profili("infj")
    assert r["mbti_type"] == "INFJ" and r["archetype"] and r["description"]
