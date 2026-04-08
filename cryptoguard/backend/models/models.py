from backend import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'username': self.username, 'email': self.email}


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tx_hash = db.Column(db.String(100), unique=True)
    wallet_from = db.Column(db.String(100))
    wallet_to = db.Column(db.String(100))
    amount = db.Column(db.Float, nullable=False)
    gas_fee = db.Column(db.Float, default=0.0)
    tx_frequency = db.Column(db.Integer, default=1)
    hour_of_day = db.Column(db.Integer, default=12)
    wallet_age_days = db.Column(db.Integer, default=365)
    num_counterparties = db.Column(db.Integer, default=5)
    failed_tx_ratio = db.Column(db.Float, default=0.0)
    avg_tx_value = db.Column(db.Float, default=0.0)
    cross_chain = db.Column(db.Integer, default=0)
    is_contract_interaction = db.Column(db.Integer, default=0)
    rapid_succession = db.Column(db.Integer, default=0)
    new_wallet_flag = db.Column(db.Integer, default=0)
    verdict = db.Column(db.String(10))
    risk_score = db.Column(db.Integer)
    fraud_probability = db.Column(db.Float)
    anomaly_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'tx_hash': self.tx_hash,
            'wallet_from': self.wallet_from,
            'wallet_to': self.wallet_to,
            'amount': self.amount,
            'gas_fee': self.gas_fee,
            'verdict': self.verdict,
            'risk_score': self.risk_score,
            'fraud_probability': self.fraud_probability,
            'anomaly_score': self.anomaly_score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class FraudAlert(db.Model):
    __tablename__ = 'fraud_alerts'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    risk_score = db.Column(db.Integer)
    alert_message = db.Column(db.String(500))
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transaction = db.relationship('Transaction', backref='alerts')

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'risk_score': self.risk_score,
            'alert_message': self.alert_message,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'tx_hash': self.transaction.tx_hash if self.transaction else None
        }