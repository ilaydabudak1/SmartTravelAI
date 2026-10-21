from collections import Counter

from agents import MBTIAgent


def test_yirmi_soru_iki_secenek_dengeli():
    sorular = MBTIAgent.SORULAR
    assert len(sorular) == 20
    assert all(len(s) == 5 and s[1] and s[2] for s in sorular)          # soru, A, B, kutup A, kutup B
    assert Counter((a, b) for *_, a, b in sorular) == {("E", "I"): 5, ("S", "N"): 5, ("T", "F"): 5, ("J", "P"): 5}


def test_puanlama():
    m = MBTIAgent()
    assert m._determine_mbti(["A"] * 20) == "ESTJ"
    assert m._determine_mbti(["B"] * 20) == "INFP"
    assert m._determine_mbti(["A) metin"] * 4 + ["B) metin"] * 16) == "INFP"       # her boyutta 1 A, 4 B
    assert m._determine_mbti({f"q{i}": "B" for i in range(1, 21)}) == "INFP"


def test_analiz_cevrimdisi_rapor_uretir():
    r = MBTIAgent().analyze(["A", "B"] * 10)
    assert r["mbti_type"] == "ENTP"            # A,B dönüşümlü → E, N, T, P
    assert r["archetype"] and r["description"]
