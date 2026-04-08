"""
CryptoGuard - Prediction Engine
Loads trained models and exposes predict() function
"""
import pickle
import numpy as np
import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

FEATURE_COLS = [
    'amount', 'gas_fee', 'tx_frequency', 'hour_of_day',
    'wallet_age_days', 'num_counterparties', 'failed_tx_ratio',
    'avg_tx_value', 'cross_chain', 'is_contract_interaction',
    'rapid_succession', 'new_wallet_flag'
]

_iso = None
_rf = None
_scaler = None


def _load_models():
    global _iso, _rf, _scaler
    if _iso is None:
        with open(os.path.join(MODEL_DIR, 'isolation_forest.pkl'), 'rb') as f:
            _iso = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'random_forest.pkl'), 'rb') as f:
            _rf = pickle.load(f)
        with open(os.path.join(MODEL_DIR, 'scaler.pkl'), 'rb') as f:
            _scaler = pickle.load(f)


def predict(transaction: dict) -> dict:
    """
    transaction: dict with keys matching FEATURE_COLS
    Returns: { 'verdict': 'fraud'|'legit', 'risk_score': 0-100,
               'fraud_probability': float, 'anomaly_score': float }
    """
    _load_models()

    features = np.array([[transaction.get(col, 0) for col in FEATURE_COLS]], dtype=float)
    scaled = _scaler.transform(features)

    # Random Forest fraud probability
    rf_prob = _rf.predict_proba(scaled)[0][1]  # probability of fraud class

    # Isolation Forest anomaly score (more negative = more anomalous)
    iso_raw = _iso.decision_function(scaled)[0]
    # Normalize: typical range [-0.5, 0.5] → map to [0, 1] (higher = more anomalous)
    anomaly_score = float(np.clip(0.5 - iso_raw, 0, 1))

    # Blend: 70% RF + 30% IF
    blended = 0.70 * rf_prob + 0.30 * anomaly_score
    risk_score = int(np.clip(blended * 100, 0, 100))

    verdict = 'fraud' if risk_score >= 60 else 'legit'

    return {
        'verdict': verdict,
        'risk_score': risk_score,
        'fraud_probability': round(float(rf_prob), 4),
        'anomaly_score': round(anomaly_score, 4)
    }