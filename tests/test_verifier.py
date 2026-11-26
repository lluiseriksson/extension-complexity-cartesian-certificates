"""
Comprehensive unit, adversarial forgery, security, and zero-float AST audit tests
for EXT-COMPLEXITY-PROD-CERT-1.0 (src/ext_complexity_verifier.py).
"""

from __future__ import annotations

import ast
import copy
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ext_complexity_verifier import MAX_JSON_BYTES, SCHEMA_VERSION, VerificationError, main, verify_certificate, verify_file

CERTS_DIR = ROOT / "certificates"
VERIFIER_PATH = ROOT / "src" / "ext_complexity_verifier.py"

CANONICAL_FILES = sorted(p.name for p in CERTS_DIR.glob("C*.json"))


def _load(name: str) -> dict:
    return json.loads((CERTS_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Canonical 16-Certificate Verification + CLI
# ---------------------------------------------------------------------------

def test_canonical_count_is_16() -> None:
    assert len(CANONICAL_FILES) == 16


@pytest.mark.parametrize("fname", CANONICAL_FILES)
def test_canonical_certificate_verifies(fname: str) -> None:
    res = verify_file(CERTS_DIR / fname)
    assert res["status"] == "VERIFIED"
    assert res["certificate_id"] == fname.removesuffix(".json")


def test_cli_directory_mode_exits_zero() -> None:
    assert main([str(CERTS_DIR)]) == 0


def test_cli_no_args_returns_two() -> None:
    assert main([]) == 2


def test_cli_empty_dir_returns_two(tmp_path: pathlib.Path) -> None:
    assert main([str(tmp_path)]) == 2


# ---------------------------------------------------------------------------
# 2. Zero-Float AST & Import Audit on Verifier Source
# ---------------------------------------------------------------------------

def test_verifier_has_zero_floats_no_truediv_no_math_numpy() -> None:
    src = VERIFIER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    forbidden_mods = {"math", "cmath", "numpy", "scipy", "decimal"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            pytest.fail(f"Float literal found in verifier: {node.value}")
        if isinstance(node, ast.Div):
            pytest.fail("True division operator (/) found in verifier")
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div):
            pytest.fail("In-place true division (/=) found in verifier")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float":
            pytest.fail("float() call found in verifier")
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden_mods
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden_mods


# ---------------------------------------------------------------------------
# 3. Schema, Security, Duplicate-Key, Float-Literal & Bounds Hardening
# ---------------------------------------------------------------------------

def test_reject_wrong_schema() -> None:
    c = _load("C01_wedge_pentagon_lemma5.json")
    c["schema_version"] = "WRONG-1.0"
    with pytest.raises(VerificationError, match="schema_version"):
        verify_certificate(c)


def test_reject_unknown_mode_and_submodes() -> None:
    c = _load("C01_wedge_pentagon_lemma5.json")
    c["mode"] = "bogus"
    with pytest.raises(VerificationError, match="Unknown mode"):
        verify_certificate(c)

    for fname in (
        "C01_wedge_pentagon_lemma5.json",
        "C05_twin_hexagon_S_S1S_L1e6.json",
        "C09_dictionary_Gamma2_Gamma3_N6.json",
        "C13_square_alphabet_t2_j2_4.json",
    ):
        c2 = _load(fname)
        c2["payload"]["submode"] = "bogus_sub"
        with pytest.raises(VerificationError, match="Unknown Mode"):
            verify_certificate(c2)


def test_reject_float_nan_dup_key_oversize_dir_deep(tmp_path: pathlib.Path) -> None:
    p1 = tmp_path / "f.json"
    p1.write_text('{"schema_version":"EXT-COMPLEXITY-PROD-CERT-1.0","x":1.25}', encoding="utf-8")
    with pytest.raises(VerificationError, match="floating-point"):
        verify_file(p1)

    p2 = tmp_path / "n.json"
    p2.write_text('{"schema_version":"EXT-COMPLEXITY-PROD-CERT-1.0","x":Infinity}', encoding="utf-8")
    with pytest.raises(VerificationError, match="non-finite"):
        verify_file(p2)

    p3 = tmp_path / "d.json"
    p3.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(VerificationError, match="Duplicate JSON key"):
        verify_file(p3)

    p4 = tmp_path / "big.json"
    p4.write_bytes(b" " * (MAX_JSON_BYTES + 8))
    with pytest.raises(VerificationError, match="MAX_JSON_BYTES"):
        verify_file(p4)

    with pytest.raises(VerificationError, match="not a readable file"):
        verify_file(tmp_path)

    p5 = tmp_path / "deep.json"
    p5.write_text("[" * 5000 + "]" * 5000, encoding="utf-8")
    with pytest.raises(VerificationError, match="Invalid JSON"):
        verify_file(p5)


def test_reject_unreduced_rational_and_bool() -> None:
    c = _load("C07_prop9_exact_L1e6_tau1_5000.json")
    c["payload"]["tau"] = [2, 10000]
    with pytest.raises(VerificationError, match="lowest terms"):
        verify_certificate(c)

    c2 = _load("C03_polytope_P_canonical_L1e6.json")
    c2["payload"]["scale_L"] = True
    with pytest.raises(VerificationError, match="Expected integer"):
        verify_certificate(c2)


# ---------------------------------------------------------------------------
# 4. Mode 1 Adversarial Forgeries (Lemma 5 Wedge Lift & Polytope B/P)
# ---------------------------------------------------------------------------

def test_mode1a_rejects_factorization_mismatch() -> None:
    c = _load("C01_wedge_pentagon_lemma5.json")
    c["payload"]["factor_V"][0][1] = [9, 1]
    with pytest.raises(VerificationError, match="U\\*V != M"):
        verify_certificate(c)


def test_mode1a_rejects_negative_factor_entry() -> None:
    c = _load("C02_wedge_prism_lemma5.json")
    c["payload"]["factor_U"][0][0] = [-2, 1]
    with pytest.raises(VerificationError, match="Negative entry in U"):
        verify_certificate(c)


def test_mode1a_rejects_lemma5_zero_pattern_violation() -> None:
    # Make row 0 strictly positive on every column where sigma > 0 -> violates Lemma 5!
    c = _load("C01_wedge_pentagon_lemma5.json")
    c["payload"]["matrix_M"][0][0] = [1, 1]
    c["payload"]["factor_V"][0][0] = [1, 1]
    with pytest.raises(VerificationError, match="Lemma 5 zero-pattern"):
        verify_certificate(c)


def test_mode1a_rejects_all_zero_sigma() -> None:
    c = _load("C01_wedge_pentagon_lemma5.json")
    c["payload"]["sigma_row"] = [[0, 1]] * 5
    with pytest.raises(VerificationError, match="nonnegative and nonzero"):
        verify_certificate(c)


def test_mode1b_exact_polytope_P_counts() -> None:
    res = verify_file(CERTS_DIR / "C03_polytope_P_canonical_L1e6.json")
    assert res["rank_R"] == 11
    assert res["base_facets"] == 37
    assert res["base_vertices"] == 39
    assert res["polytope_P_dim"] == 24
    assert res["polytope_P_facets"] == 50
    assert res["polytope_P_vertices"] == 150


def test_mode1b_rejects_too_small_L() -> None:
    c = _load("C03_polytope_P_canonical_L1e6.json")
    c["payload"]["scale_L"] = 10
    with pytest.raises(VerificationError, match="below minimum"):
        verify_certificate(c)


# ---------------------------------------------------------------------------
# 5. Mode 2 Adversarial Forgeries (Twin-Hexagon Factorizations & Prop. 9)
# ---------------------------------------------------------------------------

def test_mode2a_exact_S_and_S1S_verification() -> None:
    res = verify_file(CERTS_DIR / "C05_twin_hexagon_S_S1S_L1e6.json")
    assert res["ordinary_rank_S"] == 12
    assert res["upper_rank_S"] == 14
    assert res["upper_rank_S1S"] == 27
    assert res["pairs_verified"] == 1521
    assert res["six_cycles_verified"] == 64


def test_mode2b_exact_prop9_liu_fractions() -> None:
    res = verify_file(CERTS_DIR / "C07_prop9_exact_L1e6_tau1_5000.json")
    assert res["claim2_probe_ub"] == [663, 2500]
    assert res["claim3_alt_ub"] == [62412, 76523]


def test_mode2b_rejects_claim2_probe_failure() -> None:
    # Make L too small for tau = 1/5000 so beta = 1/(L*tau) makes 26*(tau + 2*beta) >= 1!
    c = _load("C07_prop9_exact_L1e6_tau1_5000.json")
    c["payload"]["scale_L"] = 100_000  # beta = 5000/100000 = 1/20 => 26*(1/5000 + 1/10) > 2.6 >= 1!
    with pytest.raises(VerificationError, match="Claim 2 probe bound"):
        verify_certificate(c)


def test_mode2b_rejects_claim3_alternating_failure() -> None:
    # Large tau = 1/100 with huge L=10^9: beta tiny, 26*(tau+2beta) = 26/100 < 1,
    # BUT eps = 26/100 => 26 * 6*eps/(1-eps) >> 1!
    c = _load("C07_prop9_exact_L1e6_tau1_5000.json")
    c["payload"]["scale_L"] = 1_000_000_000
    c["payload"]["tau"] = [1, 100]
    with pytest.raises(VerificationError, match="Claim 3 alternating bound"):
        verify_certificate(c)


# ---------------------------------------------------------------------------
# 6. Mode 3 Adversarial Forgeries (Linear-Fraction Deficit U_n, V_n)
# ---------------------------------------------------------------------------

def test_mode3a_exact_gamma_ranks_and_rows() -> None:
    res = verify_file(CERTS_DIR / "C09_dictionary_Gamma2_Gamma3_N6.json")
    assert res["stars_per_block_p"] == 72
    assert res["retained_rows_k2"] == 1080
    assert res["retained_rows_k3"] == 1728
    assert res["rank_E2"] == 9
    assert res["rank_E3"] == 7


def test_mode3b_exact_n6_and_n27_deficits() -> None:
    r11 = verify_file(CERTS_DIR / "C11_prop11_n6_first_saving2.json")
    assert r11["rank_M2_exact"] == 450
    assert r11["rank_M3_lb"] == 440
    assert r11["joint_ub"] == 888
    assert r11["deficit_lb"] == 2

    r12 = verify_file(CERTS_DIR / "C12_prop11_n27_exact_saving5.json")
    assert r12["deficit_lb"] == 5


def test_mode3b_rejects_small_N_below_6() -> None:
    c = _load("C11_prop11_n6_first_saving2.json")
    c["payload"]["edge_copies_N"] = 5
    with pytest.raises(VerificationError, match="below minimum 6"):
        verify_certificate(c)


# ---------------------------------------------------------------------------
# 7. Mode 4 Adversarial Forgeries (Unbounded Squares & Sec. 7 Corollaries)
# ---------------------------------------------------------------------------

def test_mode4a_rejects_slow_alphabet_growth() -> None:
    c = _load("C13_square_alphabet_t2_j2_4.json")
    c["payload"]["j_sequence"] = [2, 3]  # 3 < 2*2 = 4 violates Lemma 12!
    with pytest.raises(VerificationError, match="Lemma 12 condition violated"):
        verify_certificate(c)


def test_mode4a_rejects_insufficient_sqrt_Lambda() -> None:
    c = _load("C13_square_alphabet_t2_j2_4.json")
    c["payload"]["sqrt_Lambda"] = 5000  # Too small for q*H*s_star*max(...) < 1!
    with pytest.raises(VerificationError, match="Lemma 13"):
        verify_certificate(c)


def test_mode4b_exact_channel_bit_saving() -> None:
    r15 = verify_file(CERTS_DIR / "C15_corollaries_and_channel_d48.json")
    assert r15["channel_separate_msgs"] == 129
    assert r15["channel_joint_msgs"] == 128
    assert r15["bits_saved"] == 1


def test_mode4b_rejects_channel_dim_without_bit_drop() -> None:
    c = _load("C15_corollaries_and_channel_d48.json")
    c["payload"]["channel_simplex_dim"] = 10  # 91 -> 90 stays at 7 bits!
    with pytest.raises(VerificationError, match="bit width"):
        verify_certificate(c)


def test_mode4b_rejects_duplicate_m_or_k() -> None:
    c = _load("C15_corollaries_and_channel_d48.json")
    c["payload"]["power_m_values"] = [1, 1, 2]
    with pytest.raises(VerificationError, match="Duplicate parameter"):
        verify_certificate(c)
