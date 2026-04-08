"""
CryptoGuard - AI Fraud Detection Model
Trains IsolationForest + RandomForestClassifier on synthetic crypto transaction data
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import pickle
import os

SEED = 42
np.random.seed(SEED)

def generate_synthetic_data(n_samples=10000):
    """Generate realistic synthetic crypto transaction data"""
    n_legit = int(n_samples * 0.95)
    n_fraud = n_samples - n_legit

    # --- Legitimate transactions ---
    legit = pd.DataFrame({
        'amount': np.random.lognormal(mean=4.0, sigma=1.5, size=n_legit),
        'gas_fee': np.random.lognormal(mean=1.5, sigma=0.8, size=n_legit),
        'tx_frequency': np.random.poisson(lam=3, size=n_legit),
        'hour_of_day': np.random.randint(6, 23, size=n_legit),
        'wallet_age_days': np.random.randint(30, 2000, size=n_legit),
        'num_counterparties': np.random.randint(1, 50, size=n_legit),
        'failed_tx_ratio': np.random.beta(1, 20, size=n_legit),
        'avg_tx_value': np.random.lognormal(mean=3.8, sigma=1.2, size=n_legit),
        'cross_chain': np.random.binomial(1, 0.05, size=n_legit),
        'is_contract_interaction': np.random.binomial(1, 0.3, size=n_legit),
        'rapid_succession': np.random.binomial(1, 0.02, size=n_legit),
        'new_wallet_flag': np.random.binomial(1, 0.05, size=n_legit),
        'label': 0
    })

    # --- Fraudulent transactions ---
    fraud = pd.DataFrame({
        'amount': np.random.lognormal(mean=7.0, sigma=2.0, size=n_fraud),
        'gas_fee': np.random.lognormal(mean=3.5, sigma=1.2, size=n_fraud),
        'tx_frequency': np.random.poisson(lam=25, size=n_fraud),
        'hour_of_day': np.random.choice([0, 1, 2, 3, 4, 23], size=n_fraud),
        'wallet_age_days': np.random.randint(0, 15, size=n_fraud),
        'num_counterparties': np.random.randint(1, 5, size=n_fraud),
        'failed_tx_ratio': np.random.beta(5, 3, size=n_fraud),
        'avg_tx_value': np.random.lognormal(mean=7.5, sigma=2.5, size=n_fraud),
        'cross_chain': np.random.binomial(1, 0.7, size=n_fraud),
        'is_contract_interaction': np.random.binomial(1, 0.85, size=n_fraud),
        'rapid_succession': np.random.binomial(1, 0.85, size=n_fraud),
        'new_wallet_flag': np.random.binomial(1, 0.9, size=n_fraud),
        'label': 1
    })

    df = pd.concat([legit, fraud], ignore_index=True).sample(frac=1, random_state=SEED)
    return df

FEATURE_COLS = [
    'amount', 'gas_fee', 'tx_frequency', 'hour_of_day',
    'wallet_age_days', 'num_counterparties', 'failed_tx_ratio',
    'avg_tx_value', 'cross_chain', 'is_contract_interaction',
    'rapid_succession', 'new_wallet_flag'
]

def train_and_save():
    print("Generating synthetic dataset...")
    df = generate_synthetic_data(10000)
    X = df[FEATURE_COLS].values
    y = df['label'].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 1) Isolation Forest — anomaly detection
    print("Training IsolationForest...")
    iso = IsolationForest(n_estimators=200, contamination=0.05, random_state=SEED, n_jobs=-1)
    iso.fit(X_train_scaled)

    # 2) Random Forest — fraud classification
    print("Training RandomForestClassifier...")
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=12, min_samples_leaf=5,
        class_weight='balanced', random_state=SEED, n_jobs=-1
    )
    rf.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred = rf.predict(X_test_scaled)
    print("\n--- RandomForest Report ---")
    print(classification_report(y_test, y_pred, target_names=['Legit', 'Fraud']))

    # Save artifacts
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'isolation_forest.pkl'), 'wb') as f:
        pickle.dump(iso, f)
    with open(os.path.join(out_dir, 'random_forest.pkl'), 'wb') as f:
        pickle.dump(rf, f)
    with open(os.path.join(out_dir, 'scaler.pkl'), 'wb') as f:
        pickle.dump(scaler, f)

    print("\nModels saved to ml_model/")
    return iso, rf, scaler

if __name__ == '__main__':
    train_and_save()