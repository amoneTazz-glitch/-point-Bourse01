"""
POINT MARCHE QUOTIDIEN
Variation de la derniere seance pour 4 indices majeurs.

Usage :
    python marches.py
    python marches.py --jours 5      -> montre aussi les 5 derniers jours

Installation prealable (une seule fois) :
    pip install yfinance

Le script ecrit aussi chaque releve dans historique_marches.csv,
ce qui te constitue ta propre base au fil des jours.
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

# Les indices suivis. La cle est le symbole boursier (ticker).
INDICES = {
    "^GSPC": "S&P 500",
    "^NDX": "Nasdaq 100",
    "^FCHI": "CAC 40",
    "URTH": "MSCI World (ETF URTH)",
}

HISTORIQUE = Path("historique_marches.csv")


# ---------------------------------------------------------------
# RECUPERATION
# ---------------------------------------------------------------

def derniere_variation(ticker):
    """Renvoie un dict decrivant la derniere seance de l'indice.

    On telecharge un mois d'historique plutot que deux jours :
    week-ends, jours feries et decalages horaires font qu'on ne
    sait jamais a l'avance combien de seances il y a eu recemment.
    """
    historique = yf.Ticker(ticker).history(period="1mo", interval="1d")

    # Il faut au moins deux cloture pour calculer une variation.
    if historique is None or len(historique) < 2:
        return None

    cloture = historique["Close"].dropna()
    if len(cloture) < 2:
        return None

    # .iloc[-1] = la derniere ligne, .iloc[-2] = l'avant-derniere
    dernier = float(cloture.iloc[-1])
    precedent = float(cloture.iloc[-2])

    return {
        "ticker": ticker,
        "nom": INDICES[ticker],
        "date": cloture.index[-1].date(),
        "date_precedente": cloture.index[-2].date(),
        "cloture": dernier,
        "precedente": precedent,
        "variation_pct": (dernier / precedent - 1) * 100,
        "variation_pts": dernier - precedent,
        "serie": cloture,
    }


def collecter():
    resultats = []
    for ticker in INDICES:
        try:
            donnee = derniere_variation(ticker)
        except Exception as e:
            # Un indice indisponible ne doit pas faire tomber le reste.
            print(f"  {INDICES[ticker]} : echec ({e})")
            continue

        if donnee is None:
            print(f"  {INDICES[ticker]} : donnees insuffisantes")
            continue

        resultats.append(donnee)
    return resultats


# ---------------------------------------------------------------
# AFFICHAGE
# ---------------------------------------------------------------

def fleche(variation):
    if variation > 0.05:
        return "^"
    if variation < -0.05:
        return "v"
    return "="


def afficher(resultats, jours):
    if not resultats:
        print("Aucune donnee recuperee.")
        return

    print()
    print("=" * 62)
    print(f"  POINT MARCHE — {datetime.now():%A %d %B %Y, %H:%M}")
    print("=" * 62)
    print()
    print(f"{'Indice':<24}{'Cloture':>12}{'Variation':>12}{'':>6}")
    print("-" * 62)

    for r in resultats:
        print(f"{r['nom']:<24}{r['cloture']:>12,.2f}"
              f"{r['variation_pct']:>11.2f}%   {fleche(r['variation_pct'])}")

    # Les dates de cloture different d'un indice a l'autre :
    # on les affiche pour lever toute ambiguite.
    print()
    for r in resultats:
        print(f"  {r['nom']:<24} seance du {r['date']:%d/%m/%Y} "
              f"(vs {r['date_precedente']:%d/%m/%Y})")

    # --- Vue sur plusieurs jours, si demandee ---
    if jours > 1:
        print("\n" + "-" * 62)
        print(f"Variations quotidiennes sur {jours} seances (%)")
        print("-" * 62)

        tableau = pd.DataFrame({
            r["nom"]: r["serie"].pct_change().mul(100).tail(jours)
            for r in resultats
        })
        tableau.index = tableau.index.strftime("%d/%m")
        print(tableau.round(2).to_string())

    print()


# ---------------------------------------------------------------
# HISTORIQUE  <-- l'etat conserve entre deux executions
# ---------------------------------------------------------------

def enregistrer(resultats):
    """Ajoute le releve du jour au fichier historique, sans doublon."""
    if not resultats:
        return

    nouvelles = pd.DataFrame([{
        "releve": datetime.now().strftime("%Y-%m-%d"),
        "indice": r["nom"],
        "date_seance": r["date"],
        "cloture": round(r["cloture"], 2),
        "variation_pct": round(r["variation_pct"], 3),
    } for r in resultats])

    if HISTORIQUE.exists():
        ancien = pd.read_csv(HISTORIQUE)
        total = pd.concat([ancien, nouvelles], ignore_index=True)
        # Si le script tourne deux fois le meme jour, on ne duplique pas.
        total = total.drop_duplicates(subset=["indice", "date_seance"], keep="last")
    else:
        total = nouvelles

    total.to_csv(HISTORIQUE, index=False, encoding="utf-8-sig")
    print(f"Historique mis a jour : {HISTORIQUE} ({len(total)} lignes)")


# ---------------------------------------------------------------
# POINT D'ENTREE
# ---------------------------------------------------------------

def main():
    parseur = argparse.ArgumentParser(description="Point marche quotidien.")
    parseur.add_argument("--jours", type=int, default=1,
                         help="Nombre de seances a detailler")
    parseur.add_argument("--sans-historique", action="store_true",
                         help="Ne pas ecrire dans le fichier historique")
    args = parseur.parse_args()

    print("Recuperation des cours...")
    resultats = collecter()

    afficher(resultats, args.jours)

    if not args.sans_historique:
        enregistrer(resultats)


if __name__ == "__main__":
    main()
