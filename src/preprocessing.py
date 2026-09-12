import os
from duckdb import df
import pandas as pd
import numpy as np

def find_file(base_dir, filename):
    """
    Sucht eine Datei rekursiv im Ordner, falls sie in einem Unterordner liegt.
    """
    direct_path = os.path.join(base_dir, filename)
    if os.path.exists(direct_path):
        return direct_path
        
    for root, _, files in os.walk(base_dir):
        if filename in files:
            return os.path.join(root, filename)
            
    raise FileNotFoundError(f"Datei '{filename}' konnte nicht in {base_dir} oder dessen Unterordnern gefunden werden.")


def prepare_date_column(price_df):
    """
    Extrahiert aus timestamp_open_utc das Datum im Format YYYY-MM-DD.
    """
    df = price_df.copy()
    if 'timestamp_open_utc' in df.columns:
        df['date'] = pd.to_datetime(df['timestamp_open_utc']).dt.strftime('%Y-%m-%d')
    elif 'timestamp_close_utc' in df.columns:
        df['date'] = pd.to_datetime(df['timestamp_close_utc']).dt.strftime('%Y-%m-%d')
    return df


def apply_ticker_mapping(price_df, ticker_events_df=None):
    """
    Abwärtskompatibilitäts-Funktion: Nutzt Ticker/FIGI als Referenz.
    """
    df = price_df.copy()
    ticker_col = 'ticker' if 'ticker' in df.columns else 'figi'
    if ticker_col in df.columns:
        df['mapped_ticker'] = df[ticker_col]
    return df


def process_dividends(dividends_df, current_sim_date=None):
    """
    Kategorisiert Dividendentypen und wendet optional einen Point-in-Time Filter an.
    """
    df = dividends_df.copy()
    df['event_date'] = pd.to_datetime(df['event_date']).dt.strftime('%Y-%m-%d')

    if current_sim_date:
        df = df[df['event_date'] <= current_sim_date]

    recurring_types = ['recurring', 'supplemental']
    special_types = ['special', 'irregular']

    df['is_recurring'] = df['dividend_type'].isin(recurring_types).astype(int)
    df['is_special_shock'] = df['dividend_type'].isin(special_types).astype(int)
    df['is_unknown'] = (df['dividend_type'] == 'unknown').astype(int)

    return df

def adjust_prices_for_splits(price_df, splits_df):
    """
    Berechnet split-bereinigte Kurse und Volumen über Ticker und Datum.
    (Ticker statt FIGI als Join-Key, da FIGI bei 76% der Splits fehlt —
    siehe README: "Ticker is the reliable join key across all four files.")
    """
    if splits_df.empty or 'historical_adjustment_factor' not in splits_df.columns:
        for col in ['open', 'high', 'low', 'close']:
            if col in price_df.columns:
                price_df[f'{col}_adj'] = price_df[col]
        if 'volume' in price_df.columns:
            price_df['volume_adj'] = price_df['volume']
        return price_df

    splits = splits_df.copy()
    splits['event_date'] = pd.to_datetime(splits['event_date']).dt.strftime('%Y-%m-%d')

    df = pd.merge(
        price_df,
        splits[['ticker', 'event_date', 'historical_adjustment_factor']],
        left_on=['ticker', 'date'],
        right_on=['ticker', 'event_date'],
        how='left'
    )
    df.drop(columns=['event_date'], inplace=True)

    # Reihenfolge sicherstellen, bfill braucht sortierte Zeitreihe pro Ticker
    df = df.sort_values(['ticker', 'date']).reset_index(drop=True)

    df['historical_adjustment_factor'] = (
        df.groupby('ticker')['historical_adjustment_factor']
        .transform(lambda s: s.shift(-1).bfill())
)
    df['historical_adjustment_factor'] = df['historical_adjustment_factor'].fillna(1.0)

    for col in ['open', 'high', 'low', 'close']:
        if col in df.columns:
            df[f'{col}_adj'] = df[col] * df['historical_adjustment_factor']

    if 'volume' in df.columns:
        df['volume_adj'] = df['volume'] / df['historical_adjustment_factor']

    return df


def merge_dividends_to_prices(price_df, processed_div_df):
    """
    Verknüpft Dividendeninformationen über Ticker und Datum (Ex-Datum).
    """
    divs = processed_div_df.copy()

    cols_to_merge = ['ticker', 'event_date', 'amount', 'is_recurring', 'is_special_shock', 'is_unknown']

    df = pd.merge(
        price_df,
        divs[cols_to_merge],
        left_on=['ticker', 'date'],
        right_on=['ticker', 'event_date'],
        how='left'
    )

    df['div_amount'] = df['amount'].fillna(0.0)
    df.drop(columns=['amount', 'event_date'], errors='ignore', inplace=True)

    for col in ['is_recurring', 'is_special_shock', 'is_unknown']:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
    df["div_amount_adj"] = df["div_amount"] * df["historical_adjustment_factor"]

    return df