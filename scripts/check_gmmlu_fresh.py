"""
Check if we can get more GM-only items by loading Global-MMLU fresh.
This mimics build_expanded_v3_dataset.py but just reports counts.
"""
import re
import random
from collections import Counter, defaultdict

SEED = 42
random.seed(SEED)

try:
    from datasets import load_dataset
except ImportError:
    print("ERROR: datasets package not installed")
    exit(1)

def parse_list_col(val):
    if isinstance(val, list):
        return [str(x) for x in val]
    if isinstance(val, str):
        import ast
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
    "Africa", "African", "Sub-Saharan", "Sahara", "Sahel", "Horn of Africa",
    "Maghreb", "Kalahari", "Nile", "Congo River", "Niger River", "Zambezi",
    "Lake Victoria", "Lake Tanganyika", "Lake Malawi", "Mount Kilimanjaro",
    "Atlas Mountains", "Drakensberg", "Victoria Falls",
    "Lagos", "Cairo", "Nairobi", "Johannesburg", "Kinshasa", "Addis Ababa",
    "Dakar", "Accra", "Kampala", "Dar es Salaam", "Abidjan", "Casablanca",
    "Cape Town", "Luanda", "Khartoum", "Ibadan", "Alexandria", "Kano",
    "Douala", "Harare", "Lusaka", "Mogadishu", "Bamako", "Ouagadougou",
    "Antananarivo",
    "Zulu", "Maasai", "Hutu", "Tutsi", "Berber", "Tuareg", "Bantu",
    "Khoisan", "Xhosa", "Yoruba", "Hausa", "Igbo", "Amhara", "Oromo",
    "Shona", "Nubian",
    "Nelson Mandela", "Kwame Nkrumah", "Haile Selassie", "Shaka Zulu",
    "Mansa Musa", "Cleopatra", "Desmond Tutu", "Patrice Lumumba",
    "Jomo Kenyatta", "Julius Nyerere", "Thabo Mbeki", "F. W. de Klerk",
    "Muammar Gaddafi", "Gamal Abdel Nasser", "Anwar Sadat", "Hosni Mubarak",
    "Robert Mugabe", "Steve Biko", "Wangari Maathai", "Kofi Annan",
    "Idi Amin", "Mobutu",
    "Mali Empire", "Songhai Empire", "Great Zimbabwe", "Aksum", "Axum",
    "Ancient Egypt", "Carthage", "Ashanti Empire", "Kingdom of Benin",
    "Kingdom of Kongo", "Nubia", "Kush", "Ptolemaic",
    "apartheid", "African National Congress", "ANC", "Boer", "Boer War",
    "Great Trek", "Scramble for Africa", "Berlin Conference",
    "Atlantic slave trade", "African slave trade", "Rwandan genocide",
    "Darfur", "African Union", "OAU", "ECOWAS", "SADC", "Trans-Saharan trade",
]

EUROPE_STRONG = [
    "Europe", "European", "Balkans", "Scandinavia", "Iberian Peninsula",
    "Alps", "Mediterranean", "Baltic", "Danube", "Rhine", "Seine", "Thames",
    "Volga", "Elbe", "Loire", "Tagus", "Po River",
    "Paris", "London", "Berlin", "Rome", "Madrid", "Vienna", "Athens",
    "Moscow", "Amsterdam", "Brussels", "Prague", "Warsaw", "Budapest",
    "Lisbon", "Stockholm", "Copenhagen", "Helsinki", "Oslo", "Dublin",
    "Edinburgh", "Florence", "Venice", "Milan", "Barcelona", "Munich",
    "Hamburg", "Frankfurt", "Geneva", "Zurich", "Lyon", "Marseille",
    "Turin", "Naples", "Seville", "Valencia", "Manchester", "Birmingham",
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

def has_term(text, terms):
    if not isinstance(text, str):
        return False
    return any(re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE) for t in terms)

def has_africa_text(text):
    if not isinstance(text, str):
        return False
    text_no_aa = re.sub(r"\bAfrican[- ]American(s)?\b", "", text, flags=re.IGNORECASE)
    if re.search(r"\bguinea pig(s)?\b", text, re.IGNORECASE):
        return has_term(text_no_aa, [t for t in AFRICA_COUNTRIES if t != "Guinea"] + AFRICA_STRONG)
    return has_term(text_no_aa, AFRICA_COUNTRIES) or has_term(text_no_aa, AFRICA_STRONG)

def has_europe_text(text):
    return has_term(text, EUROPE_ALL)

def classify_row(region_list, question, subject):
    rl_africa = any(isinstance(r, str) and "africa" in r.lower() for r in region_list)
    rl_europe = any(isinstance(r, str) and "europe" in r.lower() for r in region_list)
    text_africa = has_africa_text(question)
    text_europe = has_europe_text(question)
    hard_europe = subject in HARD_EUROPE_SUBJECTS
    is_africa = rl_africa or text_africa
    is_europe = rl_europe or text_europe or hard_europe
    if is_africa and not is_europe:
        return "Africa"
    if is_europe and not is_africa:
        return "Europe"
    return ""

print("Loading CohereLabs/Global-MMLU (en, test)...")
gmmlu_df = load_dataset("CohereLabs/Global-MMLU", "en", split="test").to_pandas()
gmmlu_df["region_list"] = gmmlu_df["region"].apply(parse_list_col)
total = len(gmmlu_df)
print(f"Total Global-MMLU test items: {total}")

print("\nClassifying...")
gmmlu_df["region_label"] = gmmlu_df.apply(lambda r: classify_row(r["region_list"], r["question"], r["subject"]), axis=1)
counts = gmmlu_df["region_label"].value_counts()
print(f"  Exclusive Africa: {counts.get('Africa', 0)}")
print(f"  Exclusive Europe: {counts.get('Europe', 0)}")
print(f"  Ambiguous/none:   {counts.get('', 0)}")

gm_af = gmmlu_df[gmmlu_df["region_label"] == "Africa"]
gm_eu = gmmlu_df[gmmlu_df["region_label"] == "Europe"]
print(f"\nAfrica GM: {len(gm_af)}")
print(f"Europe GM: {len(gm_eu)}")

# Check subjects
print("\nAfrica GM subjects:")
print(gm_af['subject'].value_counts().to_string())
print("\nEurope GM subjects:")
print(gm_eu['subject'].value_counts().to_string())

# Match by (cat, diff)
af_by_stratum = defaultdict(list)
eu_by_stratum = defaultdict(list)
for _, row in gm_af.iterrows():
    af_by_stratum[(row['subject'], row['difficulty'])].append(row)
for _, row in gm_eu.iterrows():
    eu_by_stratum[(row['subject'], row['difficulty'])].append(row)

matched = 0
for key in af_by_stratum:
    n = min(len(af_by_stratum[key]), len(eu_by_stratum.get(key, [])))
    if n > 0:
        matched += n

print(f"\nMax matched pairs (by cat+diff): {matched}")
print(f"Max items: {matched * 2}")
print(f"Available Africa items for matching: {matched}")
