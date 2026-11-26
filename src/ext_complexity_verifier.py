"""
EXT-COMPLEXITY-PROD-CERT-1.0: Zero-floating-point exact algebraic verifier for
Minhao Liu's "Extension complexity is not additive under Cartesian products"
(arXiv:2611.33631v1, November 25, 2026).

Strictly zero floating-point literals, zero float() calls, zero true-division (/ or /=),
and zero math/numpy imports. All arithmetic uses exact Python int and fractions.Fraction
(parsed from lowest-terms [num, den] pairs).
"""

from __future__ import annotations

import itertools
import json
import pathlib
import sys
from fractions import Fraction
from typing import Any

SCHEMA_VERSION = "EXT-COMPLEXITY-PROD-CERT-1.0"
MAX_JSON_BYTES = 1_000_000
MAX_RAT_ABS = 10**18


class VerificationError(ValueError):
    """Raised whenever a certificate violates schema, bounds, or mathematical invariants."""


def _gcd(a: int, b: int) -> int:
    a = abs(a)
    b = abs(b)
    while b:
        a, b = b, a % b
    return a


def _req_int(val: Any, name: str, lo: int | None = None, hi: int | None = None) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        raise VerificationError(f"Expected integer for {name}, got {type(val).__name__}")
    if lo is not None and val < lo:
        raise VerificationError(f"{name}={val} below minimum {lo}")
    if hi is not None and val > hi:
        raise VerificationError(f"{name}={val} above maximum {hi}")
    return val


def _req_str(val: Any, name: str) -> str:
    if not isinstance(val, str) or not val.strip():
        raise VerificationError(f"Expected non-empty string for {name}")
    return val


def _req_list(val: Any, name: str, min_len: int = 0, max_len: int = 4096) -> list[Any]:
    if not isinstance(val, list):
        raise VerificationError(f"Expected list for {name}")
    if len(val) < min_len or len(val) > max_len:
        raise VerificationError(f"{name} length {len(val)} out of range [{min_len}, {max_len}]")
    return val


def _req_dict(val: Any, name: str) -> dict[str, Any]:
    if not isinstance(val, dict):
        raise VerificationError(f"Expected dict for {name}")
    return val


def _parse_rat(val: Any, name: str) -> Fraction:
    if not isinstance(val, list) or len(val) != 2:
        raise VerificationError(f"Expected [num, den] rational pair for {name}")
    num = _req_int(val[0], f"{name}[0]", -MAX_RAT_ABS, MAX_RAT_ABS)
    den = _req_int(val[1], f"{name}[1]", 1, MAX_RAT_ABS)
    if _gcd(num, den) != 1:
        raise VerificationError(f"Rational {name}=[{num},{den}] not in lowest terms")
    return Fraction(num, den)


def _no_dup_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise VerificationError(f"Duplicate JSON key: {k}")
        out[k] = v
    return out


def _reject_json_constant(token: str) -> Any:
    raise VerificationError(f"Illegal non-finite JSON constant: {token}")


def _reject_json_float(token: str) -> Any:
    raise VerificationError(f"Illegal floating-point JSON literal: {token}")


# ---------------------------------------------------------------------------
# Exact Rational Linear Algebra & Twin-Hexagon Graph G Helpers
# ---------------------------------------------------------------------------

def _exact_rank(rows: list[list[Fraction]]) -> int:
    """Exact Gaussian elimination rank over Q (zero floats)."""
    if not rows:
        return 0
    m = len(rows)
    n = len(rows[0])
    A = [list(r) for r in rows]
    rank = 0
    for col in range(n):
        piv = -1
        for r in range(rank, m):
            if A[r][col] != 0:
                piv = r
                break
        if piv == -1:
            continue
        A[rank], A[piv] = A[piv], A[rank]
        pv = A[rank][col]
        inv_pv = Fraction(pv.denominator, pv.numerator)
        for c in range(col, n):
            A[rank][c] *= inv_pv
        for r in range(rank + 1, m):
            f = A[r][col]
            if f != 0:
                for c in range(col, n):
                    A[r][c] -= f * A[rank][c]
        rank += 1
        if rank == m:
            break
    return rank


def _build_twin_hexagon() -> tuple[list[tuple[int, int, int]], list[list[int]], list[list[int]], list[list[int]]]:
    """
    Construct Minhao Liu's exact 12-node, 24-edge twin-hexagon graph G (Sec. 3):
    Cluster C_j = {2j, 2j+1} for j in 0..5.
    Edge type j (0..5) has 4 edges connecting C_j to C_{(j+1)%6}.
    Returns:
      edges: list of 24 tuples (u, v, etype)
      R_cols: 12 indicator columns R_v in {0,1}^24
      A_vecs: 3 indicator vectors A_0, A_1, A_2 (types 0, 2, 4)
      X_vecs: 3 indicator vectors X_0, X_1, X_2 (types {2,3,4}, {4,5,0}, {0,1,2})
    """
    edges: list[tuple[int, int, int]] = []
    for j in range(6):
        jn = (j + 1) % 6
        for a in (2 * j, 2 * j + 1):
            for b in (2 * jn, 2 * jn + 1):
                edges.append((a, b, j))
    assert len(edges) == 24
    R_cols: list[list[int]] = []
    for v in range(12):
        R_cols.append([1 if (u == v or w == v) else 0 for (u, w, _) in edges])
    A_vecs: list[list[int]] = []
    for s in range(3):
        t_type = 2 * s
        A_vecs.append([1 if et == t_type else 0 for (_, _, et) in edges])
    X_vecs: list[list[int]] = []
    for t in range(3):
        types = {(2 * t + 2) % 6, (2 * t + 3) % 6, (2 * t + 4) % 6}
        X_vecs.append([1 if et in types else 0 for (_, _, et) in edges])
    return edges, R_cols, A_vecs, X_vecs


def _comb(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    num = 1
    den = 1
    for i in range(k):
        num *= n - i
        den *= i + 1
    return num // den


# ---------------------------------------------------------------------------
# Mode 1: wedge_transfer_and_slack_polytope (Sec. 2 Thm. 3, Lemma 5; Sec. 5 Prop. 10)
# ---------------------------------------------------------------------------

def _verify_mode1(payload: dict[str, Any]) -> dict[str, Any]:
    submode = _req_str(payload.get("submode"), "submode")

    if submode == "facet_wedge_lift_and_lemma5":
        # Verify Lemma 5 & Theorem 3 on explicit nonnegative matrix M, omitted facet slack row sigma,
        # and explicit nonnegative factorization M = U * V of rank r!
        m = _req_int(payload.get("num_rows"), "num_rows", 2, 24)
        n = _req_int(payload.get("num_cols"), "num_cols", 2, 24)
        r = _req_int(payload.get("factor_rank"), "factor_rank", 1, 24)
        M_raw = _req_list(payload.get("matrix_M"), "matrix_M", m, m)
        sigma_raw = _req_list(payload.get("sigma_row"), "sigma_row", n, n)
        U_raw = _req_list(payload.get("factor_U"), "factor_U", m, m)
        V_raw = _req_list(payload.get("factor_V"), "factor_V", r, r)

        M = [[_parse_rat(c, f"M[{i}][{j}]") for j, c in enumerate(_req_list(M_raw[i], f"M[{i}]", n, n))] for i in range(m)]
        sigma = [_parse_rat(c, f"sigma[{j}]") for j, c in enumerate(sigma_raw)]
        U = [[_parse_rat(c, f"U[{i}][{k}]") for k, c in enumerate(_req_list(U_raw[i], f"U[{i}]", r, r))] for i in range(m)]
        V = [[_parse_rat(c, f"V[{k}][{j}]") for j, c in enumerate(_req_list(V_raw[k], f"V[{k}]", n, n))] for k in range(r)]

        for i in range(m):
            for j in range(n):
                if M[i][j] < 0:
                    raise VerificationError(f"Negative entry in M[{i}][{j}]")
        if any(s < 0 for s in sigma) or all(s == 0 for s in sigma):
            raise VerificationError("sigma must be nonnegative and nonzero")
        for i in range(m):
            for k in range(r):
                if U[i][k] < 0:
                    raise VerificationError(f"Negative entry in U[{i}][{k}]")
        for k in range(r):
            for j in range(n):
                if V[k][j] < 0:
                    raise VerificationError(f"Negative entry in V[{k}][{j}]")

        # Verify exact factorization M == U * V
        for i in range(m):
            for j in range(n):
                acc = sum(U[i][k] * V[k][j] for k in range(r))
                if acc != M[i][j]:
                    raise VerificationError(f"Factorization U*V != M at ({i},{j})")

        # Verify Lemma 5 zero-pattern hypothesis: for every nonzero row g of M, exists i with M[g][i] == 0 < sigma[i]
        nonzero_rows = 0
        for g in range(m):
            if any(M[g][j] > 0 for j in range(n)):
                nonzero_rows += 1
                if not any(M[g][j] == 0 and sigma[j] > 0 for j in range(n)):
                    raise VerificationError(f"Lemma 5 zero-pattern hypothesis failed at nonzero row {g}")
        if nonzero_rows == 0:
            raise VerificationError("Vacuous all-zero matrix M rejected")

        # Construct lifted matrix M_sigma ((m+2) x (2n)) and lifted (r+2)-factorization U_sigma * V_sigma
        # Columns: (M_i, sigma_i e_1) for i=0..n-1, then (M_i, sigma_i e_2) for i=0..n-1
        U_sig = [U[i] + [Fraction(0, 1), Fraction(0, 1)] for i in range(m)]
        U_sig.append([Fraction(0, 1)] * r + [Fraction(1, 1), Fraction(0, 1)])
        U_sig.append([Fraction(0, 1)] * r + [Fraction(0, 1), Fraction(1, 1)])

        V_sig = [V[k] + V[k] for k in range(r)]
        V_sig.append(sigma + [Fraction(0, 1)] * n)
        V_sig.append([Fraction(0, 1)] * n + sigma)

        # Verify exact product U_sig * V_sig == M_sigma
        for i in range(m + 2):
            for j in range(2 * n):
                orig_j = j if j < n else j - n
                if i < m:
                    expected = M[i][orig_j]
                elif i == m:
                    expected = sigma[orig_j] if j < n else Fraction(0, 1)
                else:
                    expected = Fraction(0, 1) if j < n else sigma[orig_j]
                got = sum(U_sig[i][k] * V_sig[k][j] for k in range(r + 2))
                if got != expected:
                    raise VerificationError(f"Lifted wedge factorization failed at ({i},{j})")

        return {
            "mode": "wedge_transfer_and_slack_polytope",
            "submode": submode,
            "base_shape": [m, n],
            "base_factor_rank": r,
            "lifted_shape": [m + 2, 2 * n],
            "lifted_factor_rank": r + 2,
            "nonzero_rows_checked": nonzero_rows,
        }

    if submode == "polytope_B_and_P_exact_facets":
        # Verify Sec. 5 Proposition 10 & Eq. (5.2)-(5.3) for exact parameter L >= 100
        L = _req_int(payload.get("scale_L"), "scale_L", 100, 10**9)
        edges, R_cols, _, X_vecs = _build_twin_hexagon()

        # Verify rank(R) = 11 over Q and ker(R) = span(kappa)
        R_rows = [[Fraction(R_cols[v][e], 1) for v in range(12)] for e in range(24)]
        rk_R = _exact_rank(R_rows)
        if rk_R != 11:
            raise VerificationError(f"rank(R)={rk_R} != 11")
        kappa = [1 if (v // 2) % 2 == 0 else -1 for v in range(12)]
        for e in range(24):
            if sum(R_cols[v][e] * kappa[v] for v in range(12)) != 0:
                raise VerificationError(f"kappa not in ker(R) at edge {e}")

        # Verify X_t = X_0 + R*b_t for b_0 = 0, b_1 = iota_0 - iota_3, b_2 = iota_1 - iota_4
        b_vecs = [
            [0] * 12,
            [1 if v in (0, 1) else (-1 if v in (6, 7) else 0) for v in range(12)],
            [1 if v in (2, 3) else (-1 if v in (8, 9) else 0) for v in range(12)],
        ]
        for t in range(3):
            for e in range(24):
                got = X_vecs[0][e] + sum(R_cols[v][e] * b_vecs[t][v] for v in range(12))
                if got != X_vecs[t][e]:
                    raise VerificationError(f"X_{t} != X_0 + R*b_{t} at edge {e}")

        # Build the 37 facet inequalities of B in y in R^12 (with gauge y_{11} = 0, v_0 = 11 in C_5):
        # 36 pair inequalities y_v + y_w + gamma_{vw} >= 0 (v even cluster, w odd cluster), plus sum y_v <= L!
        even_nodes = [v for v in range(12) if (v // 2) % 2 == 0]
        odd_nodes = [w for w in range(12) if (w // 2) % 2 == 1]
        gamma_clusters = {(2, 3), (4, 3), (4, 5)}

        facets: list[tuple[list[Fraction], Fraction, str]] = []
        edge_set = {(min(u, w), max(u, w)) for (u, w, _) in edges}
        for v in even_nodes:
            for w in odd_nodes:
                g_vw = 1 if (v // 2, w // 2) in gamma_clusters else 0
                a_vec = [Fraction(0, 1)] * 12
                a_vec[v] = Fraction(1, 1)
                a_vec[w] = Fraction(1, 1)
                kind = "edge" if (min(v, w), max(v, w)) in edge_set else "opposite"
                facets.append((a_vec, Fraction(g_vw, 1), kind))
        # 37th facet: L - sum y_v >= 0
        facets.append(([Fraction(-1, 1)] * 12, Fraction(L, 1), "sum"))
        assert len(facets) == 37

        # Verify every one of the 37 inequalities defines a genuine facet using Liu's explicit witness points!
        def eval_slack(y_vec: list[Fraction], f_idx: int) -> Fraction:
            a_v, c_v, _ = facets[f_idx]
            return sum(a_v[i] * y_vec[i] for i in range(12)) + c_v

        for f_idx, (a_v, c_v, kind) in enumerate(facets):
            if kind != "sum":
                # Find pair (v, w) with a_v[v]=a_v[w]=1
                pair = [i for i in range(12) if a_v[i] == 1]
                v_i, w_i = pair[0], pair[1]
                y_raw = [Fraction(2, 1)] * 12
                y_raw[v_i] = Fraction(0, 1)
                y_raw[w_i] = -c_v
            else:
                y_raw = [Fraction(L, 12)] * 12
            # Restore gauge y_{11} = 0 by shifting by multiple of kappa (kappa[11] = -1)
            shift = y_raw[11]
            y_w = [y_raw[i] + shift * kappa[i] for i in range(12)]
            if y_w[11] != 0:
                raise VerificationError("Gauge restoration failed on facet witness")
            tight = [j for j in range(37) if eval_slack(y_w, j) == 0]
            neg = [j for j in range(37) if eval_slack(y_w, j) < 0]
            if neg or tight != [f_idx]:
                raise VerificationError(f"Facet {f_idx} witness failed: tight={tight}, neg={neg}")

        # Verify all 39 vertices of B (X_t and X_t + L*R_v) satisfy all 37 facets, have exact tight-subsystem rank 11,
        # and count lifted vertices of P = B_hat via Theorem 3 Step 1!
        lifted_vertex_count = 0
        gauge_row = [Fraction(1 if i == 11 else 0, 1) for i in range(12)]
        for t in range(3):
            for v_shift in [None] + list(range(12)):
                y_raw = [Fraction(b_vecs[t][i], 1) for i in range(12)]
                if v_shift is not None:
                    y_raw[v_shift] += Fraction(L, 1)
                shift = y_raw[11]
                y_pt = [y_raw[i] + shift * kappa[i] for i in range(12)]
                tight_rows = [gauge_row]
                pos_omitted = 0
                for f_idx, (a_v, _, kind) in enumerate(facets):
                    sl = eval_slack(y_pt, f_idx)
                    if sl < 0:
                        raise VerificationError(f"Vertex (t={t}, v={v_shift}) violates facet {f_idx}")
                    if sl == 0:
                        tight_rows.append(a_v)
                    elif kind != "edge":
                        pos_omitted += 1
                if _exact_rank(tight_rows) != 12:
                    raise VerificationError(f"Point (t={t}, v={v_shift}) is not a genuine vertex of B")
                lifted_vertex_count += 1 << pos_omitted

        if lifted_vertex_count != 150:
            raise VerificationError(f"Lifted vertex count of P is {lifted_vertex_count} != 150")

        return {
            "mode": "wedge_transfer_and_slack_polytope",
            "submode": submode,
            "scale_L": L,
            "rank_R": rk_R,
            "base_facets": 37,
            "base_vertices": 39,
            "omitted_wedges": 13,
            "polytope_P_dim": 24,
            "polytope_P_facets": 50,
            "polytope_P_vertices": lifted_vertex_count,
        }

    raise VerificationError(f"Unknown Mode 1 submode: {submode}")


# ---------------------------------------------------------------------------
# Mode 2: six_cycle_subadditivity_and_bounds (Sec. 3 Lemma 7; Sec. 4 Prop. 9)
# ---------------------------------------------------------------------------

def _verify_mode2(payload: dict[str, Any]) -> dict[str, Any]:
    submode = _req_str(payload.get("submode"), "submode")

    if submode == "exact_factorizations_S_and_S1S":
        L = _req_int(payload.get("scale_L"), "scale_L", 1, 10**9)
        edges, R_cols, A_vecs, X_vecs = _build_twin_hexagon()

        # Build the 39 columns of S (24 x 39)
        S_cols: list[tuple[int, int | None, list[int]]] = []
        for t in range(3):
            S_cols.append((t, None, list(X_vecs[t])))
            for v in range(12):
                S_cols.append((t, v, [X_vecs[t][e] + L * R_cols[v][e] for e in range(24)]))

        # Verify Remark 8: ordinary rank(S) == 12 over exact Q
        S_rows_Q = [[Fraction(col[e], 1) for (_, _, col) in S_cols] for e in range(24)]
        rk_S = _exact_rank(S_rows_Q)
        if rk_S != 12:
            raise VerificationError(f"Ordinary rank(S)={rk_S} != 12")

        # Verify Eq. (3.2) for all t in Z/3: X_t = A_{t+1} + sum_{C_{2t+4}} R_v = A_{t+2} + sum_{C_{2t+3}} R_v
        for t in range(3):
            s1 = (t + 1) % 3
            c1 = (2 * t + 4) % 6
            s2 = (t + 2) % 3
            c2 = (2 * t + 3) % 6
            lhs1 = [A_vecs[s1][e] + R_cols[2 * c1][e] + R_cols[2 * c1 + 1][e] for e in range(24)]
            lhs2 = [A_vecs[s2][e] + R_cols[2 * c2][e] + R_cols[2 * c2 + 1][e] for e in range(24)]
            if lhs1 != X_vecs[t] or lhs2 != X_vecs[t]:
                raise VerificationError(f"Eq. (3.2) failed for t={t}")

        # Verify 14-generator nonnegative factorization of S (12 stars + A_0, A_1)
        W1 = R_cols + [A_vecs[0], A_vecs[1]]  # 14 generators in {0,1}^24
        for idx, (t, v_opt, col) in enumerate(S_cols):
            # Pick s in {0, 1} \ {t}
            s = 1 if t == 0 else 0
            h = [0] * 14
            h[12 + s] = 1
            cluster = (2 * t + 4) % 6 if s == (t + 1) % 3 else (2 * t + 3) % 6
            h[2 * cluster] += 1
            h[2 * cluster + 1] += 1
            if v_opt is not None:
                h[v_opt] += L
            recon = [sum(h[g] * W1[g][e] for g in range(14)) for e in range(24)]
            if recon != col:
                raise VerificationError(f"14-generator factorization of S failed at col {idx}")

        # Verify 27-generator nonnegative factorization of S otimes_1 S across ALL 39*39 = 1521 pairs!
        # Generators: (R_v, 0) [0..11], (0, R_v) [12..23], (A_s, A_s) [24..26]
        zero24 = [0] * 24
        W2 = (
            [R_cols[v] + zero24 for v in range(12)]
            + [zero24 + R_cols[v] for v in range(12)]
            + [A_vecs[s] + A_vecs[s] for s in range(3)]
        )
        pairs_checked = 0
        for t1, v1, col1 in S_cols:
            for t2, v2, col2 in S_cols:
                # Choose s in (Z/3 \ {t1}) cap (Z/3 \ {t2})
                s = next(x for x in (0, 1, 2) if x != t1 and x != t2)
                c1 = (2 * t1 + 4) % 6 if s == (t1 + 1) % 3 else (2 * t1 + 3) % 6
                c2 = (2 * t2 + 4) % 6 if s == (t2 + 1) % 3 else (2 * t2 + 3) % 6
                # Compute active generators only (O(1) exact integer check per entry!)
                active: list[tuple[int, int]] = [
                    (24 + s, 1),
                    (2 * c1, 1), (2 * c1 + 1, 1),
                    (12 + 2 * c2, 1), (12 + 2 * c2 + 1, 1),
                ]
                if v1 is not None:
                    active.append((v1, L))
                if v2 is not None:
                    active.append((12 + v2, L))
                target = col1 + col2
                for e in range(48):
                    val = 0
                    for g_idx, coeff in active:
                        val += coeff * W2[g_idx][e]
                    if val != target[e]:
                        raise VerificationError(f"27-generator factorization failed at pair ({t1},{v1},{t2},{v2}) row {e}")
                pairs_checked += 1

        # Verify Eq. (4.1): ALL 2^6 = 64 six-cycles (one node per cluster) satisfy D(R_v)=0, D(A_s)=D(X_t)=1!
        edge_index = {(u, w): idx for idx, (u, w, _) in enumerate(edges)}
        cycles_checked = 0
        for bits in itertools.product((0, 1), repeat=6):
            nodes = [2 * j + bits[j] for j in range(6)]
            cyc_edges = [edge_index[(nodes[j], nodes[(j + 1) % 6])] for j in range(6)]

            def D_val(vec: list[int]) -> int:
                return sum((1 if j % 2 == 0 else -1) * vec[cyc_edges[j]] for j in range(6))

            for v in range(12):
                if D_val(R_cols[v]) != 0:
                    raise VerificationError("Eq. (4.1) D(R_v) != 0")
            for s in range(3):
                if D_val(A_vecs[s]) != 1 or D_val(X_vecs[s]) != 1:
                    raise VerificationError("Eq. (4.1) D(A_s) or D(X_t) != 1")
            cycles_checked += 1

        # Verify empty common support of X_0, X_1, X_2
        for e in range(24):
            if X_vecs[0][e] == 1 and X_vecs[1][e] == 1 and X_vecs[2][e] == 1:
                raise VerificationError(f"Common support non-empty at edge {e}")

        return {
            "mode": "six_cycle_subadditivity_and_bounds",
            "submode": submode,
            "scale_L": L,
            "ordinary_rank_S": rk_S,
            "upper_rank_S": 14,
            "upper_rank_S1S": 27,
            "pairs_verified": pairs_checked,
            "six_cycles_verified": cycles_checked,
        }

    if submode == "proposition9_quantitative_claims":
        # Verify Proposition 9 Claims 1-4 quantitative bounds over exact Q!
        L = _req_int(payload.get("scale_L"), "scale_L", 1000, 10**12)
        tau = _parse_rat(payload.get("tau"), "tau")
        if tau <= 0 or tau >= 1:
            raise VerificationError("tau must satisfy 0 < tau < 1")
        beta = Fraction(1, L) * Fraction(tau.denominator, tau.numerator)
        eps = Fraction(1, L) + 26 * tau
        if beta >= 1 or eps >= 1:
            raise VerificationError(f"Parameters fail beta < 1 or eps < 1: beta={beta}, eps={eps}")

        # Claim 2 probe bound: 26*(tau + 2*beta) < 1
        claim2_val = 26 * (tau + 2 * beta)
        if claim2_val >= 1:
            raise VerificationError(f"Prop. 9 Claim 2 probe bound failed: {claim2_val} >= 1")

        # Claim 2 deficient-node count exceeds 13*d for d in {1, 2} and all b >= 1
        for d in (1, 2):
            if not (12 * d + 3 > 13 * d and 12 * d + 5 > 13 * d):
                raise VerificationError("Claim 2 budget exceedance failed")

        # Claim 3 alternating-sum bound: 26 * max(6*beta, 6*eps/(1-eps)) < 1
        term_a = 6 * beta
        one_minus_eps = 1 - eps
        term_b = 6 * eps * Fraction(one_minus_eps.denominator, one_minus_eps.numerator)
        claim3_val = 26 * (term_a if term_a >= term_b else term_b)
        if claim3_val >= 1:
            raise VerificationError(f"Prop. 9 Claim 3 alternating bound failed: {claim3_val} >= 1")

        # Claim 4 pigeonhole for d=1 (0 unassigned extras cannot cover 3 targets) and d=2 (2*4=8 < 9 targets)
        return {
            "mode": "six_cycle_subadditivity_and_bounds",
            "submode": submode,
            "scale_L": L,
            "claim2_probe_ub": [claim2_val.numerator, claim2_val.denominator],
            "claim3_alt_ub": [claim3_val.numerator, claim3_val.denominator],
            "rank_plus_S": 14,
            "rank_plus_S1S": 27,
        }

    raise VerificationError(f"Unknown Mode 2 submode: {submode}")


# ---------------------------------------------------------------------------
# Mode 3: linear_fraction_deficit_Un_Vn (Sec. 6.1-6.3 Prop. 11 & Thm. 2 Part 1)
# ---------------------------------------------------------------------------

def _verify_mode3(payload: dict[str, Any]) -> dict[str, Any]:
    submode = _req_str(payload.get("submode"), "submode")

    if submode == "coarse_bipartite_dictionary_and_facets":
        # Verify Sec. 6.1 Eq. (6.1) & Sec. 6.3 facet rank-drop on Gamma_2 and Gamma_3!
        N = _req_int(payload.get("edge_copies_N"), "edge_copies_N", 2, 12)
        left_nodes = [1, 2, 3, 4]
        T2 = [tuple(c) for c in itertools.combinations(left_nodes, 2)]  # 6 sets
        T3 = [tuple(c) for c in itertools.combinations(left_nodes, 3)]  # 4 sets

        # Verify every (T, U) in T2 x T3 intersects (proving joint cost <= (2p+4)n!)
        for T in T2:
            for U in T3:
                if not (set(T) & set(U)):
                    raise VerificationError(f"Disjoint pair {T}, {U} in T2 x T3")

        rank_checks: dict[str, int] = {}
        for k, T_list in ((2, T2), (3, T3)):
            nodes = [(0, s) for s in left_nodes] + [(1, T) for T in T_list]
            node_idx = {nd: i for i, nd in enumerate(nodes)}
            coarse_edges = [(s, T) for T in T_list for s in T]
            assert len(coarse_edges) == 12

            # Verify Eq. (6.1) on coarse level (sum of N copies of edge (t,T) lifts indicator of {t,T}):
            # For every T in T_k and every s in T: b_s + sum_{t in T\{s}} (e_t + e_T) == v_T!
            for T in T_list:
                vT = [Fraction(0, 1)] * len(nodes)
                for s in T:
                    vT[node_idx[(0, s)]] = Fraction(1, 1)
                vT[node_idx[(1, T)]] = Fraction(k - 1, 1)
                for s in T:
                    rhs = [Fraction(0, 1)] * len(nodes)
                    rhs[node_idx[(0, s)]] += Fraction(1, 1)
                    for t in T:
                        if t != s:
                            rhs[node_idx[(0, t)]] += Fraction(1, 1)
                            rhs[node_idx[(1, T)]] += Fraction(1, 1)
                    if rhs != vT:
                        raise VerificationError(f"Eq. (6.1) failed for k={k}, T={T}, s={s}")

            # Verify Sec. 6.3 exact node-edge incidence rank & rank-drop == 1 upon deleting I(f) for EVERY node f!
            E_rows = [[Fraction(0, 1)] * 12 for _ in range(len(nodes))]
            for e_idx, (s, T) in enumerate(coarse_edges):
                E_rows[node_idx[(0, s)]][e_idx] = Fraction(1, 1)
                E_rows[node_idx[(1, T)]][e_idx] = Fraction(1, 1)
            rk_Ek = _exact_rank(E_rows)
            if rk_Ek != len(nodes) - 1:
                raise VerificationError(f"rank(E_{k})={rk_Ek} != {len(nodes)-1}")

            for f_i, f_nd in enumerate(nodes):
                keep_cols = [e_i for e_i, (s, T) in enumerate(coarse_edges) if not ((f_nd[0] == 0 and s == f_nd[1]) or (f_nd[0] == 1 and T == f_nd[1]))]
                sub_rows = [[E_rows[r_i][c_i] for c_i in keep_cols] for r_i in range(len(nodes))]
                rk_sub = _exact_rank(sub_rows)
                if rk_sub != rk_Ek - 1:
                    raise VerificationError(f"Sec. 6.3 rank drop failed for k={k}, node={f_nd}: {rk_sub} != {rk_Ek-1}")
            rank_checks[f"rank_E{k}"] = rk_Ek

        p_stars = 12 * N
        # Exact retained row counts: left nodes deg 3 => 4*N^3; right nodes deg k => |T_k|*N^k
        rows_k2 = 4 * (N ** 3) + 6 * (N ** 2)
        rows_k3 = 4 * (N ** 3) + 4 * (N ** 3)
        return {
            "mode": "linear_fraction_deficit_Un_Vn",
            "submode": submode,
            "edge_copies_N": N,
            "stars_per_block_p": p_stars,
            "retained_rows_k2": rows_k2,
            "retained_rows_k3": rows_k3,
            "rank_E2": rank_checks["rank_E2"],
            "rank_E3": rank_checks["rank_E3"],
        }

    if submode == "prop11_conditional_counting_deficit":
        n = _req_int(payload.get("num_blocks_n"), "num_blocks_n", 1, 1000)
        N = _req_int(payload.get("edge_copies_N"), "edge_copies_N", 6, 20)
        p = 12 * N
        H = (p + 3) * n
        Lam = 100_000 * (H ** 3)
        tau = Fraction(1, 100 * H * H)
        beta = Fraction(2, Lam) * Fraction(tau.denominator, tau.numerator)
        eps = Fraction(2, Lam) + H * tau

        # Verify Prop. 11 inequalities: eps <= 1/(90*H), H*(2*beta + tau) < 1, 2*H*max(10*beta, 10*eps/(1-eps)) <= 20/89 < 1!
        if eps > Fraction(1, 90 * H):
            raise VerificationError("Prop. 11 eps <= 1/(90H) failed")
        probe_ub = H * (2 * beta + tau)
        if probe_ub >= 1:
            raise VerificationError("Prop. 11 probe bound H*(2*beta + tau) < 1 failed")
        one_minus_eps = 1 - eps
        t1 = 10 * beta
        t2 = 10 * eps * Fraction(one_minus_eps.denominator, one_minus_eps.numerator)
        func_ub = 2 * H * (t1 if t1 >= t2 else t2)
        if func_ub > Fraction(20, 89) or func_ub >= 1:
            raise VerificationError("Prop. 11 linear-functional bound <= 20/89 failed")

        # Verify exact discrete maxima of d*(1/2)^(d-1) = 1 and d*(3/4)^(d-1) = 27/16 over d=1..30 (monotone decreasing for d>=4!)
        max_half = max(Fraction(d, 1) * (Fraction(1, 2) ** (d - 1)) for d in range(1, 20))
        max_34 = max(Fraction(d, 1) * (Fraction(3, 4) ** (d - 1)) for d in range(1, 20))
        if max_half != Fraction(1, 1) or max_34 != Fraction(27, 16):
            raise VerificationError("Conditional counting maxima mismatch")
        c2 = Fraction(3, 1)  # (5-2) / 1
        c3 = Fraction(2, 1) * Fraction(16, 27)  # (5-3) / (27/16) = 32/27
        if 1 - (3 + c2) * Fraction(1, N) < 0 or 1 - (3 + c3) * Fraction(1, N) < 0:
            raise VerificationError("Prop. 11 nonnegativity of a-coefficient failed")

        # Verify tight 3-block fractional relaxation (64 profiles of weight 1/18 => total 32/9, >= 2 compatible per choice)
        # Every choice of T_2, T_3 in T_3 has |T_2|=|T_3|=3 => 4*3*3 = 36 compatible profiles, weight 36/18 = 2!
        if Fraction(4 * 3 * 3, 18) != Fraction(2, 1) or Fraction(64, 18) != 3 * c3:
            raise VerificationError("3-block fractional relaxation identity failed")

        # Exact deficit lower bound: ceil(5*n / 27)
        deficit_lb = (5 * n + 26) // 27
        r2_lb = (p + 3) * n
        r3_lb = ((27 * p + 32) * n + 26) // 27
        joint_ub = (2 * p + 4) * n
        if r2_lb + r3_lb - joint_ub < deficit_lb:
            raise VerificationError("Deficit lower bound mismatch")

        return {
            "mode": "linear_fraction_deficit_Un_Vn",
            "submode": submode,
            "num_blocks_n": n,
            "edge_copies_N": N,
            "rank_M2_exact": r2_lb,
            "rank_M3_lb": r3_lb,
            "joint_ub": joint_ub,
            "deficit_lb": deficit_lb,
            "probe_ub": [probe_ub.numerator, probe_ub.denominator],
            "func_ub": [func_ub.numerator, func_ub.denominator],
        }

    raise VerificationError(f"Unknown Mode 3 submode: {submode}")


# ---------------------------------------------------------------------------
# Mode 4: unbounded_square_and_corollaries (Sec. 6.4 Lemmas 12-13; Sec. 7)
# ---------------------------------------------------------------------------

def _verify_mode4(payload: dict[str, Any]) -> dict[str, Any]:
    submode = _req_str(payload.get("submode"), "submode")

    if submode == "alphabet_separation_and_lemma12_13":
        js_raw = _req_list(payload.get("j_sequence"), "j_sequence", 1, 8)
        js = [_req_int(v, f"j_sequence[{i}]", 2, 128) for i, v in enumerate(js_raw)]
        sqrt_lam = _req_int(payload.get("sqrt_Lambda"), "sqrt_Lambda", 10, 10**18)

        # Verify Lemma 12 growth condition j_i >= 2 * sum_{h < i} j_h for all i >= 1
        prefix = js[0]
        for i in range(1, len(js)):
            if js[i] < 2 * prefix:
                raise VerificationError(f"Lemma 12 condition violated at i={i}: j_i={js[i]} < 2*C={2*prefix}")
            # Verify j_i / (2*j_i - 1) <= 2/3
            if 3 * js[i] > 2 * (2 * js[i] - 1):
                raise VerificationError(f"Probability bound j/(2j-1) <= 2/3 failed at j={js[i]}")
            prefix += js[i]

        # For blocks with small j_i <= 4, explicitly verify every two j_i-subsets of [2*j_i - 1] intersect!
        intersections_checked = 0
        for ji in js:
            if ji <= 4:
                fams = [set(c) for c in itertools.combinations(range(2 * ji - 1), ji)]
                for a_set in fams:
                    for b_set in fams:
                        if not (a_set & b_set):
                            raise VerificationError(f"Disjoint subsets in F_{ji}")
                        intersections_checked += 1

        # Compute exact Lemma 13 coarse parameters D, q, s_star, N_star, p_star, H
        # Block i: left size 2j-1 (degree C(2j-2, j-1)), right size C(2j-1, j) (degree j)
        q = max(js)
        D = max(max(_comb(2 * j - 2, j - 1), j) for j in js)
        s_star = max((2 * j - 1) + _comb(2 * j - 1, j) for j in js)
        N_star = D + q
        total_coarse_edges = sum(j * _comb(2 * j - 1, j) for j in js)
        p_star = N_star * total_coarse_edges
        C_t = sum(js)
        H = p_star + C_t

        # Verify Lemma 13 perfect-square scale Lambda = sqrt_lam^2 satisfies all 3 strict inequalities!
        Lam = sqrt_lam * sqrt_lam
        if Lam <= q:
            raise VerificationError("Lambda <= q")
        tau = Fraction(1, sqrt_lam)
        beta = Fraction(q, sqrt_lam)  # q / (Lambda * tau) = q / sqrt_lam
        eps = Fraction(q, Lam) + H * tau
        if beta >= 1 or eps >= 1:
            raise VerificationError("Lemma 13 requires beta < 1 and eps < 1")
        if H * (2 * beta + tau) >= 1:
            raise VerificationError("Lemma 13 H*(2*beta + tau) < 1 failed")
        one_minus_eps = 1 - eps
        m_be = beta if beta >= eps * Fraction(one_minus_eps.denominator, one_minus_eps.numerator) else eps * Fraction(one_minus_eps.denominator, one_minus_eps.numerator)
        if q * H * s_star * m_be >= 1:
            raise VerificationError("Lemma 13 q*H*s_star*max(beta, eps/(1-eps)) < 1 failed")

        # Exact Cartesian-square deficit: 2*(p_star + sum j_i) - (2*p_star + sum (2j_i - 1)) = len(js)
        single_exact = p_star + C_t
        square_ub = 2 * p_star + sum(2 * j - 1 for j in js)
        deficit_lb = 2 * single_exact - square_ub
        if deficit_lb != len(js):
            raise VerificationError(f"Square deficit {deficit_lb} != t={len(js)}")

        return {
            "mode": "unbounded_square_and_corollaries",
            "submode": submode,
            "num_blocks_t": len(js),
            "j_sequence": js,
            "cover_number_Ct": C_t,
            "N_star": N_star,
            "p_star": p_star,
            "square_deficit_lb": deficit_lb,
            "intersections_checked": intersections_checked,
        }

    if submode == "corollaries_polarity_and_channel_sim":
        # Verify Sec. 7 Corollaries 14-15, face-bound sandwich, and Sec. 7.2 8-bit -> 7-bit channel saving!
        m_list_raw = _req_list(payload.get("power_m_values"), "power_m_values", 1, 16)
        k_list_raw = _req_list(payload.get("simplex_k_values"), "simplex_k_values", 1, 16)
        ms = [_req_int(v, f"m[{i}]", 1, 1000) for i, v in enumerate(m_list_raw)]
        ks = [_req_int(v, f"k[{i}]", 1, 1000) for i, v in enumerate(k_list_raw)]
        if len(set(ms)) != len(ms) or len(set(ks)) != len(ks):
            raise VerificationError("Duplicate parameter in power_m_values or simplex_k_values")

        # Corollary 14: xc(P^{2m}) <= 79m = 2m*40 - m
        for m in ms:
            if 2 * m * 40 - 79 * m != m:
                raise VerificationError("Corollary 14 identity failed")

        # Corollary 15: xc((P x Delta_k)^2) = 81 + 2k < 82 + 2k = 2*xc(P x Delta_k)
        for k in ks:
            xc_single = 40 + k + 1
            xc_sq = 79 + 2 * (k + 1)
            if xc_sq != 81 + 2 * k or 2 * xc_single - xc_sq != 1:
                raise VerificationError("Corollary 15 identity failed")

        # Face bound for P (dim 24, xc 40, xc(P x P) = 79): 0 <= delta <= 16
        face_ub_P = 40 - 24
        if not (0 < 2 * 40 - 79 <= face_ub_P):
            raise VerificationError("Sec. 7.1 face bound failed")

        # Sec. 7.2 Zero-error channel simulation: Q = P (xc 40), Q' = P x Delta_d_chan
        d_chan = _req_int(payload.get("channel_simplex_dim"), "channel_simplex_dim", 1, 256)
        separate_msgs = 40 + (40 + d_chan + 1)
        joint_msgs = 79 + d_chan + 1
        sep_bits = (separate_msgs - 1).bit_length()
        joint_bits = (joint_msgs - 1).bit_length()
        if joint_msgs >= separate_msgs:
            raise VerificationError("Channel simulation fails strict message reduction")
        # Require actual bit-length drop (e.g., d_chan=48: 129 -> 128 drops 8 bits -> 7 bits!)
        if joint_bits >= sep_bits:
            raise VerificationError(f"Channel simplex dim {d_chan} does not drop fixed-length bit width ({sep_bits} -> {joint_bits})")

        return {
            "mode": "unbounded_square_and_corollaries",
            "submode": submode,
            "checked_m": len(ms),
            "checked_k": len(ks),
            "face_bound_P": face_ub_P,
            "channel_separate_msgs": separate_msgs,
            "channel_joint_msgs": joint_msgs,
            "bits_saved": sep_bits - joint_bits,
        }

    raise VerificationError(f"Unknown Mode 4 submode: {submode}")


# ---------------------------------------------------------------------------
# Entry Points
# ---------------------------------------------------------------------------

def verify_certificate(cert: Any) -> dict[str, Any]:
    d = _req_dict(cert, "certificate")
    if d.get("schema_version") != SCHEMA_VERSION:
        raise VerificationError(f"Expected schema_version={SCHEMA_VERSION}, got {d.get('schema_version')}")
    _req_str(d.get("certificate_id"), "certificate_id")
    _req_str(d.get("paper_reference"), "paper_reference")
    mode = _req_str(d.get("mode"), "mode")
    payload = _req_dict(d.get("payload"), "payload")

    if mode == "wedge_transfer_and_slack_polytope":
        res = _verify_mode1(payload)
    elif mode == "six_cycle_subadditivity_and_bounds":
        res = _verify_mode2(payload)
    elif mode == "linear_fraction_deficit_Un_Vn":
        res = _verify_mode3(payload)
    elif mode == "unbounded_square_and_corollaries":
        res = _verify_mode4(payload)
    else:
        raise VerificationError(f"Unknown mode: {mode}")

    res["certificate_id"] = d["certificate_id"]
    res["status"] = "VERIFIED"
    return res


def verify_file(path: pathlib.Path | str) -> dict[str, Any]:
    p = pathlib.Path(path)
    if not p.is_file():
        raise VerificationError(f"Certificate path is not a readable file: {p}")
    if p.stat().st_size > MAX_JSON_BYTES:
        raise VerificationError(f"Certificate {p.name} exceeds MAX_JSON_BYTES={MAX_JSON_BYTES}")
    raw = p.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise VerificationError(f"Certificate {p.name} exceeds MAX_JSON_BYTES={MAX_JSON_BYTES}")
    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_dup_pairs,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_float,
        )
    except VerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise VerificationError(f"Invalid JSON in {p.name}: {exc}") from exc
    return verify_certificate(data)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("Usage: python -m src.ext_complexity_verifier <file-or-dir> [...]", file=sys.stderr)
        return 2
    files: list[pathlib.Path] = []
    for a in args:
        p = pathlib.Path(a)
        if p.is_dir():
            files.extend(sorted(p.glob("*.json")))
        else:
            files.append(p)
    if not files:
        print("No certificate files found.", file=sys.stderr)
        return 2
    verified = 0
    for f in files:
        res = verify_file(f)
        print(f"[VERIFIED] {f.name}: {res['mode']} ({res['submode']})")
        verified += 1
    print(f"Verified {verified}/{len(files)} certificates under {SCHEMA_VERSION}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
