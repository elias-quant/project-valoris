from pathlib import Path
import pyarrow.parquet as pq
from scipy import stats
import matplotlib.pyplot as plt
import duckdb
def find_parquet_files(data_root, asset_class="equity"):
    """
    Findet automatisch alle Parquet-Dateien
    einer bestimmten Asset-Klasse.
    """

    data_root = Path(data_root)

    asset_folder = (
        data_root
        / "daily_official"
        / f"asset_class={asset_class}"
    )

    if not asset_folder.exists():
        raise FileNotFoundError(
            f"Asset-Class-Ordner nicht gefunden: {asset_folder}"
        )

    parquet_files = sorted(
        asset_folder.rglob("*.parquet")
    )

    return parquet_files


def inspect_parquet_file(file_path):
    """
    Liest nur die Metadaten einer Parquet-Datei.
    Die eigentlichen Daten werden nicht geladen.
    """

    parquet_file = pq.ParquetFile(file_path)

    return {
        "file": file_path,
        "rows": parquet_file.metadata.num_rows,
        "columns": parquet_file.metadata.num_columns,
    }

def inspect_schema(file_path):
    """
    Zeigt die Spaltennamen und Datentypen einer Parquet-Datei,
    ohne die Daten zu laden.
    """

    parquet_file = pq.ParquetFile(file_path)
    schema = parquet_file.schema_arrow

    return schema

import pandas as pd


def load_parquet_file(file_path):
    """
    Lädt eine einzelne Parquet-Datei vollständig
    als pandas DataFrame.
    """

    return pd.read_parquet(file_path)

def deduplicate_daily_rows(df):
    """
    Entfernt Duplikate pro (ticker, timestamp_open_utc),
    behält jeweils die Zeile mit den meisten transactions.
    """

    vorher = len(df)

    df_sorted = df.sort_values("transactions", ascending=False)

    df_dedup = df_sorted.drop_duplicates(
        subset=["ticker", "timestamp_open_utc"],
        keep="first",
    )

    nachher = len(df_dedup)
    entfernt = vorher - nachher

    if entfernt > 0:
        print(f"  → {entfernt} Duplikat-Zeile(n) entfernt (niedrigere transactions verworfen)")

    return df_dedup.reset_index(drop=True)

def load_ticker_history(files, ticker):
    """
    Lädt die Kursdaten eines einzelnen Tickers über
    mehrere Parquet-Dateien hinweg und fügt sie zu
    einer durchgehenden Zeitreihe zusammen.
    """

    teil_dataframes = []

    for file in files:
        table = pq.read_table(
            file,
            filters=[("ticker", "=", ticker)],
        )

        if table.num_rows == 0:
            continue

        teil_df = table.to_pandas()
        teil_dataframes.append(teil_df)

    if not teil_dataframes:
        raise ValueError(f"Keine Daten gefunden für Ticker: {ticker}")

    gesamt_df = pd.concat(teil_dataframes, ignore_index=True)

    gesamt_df = deduplicate_daily_rows(gesamt_df)

    gesamt_df = gesamt_df.sort_values("timestamp_open_utc").reset_index(drop=True)

    return gesamt_df

def add_daily_returns(df):
    """
    Berechnet die tägliche prozentuale Rendite
    basierend auf dem Schlusskurs (close).
    """

    df = df.copy()

    df["daily_return"] = df["close"].pct_change()

    return df

def detect_split_candidates(df, toleranz=0.15):
    """
    Erkennt mögliche Split-Tage anhand eines
    ungewöhnlichen Kurssprungs, der zu einem
    typischen Split-Verhältnis passt (2, 3, 4, 5, 7, 10 ...
    oder deren Kehrwert bei Reverse-Splits).

    toleranz ist relativ (z. B. 0.15 = 15 % Abweichung
    vom sauberen Verhältnis noch erlaubt), weil sich der
    Kurs am Split-Tag zusätzlich normal bewegt.
    """

    df = df.copy()

    df["preis_verhaeltnis"] = df["close"].shift(1) / df["close"]

    bekannte_verhaeltnisse = [2, 3, 4, 5, 6, 7, 10, 1/2, 1/3, 1/4, 1/5, 1/6, 1/7, 1/10]

    def ist_split(verhaeltnis):
        if pd.isna(verhaeltnis):
            return False
        return any(
            abs(verhaeltnis - v) / v < toleranz for v in bekannte_verhaeltnisse
        )

    df["split_kandidat"] = df["preis_verhaeltnis"].apply(ist_split)

    return df[df["split_kandidat"]]

def add_outlier_flag(df, schwelle_std=2.0):
    """
    Markiert Tage, deren Rendite mehr als `schwelle_std`
    Standardabweichungen vom Mittelwert abweicht.
    """

    df = df.copy()

    mittelwert = df["daily_return"].mean()
    std = df["daily_return"].std()

    df["ist_ausreisser"] = (
        (df["daily_return"] - mittelwert).abs() > schwelle_std * std
    )

    return df


def event_study(df, tage_danach=(1, 5, 20)):
    """
    Für jeden als Ausreißer markierten Tag: berechnet die
    kumulierte Rendite in den N Tagen danach, getrennt nach
    positiven und negativen Ausreißern. Vergleicht das
    Ergebnis zusätzlich mit der unbedingten Baseline-Rendite
    (also: was passiert im Schnitt nach IRGENDEINEM Tag,
    nicht nur nach Ausreißern).
    """

    df = df.reset_index(drop=True)

    def kum_renditen_ab(indizes, n):
        werte = []
        for idx in indizes:
            ziel_idx = idx + n
            if ziel_idx < len(df):
                start_preis = df.loc[idx, "close"]
                end_preis = df.loc[ziel_idx, "close"]
                werte.append((end_preis / start_preis) - 1)
        return werte

    positive_ausreisser = df[
        df["ist_ausreisser"] & (df["daily_return"] > 0)
    ].index

    negative_ausreisser = df[
        df["ist_ausreisser"] & (df["daily_return"] < 0)
    ].index

    alle_tage = df.index

    zusammenfassung = {}

    for n in tage_danach:
        pos_werte = kum_renditen_ab(positive_ausreisser, n)
        neg_werte = kum_renditen_ab(negative_ausreisser, n)
        baseline_werte = kum_renditen_ab(alle_tage, n)

        zusammenfassung[f"{n}_tage_danach"] = {
            "nach_positivem_ausreisser": {
                "durchschnitt": sum(pos_werte) / len(pos_werte) if pos_werte else None,
                "anzahl": len(pos_werte),
            },
            "nach_negativem_ausreisser": {
                "durchschnitt": sum(neg_werte) / len(neg_werte) if neg_werte else None,
                "anzahl": len(neg_werte),
            },
            "baseline_alle_tage": {
                "durchschnitt": sum(baseline_werte) / len(baseline_werte) if baseline_werte else None,
                "anzahl": len(baseline_werte),
            },
        }

    return zusammenfassung




def teste_signifikanz(df, ist_ausreisser_index, tage_danach, baseline_werte):
    """
    Führt einen t-Test durch: unterscheidet sich die
    durchschnittliche Rendite nach Ausreißertagen signifikant
    von der Baseline-Rendite?
    """

    df = df.reset_index(drop=True)

    event_werte = []
    for idx in ist_ausreisser_index:
        ziel_idx = idx + tage_danach
        if ziel_idx < len(df):
            start_preis = df.loc[idx, "close"]
            end_preis = df.loc[ziel_idx, "close"]
            event_werte.append((end_preis / start_preis) - 1)

    t_stat, p_wert = stats.ttest_ind(event_werte, baseline_werte, equal_var=False)

    return {"t_stat": t_stat, "p_wert": p_wert, "n_events": len(event_werte)}


def plot_price_with_outliers(df, ticker_name="Ticker", speicherpfad=None):
    """
    Plottet den Kursverlauf und markiert Ausreißertage
    (grün = positiver Ausreißer, rot = negativer Ausreißer).
    """

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(
        df["timestamp_open_utc"], df["close"],
        linewidth=1, color="steelblue", label="Schlusskurs",
    )

    positive = df[df["ist_ausreisser"] & (df["daily_return"] > 0)]
    negative = df[df["ist_ausreisser"] & (df["daily_return"] < 0)]

    ax.scatter(
        positive["timestamp_open_utc"], positive["close"],
        color="green", s=25, zorder=5, label="Positiver Ausreißer",
    )
    ax.scatter(
        negative["timestamp_open_utc"], negative["close"],
        color="red", s=25, zorder=5, label="Negativer Ausreißer",
    )

    ax.set_title(f"{ticker_name} — Kursverlauf mit Ausreißertagen (split-adjustiert)")
    ax.set_xlabel("Datum")
    ax.set_ylabel("Kurs (USD)")
    ax.legend()
    ax.grid(alpha=0.3)

    fig.tight_layout()

    if speicherpfad:
        fig.savefig(speicherpfad, dpi=150)
        print(f"Chart gespeichert: {speicherpfad}")

    plt.show()


def load_clean_universe(files, mindest_dollar_volume=None):
    """
    Lädt den kompletten, deduplizierten Datensatz über alle Ticker
    und alle Dateien mittels DuckDB. Optional: Filter nach
    Mindest-Dollar-Volumen (Liquiditätsfilter für Phase 2).
    """

    dateipfade = [str(f) for f in files]

    verbindung = duckdb.connect()

    liquiditaets_filter = ""
    if mindest_dollar_volume is not None:
        liquiditaets_filter = f"WHERE dollar_volume_estimate >= {mindest_dollar_volume}"

    query = f"""
        WITH dedupliziert AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY ticker, timestamp_open_utc
                    ORDER BY transactions DESC
                ) AS rang
            FROM read_parquet(?)
            QUALIFY rang = 1
        )
        SELECT * EXCLUDE (rang)
        FROM dedupliziert
        {liquiditaets_filter}
        ORDER BY ticker, timestamp_open_utc
    """

    return verbindung.execute(query, [dateipfade]).df()

def save_clean_universe(files, zielpfad):
    """
    Baut den deduplizierten Datensatz einmalig und
    speichert ihn als eine einzige Parquet-Datei.
    """

    universum = load_clean_universe(files)

    universum.to_parquet(zielpfad, index=False)

    print(f"Gespeichert: {zielpfad} ({len(universum):,} Zeilen)")

    return universum

def add_daily_returns_universe(df):
    """
    Berechnet tägliche Renditen für einen Datensatz mit
    mehreren Tickern gleichzeitig. Wichtig: gruppiert nach
    Ticker, damit keine Rendite fälschlich vom letzten Tag
    eines Tickers zum ersten Tag des nächsten berechnet wird.
    """

    df = df.copy()

    df = df.sort_values(["ticker", "timestamp_open_utc"])

    df["daily_return"] = df.groupby("ticker")["close"].pct_change()

    return df


def adjust_for_splits(df, toleranz=0.15, mindestpreis=1.0):
    """
    Erkennt Split-Tage anhand von Kurs- UND Volumensprung
    gemeinsam (beide müssen zum selben Faktor passen) und
    passt alle Kurse VOR dem Split-Tag rückwirkend an.
    Vollkommen vektorisiert ohne df.apply(axis=1).
    """
    df = df.copy().reset_index(drop=True)
    if df.empty or len(df) < 2:
        return df

    df["volume"] = df["volume"].astype("float64")

    bekannte_verhaeltnisse = [2, 3, 4, 5, 6, 7, 10]

    vorheriger_preis = df["close"].shift(1)
    vorheriges_volumen = df["volume"].shift(1)

    preis_v = vorheriger_preis / df["close"]
    vol_v = df["volume"] / vorheriges_volumen.replace(0, pd.NA)

    # Mindestpreis-Bedingung & nicht die allererste Zeile prüfen
    gueltig = (df.index > 0) & (vorheriger_preis >= mindestpreis)

    split_faktor = pd.Series(index=df.index, dtype="float64")

    for v in bekannte_verhaeltnisse:
        preis_passt = (preis_v - v).abs() / v < toleranz
        volumen_passt = (vol_v - v).abs() / v < 0.6
        kandidat = gueltig & preis_passt & volumen_passt & split_faktor.isna()
        split_faktor[kandidat] = float(v)

    split_indizes = split_faktor[split_faktor.notna()].index

    if len(split_indizes) > 0:
        preis_spalten = ["open", "high", "low", "close"]
        # Von neu nach alt anpassen, damit mehrfache Splits kumulativ wirken
        for split_idx in sorted(split_indizes, reverse=True):
            faktor = split_faktor.loc[split_idx]
            vor_split = df.index < split_idx
            df.loc[vor_split, preis_spalten] = df.loc[vor_split, preis_spalten] / faktor
            df.loc[vor_split, "volume"] = df.loc[vor_split, "volume"] * faktor

    return df

def adjust_for_splits_universe(df, toleranz=0.15, mindestpreis=1.0):
    """
    Wendet die Split-Erkennung & Adjustierung auf JEDEN
    Ticker im Datensatz einzeln an.
    """
    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    teil_ergebnisse = []
    for ticker, gruppe in df.groupby("ticker", sort=False):
        gruppe_adjustiert = adjust_for_splits(gruppe, toleranz=toleranz, mindestpreis=mindestpreis)
        teil_ergebnisse.append(gruppe_adjustiert)

    return pd.concat(teil_ergebnisse, ignore_index=True)

def add_outlier_flag_universe(df, schwelle_std=2.0):
    """
    Markiert Ausreißertage pro Ticker (nicht global),
    da unterschiedliche Aktien unterschiedlich volatil sind.
    """

    df = df.copy()

    gruppiert = df.groupby("ticker")["daily_return"]
    mittelwert = gruppiert.transform("mean")
    std = gruppiert.transform("std")

    df["ist_ausreisser"] = (df["daily_return"] - mittelwert).abs() > schwelle_std * std

    return df

def add_forward_returns_universe(df, tage_danach=(1, 5, 20)):
    """
    Berechnet für jede Zeile die zukünftige kumulierte Rendite
    (N Tage später), getrennt pro Ticker.
    """

    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    for n in tage_danach:
        zukunfts_preis = df.groupby("ticker")["close"].shift(-n)
        df[f"fwd_{n}d"] = zukunfts_preis / df["close"] - 1

    return df

def event_study_universe(df, tage_danach=(1, 5, 20)):
    """
    Event Study über den gesamten Datensatz: vergleicht
    Renditen nach positiven/negativen Ausreißern mit der
    Baseline (alle Tage), inkl. Signifikanztest.
    """

    positive = df[df["ist_ausreisser"] & (df["daily_return"] > 0)]
    negative = df[df["ist_ausreisser"] & (df["daily_return"] < 0)]

    zusammenfassung = {}

    for n in tage_danach:
        spalte = f"fwd_{n}d"

        baseline_werte = df[spalte].dropna()
        pos_werte = positive[spalte].dropna()
        neg_werte = negative[spalte].dropna()

        _, pos_p = stats.ttest_ind(pos_werte, baseline_werte, equal_var=False)
        _, neg_p = stats.ttest_ind(neg_werte, baseline_werte, equal_var=False)

        zusammenfassung[f"{n}_tage_danach"] = {
            "nach_positivem_ausreisser": {
                "durchschnitt": pos_werte.mean(), "anzahl": len(pos_werte), "p_wert": pos_p,
            },
            "nach_negativem_ausreisser": {
                "durchschnitt": neg_werte.mean(), "anzahl": len(neg_werte), "p_wert": neg_p,
            },
            "baseline_alle_tage": {
                "durchschnitt": baseline_werte.mean(), "anzahl": len(baseline_werte),
            },
        }

    return zusammenfassung

def filter_liquid_universe(df, min_median_price=5.0, min_median_dollar_volume=1_000_000):
    """
    Behält nur Ticker, deren Median-Kurs und Median-Dollar-Volumen
    über den Schwellen liegen. Filtert ganze Ticker (nicht einzelne
    Tage), damit die Zeitreihe pro verbleibendem Ticker lückenlos bleibt.
    """

    ticker_stats = df.groupby("ticker").agg(
        median_price=("close", "median"),
        median_dollar_volume=("dollar_volume_estimate", "median"),
    )

    gueltige_ticker = ticker_stats[
        (ticker_stats["median_price"] >= min_median_price)
        & (ticker_stats["median_dollar_volume"] >= min_median_dollar_volume)
    ].index

    gefiltert = df[df["ticker"].isin(gueltige_ticker)].copy()

    print(f"Ticker vorher: {df['ticker'].nunique()}, nachher: {gefiltert['ticker'].nunique()}")
    print(f"Zeilen vorher: {len(df):,}, nachher: {len(gefiltert):,}")

    return gefiltert

def flag_bad_ticks_universe(df, schwelle=0.5, ruecksprung_toleranz=0.3):
    """
    Erkennt einzelne, isolierte Fehltage: Der Kurs weicht an
    Tag T stark vom Vortag ab, kehrt aber an Tag T+1 wieder
    fast zum Niveau von Tag T-1 zurück (V-förmiger Ausreißer).
    """

    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    vorheriger_close = df.groupby("ticker")["close"].shift(1)
    naechster_close = df.groupby("ticker")["close"].shift(-1)

    sprung_verhaeltnis = df["close"] / vorheriger_close
    grosser_sprung = (sprung_verhaeltnis > (1 + schwelle)) | (sprung_verhaeltnis < 1 / (1 + schwelle))

    rueckkehr_verhaeltnis = naechster_close / vorheriger_close
    kehrt_zurueck = (rueckkehr_verhaeltnis - 1).abs() < ruecksprung_toleranz

    df["ist_bad_tick"] = grosser_sprung & kehrt_zurueck

    anzahl = df["ist_bad_tick"].sum()
    print(f"Bad Ticks erkannt: {anzahl} von {len(df):,} Zeilen ({anzahl/len(df)*100:.3f}%)")

    return df

def flag_price_inconsistency_universe(df, verhaeltnis_schwelle=3.0):
    """
    Vergleicht 'close' mit dem impliziten Durchschnittspreis
    aus dollar_volume_estimate / volume. Weichen beide stark
    voneinander ab, ist 'close' vermutlich fehlerhaft —
    unabhängig davon, ob der Fehler nur einen oder mehrere
    Tage anhält.
    """

    df = df.copy()

    impliziter_preis = df["dollar_volume_estimate"] / df["volume"].replace(0, pd.NA)

    verhaeltnis = df["close"] / impliziter_preis

    df["ist_preis_inkonsistent"] = (
        (verhaeltnis > verhaeltnis_schwelle) | (verhaeltnis < 1 / verhaeltnis_schwelle)
    )

    anzahl = df["ist_preis_inkonsistent"].sum()
    print(f"Preis-Inkonsistenzen erkannt: {anzahl:,} von {len(df):,} Zeilen ({anzahl/len(df)*100:.3f}%)")

    return df

def flag_price_outliers_rolling(df, fenster=61, faktor_schwelle=5.0):
    """
    Vergleicht jeden Tag mit dem Median der umliegenden
    Handelstage (zeitlich zentriertes Fenster). Weicht der
    Kurs zu stark vom lokalen Median ab, wird er als
    Datenfehler markiert — unabhängig davon, ob der Fehler
    einen oder mehrere Tage anhält.
    """

    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    rollierender_median = (
        df.groupby("ticker")["close"]
        .transform(lambda s: s.rolling(window=fenster, center=True, min_periods=10).median())
    )

    verhaeltnis = df["close"] / rollierender_median

    df["ist_preis_ausreisser"] = (
        (verhaeltnis > faktor_schwelle) | (verhaeltnis < 1 / faktor_schwelle)
    )

    anzahl = df["ist_preis_ausreisser"].sum()
    print(f"Preis-Ausreißer (rollierender Median) erkannt: {anzahl:,} von {len(df):,} Zeilen ({anzahl/len(df)*100:.3f}%)")

    return df

def winsorize_column(df, spalte, unteres_perzentil=0.005, oberes_perzentil=0.995):
    """
    Kappt Extremwerte einer Spalte auf die angegebenen Perzentile,
    um den Einfluss einzelner Ausreißer auf den Mittelwert zu
    begrenzen, ohne die Zeilen komplett zu entfernen.
    """

    df = df.copy()

    untere_grenze = df[spalte].quantile(unteres_perzentil)
    obere_grenze = df[spalte].quantile(oberes_perzentil)

    df[spalte] = df[spalte].clip(lower=untere_grenze, upper=obere_grenze)

    print(f"  {spalte}: gekappt auf [{untere_grenze:.2%}, {obere_grenze:.2%}]")

    return df

def run_hypothesis_test(df, signal_spalte, hypothese_name, tage_danach=(1, 5, 20), metrik_praefix="fwd_"):
    """
    Generischer Hypothesentest: vergleicht eine Zielgröße
    (Standard: Forward Returns, `fwd_1d` etc.) zwischen Zeilen,
    bei denen `signal_spalte` True ist, und der Baseline.
    `metrik_praefix` erlaubt auch andere Zielgrößen, z.B.
    "fwd_vol_" für zukünftige Volatilität statt Renditen.
    """

    signal_df = df[df[signal_spalte]]

    ergebnisse = []

    for n in tage_danach:
        spalte = f"{metrik_praefix}{n}d"

        if spalte not in df.columns:
            continue

        signal_werte = signal_df[spalte].dropna()
        baseline_werte = df[spalte].dropna()

        if len(signal_werte) < 30:
            continue

        _, p_wert = stats.ttest_ind(signal_werte, baseline_werte, equal_var=False)

        ergebnisse.append({
            "hypothese": hypothese_name,
            "horizont": f"{n}d",
            "durchschnitt_signal": signal_werte.mean(),
            "durchschnitt_baseline": baseline_werte.mean(),
            "differenz": signal_werte.mean() - baseline_werte.mean(),
            "trefferquote": (signal_werte > 0).mean(),
            "n_events": len(signal_werte),
            "p_wert": p_wert,
        })

    return pd.DataFrame(ergebnisse)

def add_gap_signal(df, schwelle=0.03):
    """
    Markiert Tage mit einer Kurslücke (Gap) zwischen gestrigem
    Schlusskurs und heutigem Eröffnungskurs.
    """

    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    vorheriger_close = df.groupby("ticker")["close"].shift(1)
    gap = df["open"] / vorheriger_close - 1

    df["gap_hoch"] = gap > schwelle
    df["gap_tief"] = gap < -schwelle

    return df

def add_volatility_control_signal(df, ticker_vol_perzentil=0.7):
    """
    Markiert Tage bei Tickern mit hoher historischer Volatilität
    (Top 30%), aber OHNE Gap — als Kontrollgruppe, um zu prüfen,
    ob ein Gap-Effekt real ist oder nur "volatile Aktien performen
    besser" widerspiegelt.
    """

    df = df.copy()

    ticker_vol = df.groupby("ticker")["daily_return"].transform("std")
    schwelle = df.groupby("ticker")["daily_return"].transform("std").quantile(ticker_vol_perzentil)

    df["hohe_vola_kein_gap"] = (ticker_vol > schwelle) & ~df["gap_hoch"] & ~df["gap_tief"]

    return df

def add_momentum_signal(df, formation_tage=252, skip_tage=21, top_quantil=0.8, bottom_quantil=0.2):
    """
    12-1-Momentum (Jegadeesh & Titman): Rendite der letzten 12 Monate,
    aber die letzten ~21 Handelstage (1 Monat) werden übersprungen,
    um kurzfristige Reversal-Effekte nicht mit einzumischen.
    Ranking erfolgt CROSS-SECTIONAL (pro Handelstag über alle Ticker),
    nicht zeitlich pro Ticker.
    """

    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    close_vor_1_monat = df.groupby("ticker")["close"].shift(skip_tage)
    close_vor_13_monaten = df.groupby("ticker")["close"].shift(formation_tage)

    df["momentum_return"] = close_vor_1_monat / close_vor_13_monaten - 1

    rang = df.groupby("timestamp_open_utc")["momentum_return"].rank(pct=True)

    df["momentum_hoch"] = rang >= top_quantil
    df["momentum_tief"] = rang <= bottom_quantil

    return df

def add_forward_volatility_universe(df, tage_danach=(5, 20)):
    """
    Berechnet die realisierte Volatilität (Std.-Abw. der täglichen
    Renditen) in den N Tagen NACH dem aktuellen Tag, pro Ticker.
    """

    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    def forward_vol(gruppe):
        umgekehrt = gruppe["daily_return"][::-1]
        for n in tage_danach:
            roll = umgekehrt.rolling(window=n, min_periods=max(3, n // 2)).std()
            gruppe[f"fwd_vol_{n}d"] = roll[::-1].shift(-1).values
        return gruppe

    return df.groupby("ticker", group_keys=False).apply(forward_vol)


def add_volatility_regime_signal(df, fenster=5, perzentil=0.8):
    """
    Markiert Tage, an denen die Volatilität der letzten `fenster`
    Handelstage im oberen `perzentil` der HISTORISCHEN Volatilität
    dieses Tickers liegt (tickerspezifische Schwelle, da manche
    Aktien grundsätzlich volatiler sind als andere).
    """

    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    trailing_vol = (
        df.groupby("ticker")["daily_return"]
        .transform(lambda s: s.rolling(window=fenster, min_periods=3).std())
    )

    schwelle = trailing_vol.groupby(df["ticker"]).transform(lambda s: s.quantile(perzentil))

    df["vola_hoch_aktuell"] = trailing_vol > schwelle

    return df


def test_vol_clustering(df, signal_spalte, hypothese_name, horizonte=(5, 20)):
    """
    Wie run_hypothesis_test, aber für Volatilität statt Rendite:
    vergleicht künftige Schwankungsbreite (nicht Richtung) zwischen
    Signal-Gruppe und Baseline.
    """

    signal_df = df[df[signal_spalte]]

    ergebnisse = []

    for n in horizonte:
        spalte = f"fwd_vol_{n}d"

        signal_werte = signal_df[spalte].dropna()
        baseline_werte = df[spalte].dropna()

        if len(signal_werte) < 30:
            continue

        _, p_wert = stats.ttest_ind(signal_werte, baseline_werte, equal_var=False)

        ergebnisse.append({
            "hypothese": hypothese_name,
            "horizont": f"{n}d",
            "vol_signal": signal_werte.mean(),
            "vol_baseline": baseline_werte.mean(),
            "verhaeltnis": signal_werte.mean() / baseline_werte.mean(),
            "n_events": len(signal_werte),
            "p_wert": p_wert,
        })

    return pd.DataFrame(ergebnisse)

def add_forward_volatility_universe(df, fenster=(5, 20)):
    """
    Berechnet die realisierte Volatilität (Std.-Abw. der täglichen
    Renditen) der NÄCHSTEN n Handelstage (ab morgen, heute nicht
    mitgezählt), pro Ticker.
    """

    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    for n in fenster:
        spalte = f"fwd_vol_{n}d"

        def berechne(s, n=n):
            zukunft = s.shift(-1)
            return zukunft[::-1].rolling(window=n, min_periods=n).std()[::-1]

        df[spalte] = df.groupby("ticker")["daily_return"].transform(berechne)

    return df


def add_volatility_regime_signal(df, trailing_fenster=20, top_quantil=0.8, bottom_quantil=0.2):
    """
    Markiert Tage, an denen ein Ticker im Vergleich zu ALLEN
    anderen Tickern AM SELBEN TAG besonders hohe/niedrige
    Volatilität der letzten `trailing_fenster` Tage hatte
    (cross-sectionales Ranking, wie beim Momentum-Signal).
    """

    df = df.sort_values(["ticker", "timestamp_open_utc"]).reset_index(drop=True)

    trailing_vol = df.groupby("ticker")["daily_return"].transform(
        lambda s: s.rolling(window=trailing_fenster, min_periods=trailing_fenster).std()
    )
    df["trailing_vol"] = trailing_vol

    rang = df.groupby("timestamp_open_utc")["trailing_vol"].rank(pct=True)

    df["vola_hoch"] = rang >= top_quantil
    df["vola_tief"] = rang <= bottom_quantil

    return df

def test_weekday_effect(df):
    """
    Prüft, ob die durchschnittliche Tagesrendite an bestimmten
    Wochentagen signifikant von der Gesamt-Baseline abweicht
    (klassischer "Montags-Effekt"-Test).
    """

    df = df.copy()
    df["wochentag"] = df["timestamp_open_utc"].dt.day_name()

    baseline = df["daily_return"].dropna()

    ergebnisse = []

    for tag in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        gruppe = df[df["wochentag"] == tag]["daily_return"].dropna()

        if len(gruppe) < 30:
            continue

        _, p_wert = stats.ttest_ind(gruppe, baseline, equal_var=False)

        ergebnisse.append({
            "wochentag": tag,
            "durchschnitt": gruppe.mean(),
            "durchschnitt_baseline": baseline.mean(),
            "differenz": gruppe.mean() - baseline.mean(),
            "n_events": len(gruppe),
            "p_wert": p_wert,
        })

    return pd.DataFrame(ergebnisse)