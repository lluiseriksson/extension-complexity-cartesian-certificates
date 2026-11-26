# Exact Rational and Constructive Lean 4 Certificates for Non-Additivity of Extension Complexity Under Cartesian Products

Independent companion verification artifact (`EXT-COMPLEXITY-PROD-CERT-1.0`) for Minhao Liu's preprint *"Extension complexity is not additive under Cartesian products"* (`arXiv:2611.33631v1`, November 25, 2026), which disproves Conjecture 1.2 of Grande, Padrol, and Sanyal.

## Contents
- `lean/ExtensionComplexityCert.lean`: 18 constructive Lean 4.35.0 theorems (0 `sorry`, 0 custom axioms, 0 `Classical.choice`, 0 Mathlib) formalizing facet-wedge deficit invariance (Theorem 3, Lemma 5), exact polytope $P$ counts (Theorem 1), Proposition 9 probe and alternating-sum margins, Proposition 11 discrete maxima and $5n/27$ linear-fraction deficit, Lemma 12--13 alphabet-separated square deficits, and Section 7 zero-error channel bit savings.
- `src/ext_complexity_verifier.py`: Strictly zero-floating-point Python verifier over exact $\mathbb{Z}$ and $\mathbb{Q}$ checking four verification modes (eight submodes), including all 37 facets and 39 vertices of $B$ (lifting to 50 facets and 150 vertices of $P$), all $39^2 = 1{,}521$ columns of $S \otimes_1 S$ and all $2^6 = 64$ six-cycles, exact node-deletion facet rank drops on $\Gamma_2$ and $\Gamma_3$, and Lemma 12--13 alphabet-separated squares.
- `certificates/C01..C16`: 16 canonical JSON certificates verified deterministically.
- `tests/test_verifier.py`: Comprehensive unit, adversarial forgery, security, and zero-float AST audit suite.
- `paper/main.pdf`: 4-page companion verification manuscript.

## Quick Verification
```bash
cd lean && lake build
cd ..
python -m src.ext_complexity_verifier certificates
pytest -q
```

## Licensing & Attribution
Code, Lean 4 formalization, and JSON certificates: MIT License. Manuscript and figures: CC-BY-4.0. All primary mathematical theorems belong to Minhao Liu (`arXiv:2611.33631v1`).
