#!/usr/bin/env python3
"""Derive all extraction deliverables from full-extraction.json (single source of truth)."""
import csv, json, os, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "full-extraction.json")
RAW_DIR = os.path.join(HERE, "raw-extractions")
os.makedirs(RAW_DIR, exist_ok=True)

with open(SRC, encoding="utf-8") as fh:
    papers = json.load(fh)

assert len(papers) == 29, f"expected 29 papers, got {len(papers)}"

# ---- OUTPUT 1: comparison-table.csv (29 rows x 12 columns) ----
cols = ["ID", "Paper (Author_Year)", "Definition (first 100 chars)", "Elements (key)",
        "Stakeholders (brief)", "Decision-Making (Y/N/Brief)", "Temporality (Y/N/What)",
        "Megaproject Coverage (Full/Partial/No)", "Temporal Misalignment (Y/N)",
        "Relevance to Electoral-Project Misalignment", "Key Gaps"]

def author_year(p):
    first = p["authors"].split(",")[0].split()[-1]
    multi = "," in p["authors"] or "&" in p["authors"]
    return f"{first}{' et al.' if multi else ''}_{p['year']}"

with open(os.path.join(HERE, "comparison-table.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(cols)
    for p in papers:
        w.writerow([
            p["id"], author_year(p), p["definition"][:100],
            "; ".join(p["elements"][:2]), p["stakeholders"][:90].rsplit(" ", 1)[0] + "...",
            p["decision_making"].split(" - ")[0].split(" (")[0],
            f'{p["temporality_flag"]} - {p["temporality_detail"][:60]}',
            p["megaproject_coverage"], p["misalignment_flag"], p["relevance"],
            p["gaps"][:120],
        ])

# Papers that discuss an electoral / partisan / political-turnover cycle in THEIR OWN analysis
# (hand-coded from the source texts, not inferred from gap annotations):
#  3 Sanderson (promoters out of office), 8 Menga (power changing hands), 9 Biesenthal et al.
#  (political life cycle of a national government), 11 Livert (electoral budget cycles),
#  24 Afieroho (different parties / next election), 25 Brunet & Choiniere (changes of government
#  parties), 27 Gil & Beckman (Sunak cancellation / regime turnover), 29 Delcayre & Bourdin (NIMEY).
ELECTORAL_CYCLE_IDS = {3, 8, 9, 11, 24, 25, 27, 29}

# ---- OUTPUT 3: thematic-matrix.json (pivot-friendly) ----
matrix = []
for p in papers:
    matrix.append({
        "id": p["id"], "paper": author_year(p), "year": p["year"],
        "cluster": None,  # filled below
        "definition_explicit": p["definition_explicit"],
        "temporality": p["temporality_flag"],
        "megaproject": p["megaproject_coverage"],
        "misalignment": p["misalignment_flag"],
        "relevance": p["relevance"],
        "elements": p["elements"],
        "discusses_electoral_cycle": p["id"] in ELECTORAL_CYCLE_IDS,
    })

clusters = {
    "A_foundations": [2, 5, 6, 7, 14, 16, 26],
    "B_megaprojects_complexity": [1, 3, 9, 12, 13, 15, 19, 20, 21],
    "C_temporality_interorg_network": [10, 17, 18, 22, 23, 28],
    "D_political_electoral_multilevel": [4, 8, 11, 24, 25, 27, 29],
}
id_to_cluster = {i: c for c, ids in clusters.items() for i in ids}
for m in matrix:
    m["cluster"] = id_to_cluster[m["id"]]

with open(os.path.join(HERE, "thematic-matrix.json"), "w", encoding="utf-8") as fh:
    json.dump({"clusters": clusters, "papers": matrix}, fh, indent=2, ensure_ascii=False)

# ---- OUTPUT 4: one JSON per paper ----
for p in papers:
    p_out = dict(p)
    p_out["cluster"] = id_to_cluster[p["id"]]
    fn = os.path.join(RAW_DIR, f"paper-{p['id']:02d}.json")
    with open(fn, "w", encoding="utf-8") as fh:
        json.dump(p_out, fh, indent=2, ensure_ascii=False)

# ---- OUTPUT 5: summary-statistics.md ----
def count(flag_key, predicate):
    return sum(1 for p in papers if predicate(p[flag_key]))

temp_yes = count("temporality_flag", lambda v: v == "Yes")
temp_brief = count("temporality_flag", lambda v: v == "Brief")
temp_no = count("temporality_flag", lambda v: v == "No")
mis_yes = count("misalignment_flag", lambda v: v == "Yes")
mega_full = count("megaproject_coverage", lambda v: v == "Full")
mega_partial = count("megaproject_coverage", lambda v: v == "Partial")
mega_no = count("megaproject_coverage", lambda v: v == "No")
rel = {r: count("relevance", lambda v, r=r: v == r) for r in ["High", "Medium", "Low", "None"]}
def_explicit = sum(1 for p in papers if p["definition_explicit"])
electoral = sum(1 for m in matrix if m["discusses_electoral_cycle"])
years = [p["year"] for p in papers]

lines = [
    "# Summary Statistics - 29-Paper Governance Extraction", "",
    f"- **Corpus size:** {len(papers)} unique papers ({min(years)}-{max(years)}); one duplicate (Ika et al. 2025) de-counted.",
    f"- **Temporality discussed:** {temp_yes}/29 substantively (Yes); {temp_brief}/29 briefly/partially; {temp_no}/29 not (Joslin & Muller 2016; Sainati et al. 2020).",
    f"- **Temporal-misalignment discussed:** {mis_yes}/29.",
    f"- **Explicit electoral/partisan/political-turnover cycle discussed in the paper's own analysis:** {electoral}/29 (IDs {sorted(ELECTORAL_CYCLE_IDS)}).",
    f"- **Megaproject coverage:** Full {mega_full}/29; Partial {mega_partial}/29; No {mega_no}/29 (Full+Partial = {mega_full+mega_partial}/29).",
    f"- **Explicit governance definition given:** {def_explicit}/29 (remainder substitute an alternative object - institutional logics, narrative/time, ideology, coupling, project design, governance trap).",
    f"- **Relevance to electoral-project temporal misalignment:** High {rel['High']}; Medium {rel['Medium']}; Low {rel['Low']}; None {rel['None']}.",
    "",
    "## Consensus on definition",
    "**No full consensus.** A stable structural core recurs (structure / process / roles / accountability - Turner 2009; Muller 2016; APM 2019; PMI 2021), but Ahola et al. (2014, p. 1324) state outright there is 'a lack of a shared and universally accepted view.' The field has drifted from control to adaptation (Bakhshi et al. 2025), and several papers decline a governance definition entirely.",
    "",
    "## High-relevance papers (electoral-project temporal misalignment)",
]
for p in papers:
    if p["relevance"] == "High":
        lines.append(f"- **{author_year(p)}** ({id_to_cluster[p['id']]}): {p['misalignment_detail'][:150]}")

lines += ["", "## Papers by cluster"]
for c, ids in clusters.items():
    names = ", ".join(author_year(next(p for p in papers if p["id"] == i)) for i in ids)
    lines.append(f"- **{c}** ({len(ids)}): {names}")

with open(os.path.join(HERE, "summary-statistics.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print("Built:")
print("  comparison-table.csv       (29 rows x 12 cols)")
print("  thematic-matrix.json")
print(f"  raw-extractions/*.json     ({len(papers)} files)")
print("  summary-statistics.md")
print(f"\nStats: temporality Yes={temp_yes} Brief={temp_brief} No={temp_no} | "
      f"misalignment={mis_yes} | electoral={electoral} | "
      f"megaproject Full={mega_full} Partial={mega_partial} No={mega_no} | "
      f"relevance High={rel['High']} Med={rel['Medium']} Low={rel['Low']}")
