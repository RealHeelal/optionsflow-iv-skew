#!/usr/bin/env python3
"""
OptionsFlow IV Skew Analyzer
Compares OTM Call IV vs OTM Put IV to detect smart money bias.
Formula: (OTM Put IV - OTM Call IV) / ATM IV
Based on Blair Hull and Quantra/QuantInsti skew methodology.
"""

import sys
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")


def get_atm_strike(price: float, strikes: pd.Series) -> float:
    return float(strikes.iloc[(strikes - price).abs().argsort().iloc[0]])


def get_otm_call_strike(price: float, strikes: pd.Series, offset: int = 1) -> float:
    otm = strikes[strikes > price].sort_values()
    return float(otm.iloc[offset - 1]) if len(otm) >= offset else float(otm.iloc[-1])


def get_otm_put_strike(price: float, strikes: pd.Series, offset: int = 1) -> float:
    otm = strikes[strikes < price].sort_values(ascending=False)
    return float(otm.iloc[offset - 1]) if len(otm) >= offset else float(otm.iloc[-1])


def analyze_skew(ticker: str, target_expiry: str = None) -> dict:
    tk = yf.Ticker(ticker)

    hist = tk.history(period="1d", interval="1m")
    if hist.empty:
        return {"error": f"Cannot fetch price for {ticker}"}
    current_price = float(hist["Close"].iloc[-1])

    expirations = tk.options
    if not expirations:
        return {"error": f"No options chain found for {ticker}"}

    if target_expiry and target_expiry in expirations:
        expiry = target_expiry
    else:
        today  = datetime.now().date()
        future = [e for e in expirations
                  if (datetime.strptime(e, "%Y-%m-%d").date() - today).days >= 1]
        if not future:
            return {"error": "No upcoming expiration found"}
        expiry = future[0]

    chain = tk.option_chain(expiry)
    calls = chain.calls[["strike", "impliedVolatility", "openInterest"]].copy()
    puts  = chain.puts[["strike",  "impliedVolatility", "openInterest"]].copy()

    calls = calls[calls["impliedVolatility"] > 0.01].dropna()
    puts  = puts[puts["impliedVolatility"]   > 0.01].dropna()

    if calls.empty or puts.empty:
        return {"error": "Insufficient IV data in options chain"}

    atm_strike      = get_atm_strike(current_price, calls["strike"])
    otm_call_strike = get_otm_call_strike(current_price, calls["strike"], offset=1)
    otm_put_strike  = get_otm_put_strike(current_price,  puts["strike"],  offset=1)

    def get_iv(df, strike):
        row = df[df["strike"] == strike]
        return float(row["impliedVolatility"].iloc[0]) if not row.empty else None

    atm_iv      = get_iv(calls, atm_strike) or float(calls["impliedVolatility"].median())
    otm_call_iv = get_iv(calls, otm_call_strike) or atm_iv
    otm_put_iv  = get_iv(puts,  otm_put_strike)  or atm_iv

    skew_raw = otm_put_iv - otm_call_iv
    skew_pct = (skew_raw / atm_iv) * 100 if atm_iv > 0 else 0.0

    mean_call_iv = float(calls["impliedVolatility"].mean()) * 100
    mean_put_iv  = float(puts["impliedVolatility"].mean())  * 100

    all_iv   = pd.concat([calls["impliedVolatility"], puts["impliedVolatility"]])
    iv_min   = float(all_iv.min()) * 100
    iv_max   = float(all_iv.max()) * 100
    iv_rank  = ((atm_iv * 100 - iv_min) / (iv_max - iv_min) * 100) \
               if (iv_max - iv_min) > 0 else 50.0

    if skew_pct > 5:
        signal, bias, trade = "PUT HEAVY", "BEARISH", "PUT"
        note = "Smart money buying puts — bearish hedge detected"
    elif skew_pct < -5:
        signal, bias, trade = "CALL HEAVY", "BULLISH", "CALL"
        note = "Smart money buying calls — bullish positioning detected"
    else:
        signal, bias, trade = "NEUTRAL", "NO EDGE", "FOLLOW OTHER SIGNALS"
        note = "No significant smart money directional bet"

    return {
        "ticker":           ticker.upper(),
        "expiry":           expiry,
        "current_price":    round(current_price, 2),
        "atm_strike":       atm_strike,
        "atm_iv_pct":       round(atm_iv * 100, 2),
        "otm_call_strike":  otm_call_strike,
        "otm_call_iv_pct":  round(otm_call_iv * 100, 2),
        "otm_put_strike":   otm_put_strike,
        "otm_put_iv_pct":   round(otm_put_iv * 100, 2),
        "mean_call_iv_pct": round(mean_call_iv, 2),
        "mean_put_iv_pct":  round(mean_put_iv, 2),
        "skew_pct":         round(skew_pct, 2),
        "iv_rank_approx":   round(iv_rank, 1),
        "signal":           signal,
        "bias":             bias,
        "trade_direction":  trade,
        "note":             note,
    }


def format_output(r: dict) -> str:
    if "error" in r:
        return f"\n ERROR: {r['error']}\n"

    return f"""
====================================================
IV SKEW ANALYSIS — {r['ticker']} | exp {r['expiry']}
====================================================
Price        : ${r['current_price']}
ATM Strike   : ${r['atm_strike']}  | ATM IV : {r['atm_iv_pct']}%
OTM Call     : ${r['otm_call_strike']} | Call IV: {r['otm_call_iv_pct']}%
OTM Put      : ${r['otm_put_strike']}  | Put IV : {r['otm_put_iv_pct']}%
----------------------------------------------------
Mean Call IV : {r['mean_call_iv_pct']}%
Mean Put IV  : {r['mean_put_iv_pct']}%
IV Rank      : ~{r['iv_rank_approx']}%
Skew         : {r['skew_pct']:+.2f}%
----------------------------------------------------
Signal       : {r['signal']}
Bias         : {r['bias']}
Trade WITH   : {r['trade_direction']}
Note         : {r['note']}
====================================================
"""


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python iv_skew.py TICKER [EXPIRY_DATE]")
        sys.exit(1)

    ticker_arg = args[0].upper()
    expiry_arg = args[1] if len(args) > 1 else None
    result     = analyze_skew(ticker_arg, expiry_arg)
    print(format_output(result))
