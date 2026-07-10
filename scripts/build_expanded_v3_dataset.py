"""
build_expanded_v3_dataset.py
============================
Build a substantially larger AfriKnow evaluation set (v3) using a refined,
high-precision region detector on Global-MMLU.

Design rationale
----------------
v2 (480 full + 86 GM-only) is still modest. Global-MMLU's own region labels are
sparse (only ~4% of items are annotated), so the v2 detector left most
Africa/Europe content unlabelled. This script uses an expanded but carefully
curated keyword list plus the existing region_list annotations to label items
exclusively as Africa or Europe. Cross-region/ambiguous items are excluded.

Key quality controls
--------------------
1. Exclusive labels: an item is Africa **only** if it has an Africa signal and
   no Europe signal; Europe **only** if Europe signal and no Africa signal.
2. region_list annotations are respected when present.
3. "African American" is not treated as an Africa signal (US diaspora).
4. "guinea pig" does not trigger Guinea.
5. No demonym-only Europe labels (e.g., "English" in a machine-learning item
   about BLEU/ROUGE does not become Europe).
6. `high_school_european_history` is hard-labelled Europe.
7. Deduplication against AfriMMLU and within GM is applied.

Outputs in ./phase2_data/:
  - afriknow_source_annotated_full_v3.json
  - afriknow_gm_only_v3.json

Run:
    python build_expanded_v3_dataset.py
"""

import ast
import json
import os
import random
import re
from collections import Counter, defaultdict

import pandas as pd
from datasets import load_dataset

SEED = 42
random.seed(SEED)
os.makedirs("phase2_data", exist_ok=True)

LABS = ["A", "B", "C", "D"]

AFRIMMLU_SUBJECTS_V11 = [
    "high_school_geography",
    "high_school_world_history",
    "global_facts",
    "miscellaneous",
    "high_school_government_and_politics",
]

HARD_EUROPE_SUBJECTS = {"high_school_european_history"}

AFRICA_COUNTRIES = [
    "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi",
    "Cameroon", "Cape Verde", "Central African Republic", "Chad", "Comoros",
    "Democratic Republic of the Congo", "Djibouti", "Egypt", "Equatorial Guinea",
    "Eritrea", "Eswatini", "Ethiopia", "Gabon", "Gambia", "Ghana", "Guinea",
    "Guinea-Bissau", "Ivory Coast", "Kenya", "Lesotho", "Liberia", "Libya",
    "Madagascar", "Malawi", "Mali", "Mauritania", "Mauritius", "Morocco",
    "Mozambique", "Namibia", "Niger", "Nigeria", "Republic of the Congo",
    "Rwanda", "Sao Tome and Principe", "Senegal", "Seychelles", "Sierra Leone",
    "Somalia", "South Africa", "South Sudan", "Sudan", "Tanzania", "Togo",
    "Tunisia", "Uganda", "Zambia", "Zimbabwe",
]

EUROPE_COUNTRIES = [
    "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus",
    "Belgium", "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus",
    "Czech Republic", "Denmark", "Estonia", "Finland", "France", "Georgia",
    "Germany", "Greece", "Hungary", "Iceland", "Ireland", "Italy", "Kosovo",
    "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta", "Moldova",
    "Monaco", "Montenegro", "Netherlands", "North Macedonia", "Norway",
    "Poland", "Portugal", "Romania", "Russia", "San Marino", "Serbia",
    "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland", "Turkey",
    "Ukraine", "United Kingdom", "Vatican City",
]

AFRICA_STRONG = [
    # regions / geography
    "Africa", "African", "Sub-Saharan", "Sahara", "Sahel", "Horn of Africa",
    "Maghreb", "Kalahari", "Nile", "Congo River", "Niger River", "Zambezi",
    "Lake Victoria", "Lake Tanganyika", "Lake Malawi", "Mount Kilimanjaro",
    "Atlas Mountains", "Drakensberg", "Victoria Falls",
    # cities
    "Lagos", "Cairo", "Nairobi", "Johannesburg", "Kinshasa", "Addis Ababa",
    "Dakar", "Accra", "Kampala", "Dar es Salaam", "Abidjan", "Casablanca",
    "Cape Town", "Luanda", "Khartoum", "Ibadan", "Alexandria", "Kano",
    "Douala", "Harare", "Lusaka", "Mogadishu", "Bamako", "Ouagadougou",
    "Antananarivo",
    # peoples / ethnic groups
    "Zulu", "Maasai", "Hutu", "Tutsi", "Berber", "Tuareg", "Bantu",
    "Khoisan", "Xhosa", "Yoruba", "Hausa", "Igbo", "Amhara", "Oromo",
    "Shona", "Nubian",
    # historical figures
    "Nelson Mandela", "Kwame Nkrumah", "Haile Selassie", "Shaka Zulu",
    "Mansa Musa", "Cleopatra", "Desmond Tutu", "Patrice Lumumba",
    "Jomo Kenyatta", "Julius Nyerere", "Thabo Mbeki", "F. W. de Klerk",
    "Muammar Gaddafi", "Gamal Abdel Nasser", "Anwar Sadat", "Hosni Mubarak",
    "Robert Mugabe", "Steve Biko", "Wangari Maathai", "Kofi Annan",
    "Idi Amin", "Mobutu",
    # empires / civilizations
    "Mali Empire", "Songhai Empire", "Great Zimbabwe", "Aksum", "Axum",
    "Ancient Egypt", "Carthage", "Ashanti Empire", "Kingdom of Benin",
    "Kingdom of Kongo", "Nubia", "Kush", "Ptolemaic",
    # events / movements
    "apartheid", "African National Congress", "ANC", "Boer", "Boer War",
    "Great Trek", "Scramble for Africa", "Berlin Conference",
    "Atlantic slave trade", "African slave trade", "Rwandan genocide",
    "Darfur", "African Union", "OAU", "ECOWAS", "SADC", "Trans-Saharan trade",
]

EUROPE_STRONG = [
    # regions / geography
    "Europe", "European", "Balkans", "Scandinavia", "Iberian Peninsula",
    "Alps", "Mediterranean", "Baltic", "Danube", "Rhine", "Seine", "Thames",
    "Volga", "Elbe", "Loire", "Tagus", "Po River",
    # cities
    "Paris", "London", "Berlin", "Rome", "Madrid", "Vienna", "Athens",
    "Moscow", "Amsterdam", "Brussels", "Prague", "Warsaw", "Budapest",
    "Lisbon", "Stockholm", "Copenhagen", "Helsinki", "Oslo", "Dublin",
    "Edinburgh", "Florence", "Venice", "Milan", "Barcelona", "Munich",
    "Hamburg", "Frankfurt", "Geneva", "Zurich", "Lyon", "Marseille",
    "Turin", "Naples", "Seville", "Valencia", "Manchester", "Birmingham",
    # historical figures
    "Napoleon", "Hitler", "Churchill", "Caesar", "Shakespeare",
    "Leonardo da Vinci", "Michelangelo", "Mozart", "Beethoven", "Bach",
    "Van Gogh", "Rembrandt", "Galileo", "Isaac Newton", "Darwin",
    "Marie Curie", "Winston Churchill", "Joseph Stalin", "Mikhail Gorbachev",
    "Charles de Gaulle", "Otto von Bismarck", "Queen Victoria", "Elizabeth I",
    "Henry VIII", "Louis XIV", "Peter the Great", "Catherine the Great",
    "Socrates", "Plato", "Aristotle", "Alexander the Great", "Charlemagne",
    "William the Conqueror", "Isabella I", "Ferdinand", "Magellan",
    "Columbus", "Martin Luther", "John Calvin", "Voltaire", "Rousseau",
    "Kant", "Hegel", "Nietzsche", "Freud", "Marx", "Lenin",
    # empires / events / institutions
    "Roman Empire", "Holy Roman Empire", "British Empire", "French Revolution",
    "Russian Revolution", "Renaissance", "Reformation",
    "Protestant Reformation", "Enlightenment", "Industrial Revolution",
    "Berlin Wall", "Iron Curtain", "NATO", "European Union", "Warsaw Pact",
    "Treaty of Versailles", "Congress of Vienna", "Ottoman Empire",
    "Byzantine Empire", "Crusades", "Hundred Years' War", "Thirty Years' War",
    "Black Death", "Spanish Inquisition", "Feudalism", "Medieval Europe",
    "Viking Age", "Norman Conquest", "Brexit",
]

EUROPE_ALL = EUROPE_COUNTRIES + EUROPE_STRONG


def parse_list_col(val):
    if isinstance(val, list):
        return [str(x) for x in val]
    if isinstance(val, str):
        try:
            r = ast.literal_eval(val)
            if isinstance(r, list):
                return [str(x) for x in r]
        except Exception:
            pass
        for sep in ["|||", "||", "|", ";"]:
            if sep in val:
                return [x.strip() for x in val.split(sep)]
    return [str(val)] if val else []


def parse_choices(raw):
    if isinstance(raw, list):
        ch = [str(x) for x in raw]
    elif isinstance(raw, str):
        try:
            p = ast.literal_eval(raw)
            ch = [str(x) for x in p] if isinstance(p, list) else [raw]
        except Exception:
            ch = [raw]
    else:
        ch = [str(raw)]
    while len(ch) < 4:
        ch.append(ch[-1] if ch else "N/A")
    return ch[:4]


def answer_idx(ans, ch):
    if isinstance(ans, int):
        ai = ans
    elif isinstance(ans, str) and ans in LABS:
        ai = LABS.index(ans)
    else:
        try:
            ai = int(ans)
        except Exception:
            ai = 0
    return min(ai, len(ch) - 1)


def norm_q(q):
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9]", " ", str(q))).strip().lower()


def has_region(row, target):
    return any(isinstance(r, str) and target.lower() in r.lower()
               for r in row["region_list"])


def has_term(text, terms):
    if not isinstance(text, str):
        return False
    return any(re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE)
               for t in terms)


def has_africa_text(text):
    if not isinstance(text, str):
        return False
    # Remove "African American" diaspora references; keep if a country/etc. also appears.
    text_no_aa = re.sub(r"\bAfrican[- ]American(s)?\b", "", text,
                        flags=re.IGNORECASE)
    # "guinea pig" should not trigger the country Guinea.
    if re.search(r"\bguinea pig(s)?\b", text, re.IGNORECASE):
        return has_term(text_no_aa,
                        [t for t in AFRICA_COUNTRIES if t != "Guinea"] +
                        AFRICA_STRONG)
    return has_term(text_no_aa, AFRICA_COUNTRIES) or has_term(text_no_aa, AFRICA_STRONG)


def has_europe_text(text):
    return has_term(text, EUROPE_ALL)


def classify_row(row):
    """Return 'Africa', 'Europe', or '' (exclusive label)."""
    rl_africa = has_region(row, "Africa")
    rl_europe = has_region(row, "Europe")
    text_africa = has_africa_text(row["question"])
    text_europe = has_europe_text(row["question"])
    hard_europe = row["subject"] in HARD_EUROPE_SUBJECTS

    is_africa = rl_africa or text_africa
    is_europe = rl_europe or text_europe or hard_europe

    if is_africa and not is_europe:
        return "Africa"
    if is_europe and not is_africa:
        return "Europe"
    return ""


def make_q(qid, source, region, group, cat, diff, q_text, ch, a_idx,
           cs_label, lang="en"):
    return dict(
        id=qid, source=source, region=region, group=group,
        cat=cat, diff=diff, q=q_text, ch=ch, a=a_idx,
        cs=cs_label, lang=lang
    )


def gmmlu_to_questions(df_sub, region, id_prefix):
    out = []
    for _, row in df_sub.iterrows():
        ch = parse_choices([
            row.get("option_a"), row.get("option_b"),
            row.get("option_c"), row.get("option_d")
        ])
        ai = answer_idx(row.get("answer", "A"), ch)
        qtx = str(row.get("question", "")).strip()
        if not qtx:
            continue
        cs = str(row.get("cultural_sensitivity_label", "-"))
        sid = str(row.get("sample_id", ""))
        qid = f"{id_prefix}-{region[:2].upper()}-{sid.replace('/', '-')}"[:64]
        out.append(make_q(
            qid=qid,
            source="Global-MMLU (ACL 2025)",
            region=region,
            group=f"GM_{region}_{cs}",
            cat=str(row.get("subject", "misc")),
            diff=str(row.get("difficulty", "medium")),
            q_text=qtx,
            ch=ch,
            a_idx=ai,
            cs_label=cs,
        ))
    return out


def load_gmmlu():
    print("Loading CohereLabs/Global-MMLU (en, test)...")
    gmmlu_df = load_dataset("CohereLabs/Global-MMLU", "en", split="test").to_pandas()
    gmmlu_df["region_list"] = gmmlu_df["region"].apply(parse_list_col)
    return gmmlu_df


def classify_gmmlu_items(gmmlu_df):
    gmmlu_df["region_label"] = gmmlu_df.apply(classify_row, axis=1)
    counts = gmmlu_df["region_label"].value_counts()
    print("\nGlobal-MMLU refined region detection:")
    print(f"  Exclusive Africa: {counts.get('Africa', 0)}")
    print(f"  Exclusive Europe: {counts.get('Europe', 0)}")
    print(f"  Ambiguous/none:   {counts.get('', 0)}")
    return gmmlu_df


def load_afrimmlu_v11():
    print("\nLoading masakhane/afrimmlu (eng, test) with v11 subject filter...")
    df_eng = load_dataset("masakhane/afrimmlu", "eng", split="test").to_pandas()
    df_filt = df_eng[df_eng["subject"].isin(AFRIMMLU_SUBJECTS_V11)]
    out = []
    for _, row in df_filt.iterrows():
        ch = parse_choices(row.get("choices", []))
        ai = answer_idx(row.get("answer", "A"), ch)
        qtx = str(row.get("question", "")).strip()
        if not qtx:
            continue
        qid = f"AFRIMMLU-v11-{len(out):05d}"
        out.append(make_q(
            qid=qid,
            source="AfriMMLU/IrokoBench (NAACL 2025)",
            region="Africa",
            group="Africa_CS",
            cat=str(row.get("subject", "misc")),
            diff="medium",
            q_text=qtx,
            ch=ch,
            a_idx=ai,
            cs_label="CS",
        ))
    print(f"  AfriMMLU v11 items: {len(out)}")
    return out


def dedupe_items(items):
    seen = set()
    out = []
    for it in items:
        nq = norm_q(it["q"])
        if nq not in seen:
            seen.add(nq)
            out.append(it)
    return out


def dedupe_gm_against_afrimmlu(gm_items, afri_items):
    afri_qnorm = {norm_q(it["q"]) for it in afri_items}
    kept, removed = [], []
    for it in gm_items:
        if norm_q(it["q"]) in afri_qnorm:
            removed.append(it)
        else:
            kept.append(it)
    return kept, removed


def build_source_annotated_full_v3(gmmlu_df, afri_items):
    gm_af = gmmlu_to_questions(
        gmmlu_df[gmmlu_df["region_label"] == "Africa"], "Africa", "GM"
    )
    gm_eu = gmmlu_to_questions(
        gmmlu_df[gmmlu_df["region_label"] == "Europe"], "Europe", "GM"
    )

    gm_af, removed_af = dedupe_gm_against_afrimmlu(gm_af, afri_items)
    gm_eu, removed_eu = dedupe_gm_against_afrimmlu(gm_eu, afri_items)

    gm_af = dedupe_items(gm_af)
    gm_eu = dedupe_items(gm_eu)

    all_items = afri_items + gm_af + gm_eu
    all_items = dedupe_items(all_items)

    rng = random.Random(SEED)
    rng.shuffle(all_items)

    source_counts = Counter(q["source"] for q in all_items)
    region_counts = Counter(q["region"] for q in all_items)
    cs_counts = Counter((q["region"], q["cs"]) for q in all_items)

    print(f"\nSource-annotated full v3 dataset: {len(all_items)} items")
    print(f"  By source: {dict(source_counts)}")
    print(f"  By region: {dict(region_counts)}")
    print(f"  By region x CS: {dict(cs_counts)}")
    print(f"  Duplicates removed: Africa={len(removed_af)}, Europe={len(removed_eu)}")

    return {
        "name": "AfriKnow source-annotated full dataset v3 (GM + AfriMMLU)",
        "version": "phase2_source_annotated_v3",
        "description": (
            "Larger dataset combining Global-MMLU African/European items "
            "(identified via region_list annotations and a curated high-precision "
            "keyword list) with AfriMMLU African items. Items with both Africa "
            "and Europe signals are excluded. Source is explicitly annotated; "
            "CS/CA labels are retained where present and '-' otherwise."
        ),
        "items": all_items,
        "statistics": {
            "n_total": len(all_items),
            "n_africa": region_counts["Africa"],
            "n_europe": region_counts["Europe"],
            "source_counts": dict(source_counts),
            "region_cs_counts": {f"{k[0]}_{k[1]}": v for k, v in cs_counts.items()},
            "gm_duplicates_removed": {
                "africa": len(removed_af),
                "europe": len(removed_eu),
            },
        }
    }


def build_gm_only_v3(gmmlu_df):
    gm_af = gmmlu_to_questions(
        gmmlu_df[gmmlu_df["region_label"] == "Africa"], "Africa", "GM"
    )
    gm_eu = gmmlu_to_questions(
        gmmlu_df[gmmlu_df["region_label"] == "Europe"], "Europe", "GM"
    )

    gm_af = dedupe_items(gm_af)
    gm_eu = dedupe_items(gm_eu)

    af_by_stratum = defaultdict(list)
    eu_by_stratum = defaultdict(list)
    for q in gm_af:
        af_by_stratum[(q["cat"], q["diff"], q["cs"])].append(q)
    for q in gm_eu:
        eu_by_stratum[(q["cat"], q["diff"], q["cs"])].append(q)

    matched_af = []
    matched_eu = []
    strata_used = []
    deficits = []

    rng = random.Random(SEED)
    for key in sorted(af_by_stratum.keys()):
        af_list = af_by_stratum[key]
        eu_list = eu_by_stratum.get(key, [])
        n_match = min(len(af_list), len(eu_list))
        if n_match == 0:
            deficits.append(f"{key}: {len(af_list)} Africa, {len(eu_list)} Europe")
            continue
        matched_af.extend(rng.sample(af_list, n_match))
        matched_eu.extend(rng.sample(eu_list, n_match))
        strata_used.append(f"{key}: n={n_match}")

    all_items = matched_af + matched_eu
    rng.shuffle(all_items)

    print(f"\nGM-only v3 matched items: {len(all_items)} "
          f"(Africa={len(matched_af)}, Europe={len(matched_eu)})")
    print(f"  Strata used: {len(strata_used)}")
    if deficits:
        print(f"  Strata with deficits (excluded): {len(deficits)}")

    return {
        "name": "AfriKnow Global-MMLU-only matched-source subset v3",
        "version": "phase2_gm_only_v3",
        "description": (
            "Africa-vs-Europe items drawn exclusively from Global-MMLU, "
            "matched by subject, difficulty, and cultural-sensitivity label. "
            "Region detected via region_list annotations and a curated "
            "high-precision keyword list; ambiguous items excluded."
        ),
        "items": all_items,
        "statistics": {
            "n_total": len(all_items),
            "n_africa": len(matched_af),
            "n_europe": len(matched_eu),
            "strata_used": strata_used,
            "strata_deficits": deficits,
        }
    }


def audit_dataset(dataset):
    items = dataset["items"]
    print(f"\n--- Audit: {dataset['name']} ---")
    print(f"Total items: {len(items)}")
    if not items:
        return

    df = pd.DataFrame(items)
    print("\nRegion x CS:")
    print(pd.crosstab(df["cs"], df["region"]))
    print("\nSubject x Region:")
    print(pd.crosstab(df["cat"], df["region"]))
    print("\nDifficulty x Region:")
    print(pd.crosstab(df["diff"], df["region"]))
    print("\nSource x Region:")
    print(pd.crosstab(df["source"], df["region"]))

    assert df["region"].isin(["Africa", "Europe"]).all()
    assert df["cs"].notna().all()
    assert (df["ch"].apply(lambda x: isinstance(x, list) and len(x) == 4)).all()
    print("Validation OK")


def main():
    gmmlu_df = load_gmmlu()
    gmmlu_df = classify_gmmlu_items(gmmlu_df)
    afrimmlu_items = load_afrimmlu_v11()

    full_v3 = build_source_annotated_full_v3(gmmlu_df, afrimmlu_items)
    gm_only_v3 = build_gm_only_v3(gmmlu_df)

    audit_dataset(full_v3)
    audit_dataset(gm_only_v3)

    with open("phase2_data/afriknow_source_annotated_full_v3.json", "w", encoding="utf-8") as f:
        json.dump(full_v3, f, ensure_ascii=False, indent=2)
    with open("phase2_data/afriknow_gm_only_v3.json", "w", encoding="utf-8") as f:
        json.dump(gm_only_v3, f, ensure_ascii=False, indent=2)

    print("\nSaved artefacts to ./phase2_data/:")
    print("  - afriknow_source_annotated_full_v3.json")
    print("  - afriknow_gm_only_v3.json")


if __name__ == "__main__":
    main()
