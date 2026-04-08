from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend import db
from backend.models.models import Transaction, FraudAlert
import sys, os, uuid, random, string
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from ml_model.predictor import predict

predict_bp = Blueprint('predict', __name__)


def _rand_hash():
    return '0x' + ''.join(random.choices(string.hexdigits.lower(), k=64))


def _rand_wallet():
    return '0x' + ''.join(random.choices(string.hexdigits.lower(), k=40))


@predict_bp.route('/predict', methods=['POST'])
@jwt_required()
def predict_transaction():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    tx_data = {
        'amount': float(data.get('amount', 0)),
        'gas_fee': float(data.get('gas_fee', 0)),
        'tx_frequency': int(data.get('tx_frequency', 1)),
        'hour_of_day': int(data.get('hour_of_day', datetime.utcnow().hour)),
        'wallet_age_days': int(data.get('wallet_age_days', 365)),
        'num_counterparties': int(data.get('num_counterparties', 5)),
        'failed_tx_ratio': float(data.get('failed_tx_ratio', 0.0)),
        'avg_tx_value': float(data.get('avg_tx_value', data.get('amount', 0))),
        'cross_chain': int(data.get('cross_chain', 0)),
        'is_contract_interaction': int(data.get('is_contract_interaction', 0)),
        'rapid_succession': int(data.get('rapid_succession', 0)),
        'new_wallet_flag': int(data.get('new_wallet_flag', 0)),
    }

    result = predict(tx_data)

    tx = Transaction(
        user_id=user_id,
        tx_hash=data.get('tx_hash') or _rand_hash(),
        wallet_from=data.get('wallet_from') or _rand_wallet(),
        wallet_to=data.get('wallet_to') or _rand_wallet(),
        amount=tx_data['amount'],
        gas_fee=tx_data['gas_fee'],
        tx_frequency=tx_data['tx_frequency'],
        hour_of_day=tx_data['hour_of_day'],
        wallet_age_days=tx_data['wallet_age_days'],
        num_counterparties=tx_data['num_counterparties'],
        failed_tx_ratio=tx_data['failed_tx_ratio'],
        avg_tx_value=tx_data['avg_tx_value'],
        cross_chain=tx_data['cross_chain'],
        is_contract_interaction=tx_data['is_contract_interaction'],
        rapid_succession=tx_data['rapid_succession'],
        new_wallet_flag=tx_data['new_wallet_flag'],
        verdict=result['verdict'],
        risk_score=result['risk_score'],
        fraud_probability=result['fraud_probability'],
        anomaly_score=result['anomaly_score'],
    )
    db.session.add(tx)
    db.session.flush()

    if result['verdict'] == 'fraud':
        alert = FraudAlert(
            transaction_id=tx.id,
            user_id=user_id,
            risk_score=result['risk_score'],
            alert_message=f"High-risk transaction detected. Risk score: {result['risk_score']}/100. "
                          f"Fraud probability: {result['fraud_probability']*100:.1f}%."
        )
        db.session.add(alert)

    db.session.commit()
    return jsonify({**result, 'transaction': tx.to_dict()}), 200


@predict_bp.route('/predict/csv', methods=['POST'])
@jwt_required()
def predict_csv():
    import csv, io
    user_id = int(get_jwt_identity())
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    f = request.files['file']
    content = f.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    results = []
    for row in reader:
        try:
            tx_data = {
                'amount': float(row.get('amount', 0)),
                'gas_fee': float(row.get('gas_fee', 0)),
                'tx_frequency': int(float(row.get('tx_frequency', 1))),
                'hour_of_day': int(float(row.get('hour_of_day', 12))),
                'wallet_age_days': int(float(row.get('wallet_age_days', 365))),
                'num_counterparties': int(float(row.get('num_counterparties', 5))),
                'failed_tx_ratio': float(row.get('failed_tx_ratio', 0.0)),
                'avg_tx_value': float(row.get('avg_tx_value', row.get('amount', 0))),
                'cross_chain': int(float(row.get('cross_chain', 0))),
                'is_contract_interaction': int(float(row.get('is_contract_interaction', 0))),
                'rapid_succession': int(float(row.get('rapid_succession', 0))),
                'new_wallet_flag': int(float(row.get('new_wallet_flag', 0))),
            }
            result = predict(tx_data)
            tx = Transaction(
                user_id=user_id,
                tx_hash=row.get('tx_hash') or _rand_hash(),
                wallet_from=row.get('wallet_from') or _rand_wallet(),
                wallet_to=row.get('wallet_to') or _rand_wallet(),
                **{k: tx_data[k] for k in tx_data},
                verdict=result['verdict'],
                risk_score=result['risk_score'],
                fraud_probability=result['fraud_probability'],
                anomaly_score=result['anomaly_score'],
            )
            db.session.add(tx)
            db.session.flush()
            if result['verdict'] == 'fraud':
                db.session.add(FraudAlert(
                    transaction_id=tx.id, user_id=user_id,
                    risk_score=result['risk_score'],
                    alert_message=f"CSV batch: High-risk transaction. Score: {result['risk_score']}/100."
                ))
            results.append({**result, 'row': dict(row)})
        except Exception as e:
            results.append({'error': str(e), 'row': dict(row)})
    db.session.commit()
    fraud_count = sum(1 for r in results if r.get('verdict') == 'fraud')
    return jsonify({'processed': len(results), 'fraud_found': fraud_count, 'results': results}), 200