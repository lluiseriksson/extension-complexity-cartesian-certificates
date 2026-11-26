"""
Generate the 16 canonical EXT-COMPLEXITY-PROD-CERT-1.0 certificates (C01..C16) for
paper76-extension-complexity-cartesian-certificates and verify every single one.
"""

from __future__ import annotations

import json
import pathlib
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ext_complexity_verifier import SCHEMA_VERSION, verify_file

CERTS_DIR = ROOT / "certificates"


def _r(num: int, den: int = 1) -> list[int]:
    f = Fraction(num, den)
    return [f.numerator, f.denominator]


def build_certificates() -> list[tuple[str, dict]]:
    certs: list[tuple[str, dict]] = []

    # ------------------------------------------------------------------
    # Mode 1a: facet_wedge_lift_and_lemma5 (Sec. 2 Theorem 3 & Lemma 5)
    # ------------------------------------------------------------------
    # C01: Pentagon slack submatrix M (4 retained facets x 5 vertices) + 5th omitted facet sigma!
    # Regular-like rational pentagon with vertices (0,0),(2,0),(3,2),(1,3),(0,2):
    # Facets: x>=0, y>=0, 2x-y+0<=4 (4-2x+y>=0), x+2y<=7 (7-x-2y>=0), -x+y<=2 (2+x-y>=0)
    # Slacks at 5 vertices:
    # f0 (x>=0): [0, 2, 3, 1, 0]
    # f1 (y>=0): [0, 0, 2, 3, 2]
    # f2 (4-2x+y>=0): [4, 0, 0, 5, 6]
    # f3 (7-x-2y>=0): [7, 5, 0, 0, 3]
    # sigma = f4 (2+x-y>=0): [2, 4, 3, 0, 0]
    # Check Lemma 5 zero-pattern:
    # row 0 has 0 at v0 where sigma[0]=2>0; row 1 has 0 at v0,v1 (sigma=2,4>0);
    # row 2 has 0 at v1,v2 (sigma=4,3>0); row 3 has 0 at v2 (sigma=3>0)! ALL 4 pass!
    # Rank-4 trivial factorization U = I_4, V = M (or rank-4 conic factorization)
    M01 = [
        [_r(0), _r(2), _r(3), _r(1), _r(0)],
        [_r(0), _r(0), _r(2), _r(3), _r(2)],
        [_r(4), _r(0), _r(0), _r(5), _r(6)],
        [_r(7), _r(5), _r(0), _r(0), _r(3)],
    ]
    sig01 = [_r(2), _r(4), _r(3), _r(0), _r(0)]
    U01 = [[_r(1 if i == j else 0) for j in range(4)] for i in range(4)]
    certs.append((
        "C01_wedge_pentagon_lemma5.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C01_wedge_pentagon_lemma5",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 2 Theorem 3 & Lemma 5 Pentagon Facet Wedge",
            "mode": "wedge_transfer_and_slack_polytope",
            "payload": {
                "submode": "facet_wedge_lift_and_lemma5",
                "num_rows": 4,
                "num_cols": 5,
                "factor_rank": 4,
                "matrix_M": M01,
                "sigma_row": sig01,
                "factor_U": U01,
                "factor_V": M01,
            },
        },
    ))

    # C02: 3D triangular prism retained slack matrix (4 facets x 6 vertices) + omitted base facet sigma
    # Nonnegative factorization of rank 4 (exact rank-4 U*V with non-identity rational U, V)
    # Vertices of prism Triangle x [0,1]: (0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,0,1),(0,1,1)
    # Retained facets: x>=0, y>=0, 1-x-y>=0, z>=0; omitted facet sigma: 1-z>=0 -> [1,1,1,0,0,0]
    # Wait: z>=0 vanishes at v0,v1,v2 where sigma=1>0; x>=0 vanishes at v0 (sigma=1>0);
    # y>=0 vanishes at v0,v1 (sigma=1>0); 1-x-y>=0 vanishes at v1,v2 (sigma=1>0)!
    # Use scaled U = diag(2, 1/2, 3, 1) and V = diag(1/2, 2, 1/3, 1)*M!
    M02 = [
        [_r(0), _r(1), _r(0), _r(0), _r(1), _r(0)],
        [_r(0), _r(0), _r(1), _r(0), _r(0), _r(1)],
        [_r(1), _r(0), _r(0), _r(1), _r(0), _r(0)],
        [_r(0), _r(0), _r(0), _r(1), _r(1), _r(1)],
    ]
    sig02 = [_r(1), _r(1), _r(1), _r(0), _r(0), _r(0)]
    U02 = [
        [_r(2), _r(0), _r(0), _r(0)],
        [_r(0), _r(1, 2), _r(0), _r(0)],
        [_r(0), _r(0), _r(3), _r(0)],
        [_r(0), _r(0), _r(0), _r(1)],
    ]
    V02 = [
        [_r(0), _r(1, 2), _r(0), _r(0), _r(1, 2), _r(0)],
        [_r(0), _r(0), _r(2), _r(0), _r(0), _r(2)],
        [_r(1, 3), _r(0), _r(0), _r(1, 3), _r(0), _r(0)],
        [_r(0), _r(0), _r(0), _r(1), _r(1), _r(1)],
    ]
    certs.append((
        "C02_wedge_prism_lemma5.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C02_wedge_prism_lemma5",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 2 Theorem 3 & Lemma 5 Triangular-Prism Wedge",
            "mode": "wedge_transfer_and_slack_polytope",
            "payload": {
                "submode": "facet_wedge_lift_and_lemma5",
                "num_rows": 4,
                "num_cols": 6,
                "factor_rank": 4,
                "matrix_M": M02,
                "sigma_row": sig02,
                "factor_U": U02,
                "factor_V": V02,
            },
        },
    ))

    # ------------------------------------------------------------------
    # Mode 1b: polytope_B_and_P_exact_facets (Sec. 5 Prop. 10 & Eq. (5.3))
    # ------------------------------------------------------------------
    certs.append((
        "C03_polytope_P_canonical_L1e6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C03_polytope_P_canonical_L1e6",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 5 Prop. 10 & Theorem 1 (L = 10^6)",
            "mode": "wedge_transfer_and_slack_polytope",
            "payload": {
                "submode": "polytope_B_and_P_exact_facets",
                "scale_L": 1_000_000,
            },
        },
    ))

    certs.append((
        "C04_polytope_P_scaled_L1e7.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C04_polytope_P_scaled_L1e7",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 5 Prop. 10 Scale Invariance (L = 10^7)",
            "mode": "wedge_transfer_and_slack_polytope",
            "payload": {
                "submode": "polytope_B_and_P_exact_facets",
                "scale_L": 10_000_000,
            },
        },
    ))

    # ------------------------------------------------------------------
    # Mode 2a: exact_factorizations_S_and_S1S (Sec. 3 Lemma 7 & Remark 8)
    # ------------------------------------------------------------------
    certs.append((
        "C05_twin_hexagon_S_S1S_L1e6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C05_twin_hexagon_S_S1S_L1e6",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 3 Lemma 7 & Eq. (4.1) (L = 10^6)",
            "mode": "six_cycle_subadditivity_and_bounds",
            "payload": {
                "submode": "exact_factorizations_S_and_S1S",
                "scale_L": 1_000_000,
            },
        },
    ))

    certs.append((
        "C06_twin_hexagon_S_S1S_L5e6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C06_twin_hexagon_S_S1S_L5e6",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 3 Lemma 7 & Eq. (4.1) (L = 5*10^6)",
            "mode": "six_cycle_subadditivity_and_bounds",
            "payload": {
                "submode": "exact_factorizations_S_and_S1S",
                "scale_L": 5_000_000,
            },
        },
    ))

    # ------------------------------------------------------------------
    # Mode 2b: proposition9_quantitative_claims (Sec. 4 Prop. 9 Claims 1-4)
    # ------------------------------------------------------------------
    certs.append((
        "C07_prop9_exact_L1e6_tau1_5000.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C07_prop9_exact_L1e6_tau1_5000",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 4 Prop. 9 Canonical Parameters",
            "mode": "six_cycle_subadditivity_and_bounds",
            "payload": {
                "submode": "proposition9_quantitative_claims",
                "scale_L": 1_000_000,
                "tau": _r(1, 5000),
            },
        },
    ))

    certs.append((
        "C08_prop9_tightened_L1e7_tau1_20000.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C08_prop9_tightened_L1e7_tau1_20000",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 4 Prop. 9 Tightened Margin",
            "mode": "six_cycle_subadditivity_and_bounds",
            "payload": {
                "submode": "proposition9_quantitative_claims",
                "scale_L": 10_000_000,
                "tau": _r(1, 20000),
            },
        },
    ))

    # ------------------------------------------------------------------
    # Mode 3a: coarse_bipartite_dictionary_and_facets (Sec. 6.1 & 6.3)
    # ------------------------------------------------------------------
    certs.append((
        "C09_dictionary_Gamma2_Gamma3_N6.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C09_dictionary_Gamma2_Gamma3_N6",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 6.1 & 6.3 Canonical N=6 (p=72 stars)",
            "mode": "linear_fraction_deficit_Un_Vn",
            "payload": {
                "submode": "coarse_bipartite_dictionary_and_facets",
                "edge_copies_N": 6,
            },
        },
    ))

    certs.append((
        "C10_dictionary_Gamma2_Gamma3_N8.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C10_dictionary_Gamma2_Gamma3_N8",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 6.1 & 6.3 Extended N=8 (p=96 stars)",
            "mode": "linear_fraction_deficit_Un_Vn",
            "payload": {
                "submode": "coarse_bipartite_dictionary_and_facets",
                "edge_copies_N": 8,
            },
        },
    ))

    # ------------------------------------------------------------------
    # Mode 3b: prop11_conditional_counting_deficit (Sec. 6.2 Prop. 11)
    # ------------------------------------------------------------------
    certs.append((
        "C11_prop11_n6_first_saving2.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C11_prop11_n6_first_saving2",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 6.2 Prop. 11 Example n=6 (450+440-888=2)",
            "mode": "linear_fraction_deficit_Un_Vn",
            "payload": {
                "submode": "prop11_conditional_counting_deficit",
                "num_blocks_n": 6,
                "edge_copies_N": 6,
            },
        },
    ))

    certs.append((
        "C12_prop11_n27_exact_saving5.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C12_prop11_n27_exact_saving5",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 6.2-6.3 Theorem 2 Exact Multiple n=27 (saving >= 5)",
            "mode": "linear_fraction_deficit_Un_Vn",
            "payload": {
                "submode": "prop11_conditional_counting_deficit",
                "num_blocks_n": 27,
                "edge_copies_N": 6,
            },
        },
    ))

    # ------------------------------------------------------------------
    # Mode 4a: alphabet_separation_and_lemma12_13 (Sec. 6.4 Lemmas 12-13)
    # ------------------------------------------------------------------
    # C13: t=2 blocks, j = [2, 4] (j1=2, j2=2*2=4 => cover=6, deficit=2!)
    # Compute safe sqrt_Lambda:
    # j=[2,4]: q=4, D=max(C(2,1), C(6,3))=20, s_star=max(6, 7+35)=42, N_star=24
    # coarse edges = 2*3 + 4*35 = 146, p_star = 24*146 = 3504, H = 3510
    # Need q*H*s_star*(H/sqrt_lam) < 1 => sqrt_lam > 4 * 3510^2 * 42 ~ 2.07e9 -> pick 10^10!
    certs.append((
        "C13_square_alphabet_t2_j2_4.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C13_square_alphabet_t2_j2_4",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 6.4 Lemmas 12-13 (t=2, j=[2,4], deficit>=2)",
            "mode": "unbounded_square_and_corollaries",
            "payload": {
                "submode": "alphabet_separation_and_lemma12_13",
                "j_sequence": [2, 4],
                "sqrt_Lambda": 10_000_000_000,
            },
        },
    ))

    # C14: t=3 blocks, j = [2, 4, 12] (j1=2, j2=4, j3=2*(2+4)=12 => cover=18, deficit=3!)
    # For j=12: C(22,11)=705432, C(23,12)=1352078, D=705432, s_star=1352101, N_star=705444
    # p_star ~ 705444 * 12 * 1352078 ~ 1.14e13 -> sqrt_Lambda = 10^35? Wait MAX_INT in JSON is fine, check _req_int hi=10**18!
    # Wait: for t=3 with j=[2, 4, 12], H ~ 1.14e13, so H^2 * s_star * q ~ 12 * 1.3e26 * 1.35e6 ~ 2.1e33!
    # Wait: for smaller j=[2, 4] (t=2) and t=1 j=[2] or t=2 j=[2, 5]?
    # Let's check t=2 j=[2, 5]: C(8,4)=70, C(9,5)=126, D=70, s_star=135, N_star=75, coarse=6+630=636, p_star=47700, H=47707!
    # q*H^2*s_star = 5 * 47707^2 * 135 ~ 1.54e12 < 10^13 (well below 10^18)!
    # AND what about t=3 with j=[2, 4, 12]? If we allow sqrt_Lambda up to 10**40 (just a Python int, exact!) OR use j=[2, 5] for C14!
    # Wait: having t=3 (j=[2, 4, 12]) is SO MUCH COOLER because it is LITERALLY Liu's canonical sequence j_1=2, j_2=4, j_3=12 giving deficit >= 3!
    # Let's check: in ext_complexity_verifier.py, _req_int(..., hi=10**18) for sqrt_Lambda can simply be hi=10**40!
    certs.append((
        "C14_square_alphabet_t2_j2_5.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C14_square_alphabet_t2_j2_5",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 6.4 Lemmas 12-13 (t=2, j=[2,5], deficit>=2)",
            "mode": "unbounded_square_and_corollaries",
            "payload": {
                "submode": "alphabet_separation_and_lemma12_13",
                "j_sequence": [2, 5],
                "sqrt_Lambda": 100_000_000_000_000,
            },
        },
    ))

    # ------------------------------------------------------------------
    # Mode 4b: corollaries_polarity_and_channel_sim (Sec. 7.1 & 7.2)
    # ------------------------------------------------------------------
    certs.append((
        "C15_corollaries_and_channel_d48.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C15_corollaries_and_channel_d48",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 7 Corollaries 14-15 & 8->7 Bit Channel Sim (Delta_48)",
            "mode": "unbounded_square_and_corollaries",
            "payload": {
                "submode": "corollaries_polarity_and_channel_sim",
                "power_m_values": [1, 2, 3, 5, 10, 25],
                "simplex_k_values": [1, 2, 4, 8, 16, 48],
                "channel_simplex_dim": 48,
            },
        },
    ))

    certs.append((
        "C16_corollaries_and_channel_d176.json",
        {
            "schema_version": SCHEMA_VERSION,
            "certificate_id": "C16_corollaries_and_channel_d176",
            "paper_reference": "Liu (arXiv:2611.33631v1), Sec. 7 Corollaries 14-15 & 9->8 Bit Channel Sim (Delta_176)",
            "mode": "unbounded_square_and_corollaries",
            "payload": {
                "submode": "corollaries_polarity_and_channel_sim",
                "power_m_values": [4, 8, 16, 32, 64],
                "simplex_k_values": [3, 7, 15, 31, 176],
                "channel_simplex_dim": 176,
            },
        },
    ))

    return certs


def main() -> int:
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    certs = build_certificates()
    for fname, obj in certs:
        out_path = CERTS_DIR / fname
        out_path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
        res = verify_file(out_path)
        print(f"[OK] {fname}: {res}")
    print(f"Generated and verified {len(certs)} certificates in {CERTS_DIR}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
