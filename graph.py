import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import pandas as pd

# ------------ PARAMÈTRES ---------------- #
TOP_N_FUNCS = 10           # nombre de fonctions à afficher
DURATION_DAYS = 1          # durée fictive d'un changement
# ---------------------------------------- #

# Lire le patch log
with open("gitlog.txt", "r") as f:
    lines = f.readlines()

entries = []
current_date = None
in_diff = False

for line in lines:
    line = line.strip()

    # Récupérer la date
    if line.startswith("Date:"):
        try:
            date_str = line.split("Date:")[1].strip()
            current_date = datetime.fromisoformat(date_str)
        except Exception as e:
            current_date = None  # on ignore si erreur

    # Début d'un diff
    if line.startswith("diff --git"):
        in_diff = True
        continue

    if in_diff and current_date:
        # Cherche une fonction Python (ajustable selon langage)
        match = re.match(r"\+def (\w+)\(", line)
        if match:
            func = match.group(1)
            entries.append({
                "function": func,
                "date": current_date
            })

# Convertir en DataFrame
df = pd.DataFrame(entries)

if df.empty:
    print("Aucune fonction détectée. Vérifie le patch_log.txt ou le format des définitions de fonction.")
    exit()

# Ajouter date de fin fictive
df["end_date"] = df["date"] + timedelta(days=DURATION_DAYS)

# Garder les fonctions les plus modifiées
top_funcs = df["function"].value_counts().nlargest(TOP_N_FUNCS).index
df = df[df["function"].isin(top_funcs)]

# Supprimer les doublons exacts
df = df.drop_duplicates()

# Créer le Gantt
fig, ax = plt.subplots(figsize=(12, 6))

for _, row in df.iterrows():
    ax.barh(row["function"],
            (row["end_date"] - row["date"]).days or 1,
            left=row["date"],
            color="gray")  # même couleur pour tout

# Format de l'axe X
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.xticks(rotation=45, ha='right')

# Titre et labels
ax.set_xlabel("Date")
ax.set_ylabel("Fonction modifiée")
ax.set_title("Diagramme de Gantt des modifications par fonction")

plt.tight_layout()
plt.show()
