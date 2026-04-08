from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.models import Transaction, FraudAlert
from sqlalchemy import func
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def stats():
    user_id = int(get_jwt_identity())
    total = Transaction.query.filter_by(user_id=user_id).count()
    fraud = Transaction.query.filter_by(user_id=user_id, verdict='fraud').count()
    legit = total - fraud
    alerts = FraudAlert.query.filter_by(user_id=user_id, is_resolved=False).count()
    avg_risk = Transaction.query.filter_by(user_id=user_id).with_entities(
        func.avg(Transaction.risk_score)).scalar() or 0

    return jsonify({
        'total_transactions': total,
        'fraud_count': fraud,
        'legit_count': legit,
        'active_alerts': alerts,
        'avg_risk_score': round(float(avg_risk), 1)
    })


@dashboard_bp.route('/dashboard/transactions', methods=['GET'])
@jwt_required()
def transactions():
    user_id = int(get_jwt_identity())
    txs = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.created_at.desc()).limit(50).all()
    return jsonify({'transactions': [t.to_dict() for t in txs]})


@dashboard_bp.route('/dashboard/alerts', methods=['GET'])
@jwt_required()
def alerts():
    user_id = int(get_jwt_identity())
    alts = FraudAlert.query.filter_by(user_id=user_id)\
        .order_by(FraudAlert.created_at.desc()).limit(20).all()
    return jsonify({'alerts': [a.to_dict() for a in alts]})


@dashboard_bp.route('/dashboard/trend', methods=['GET'])
@jwt_required()
def trend():
    user_id = int(get_jwt_identity())
    days = 7
    trend_data = []
    for i in range(days - 1, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        start = datetime.combine(day, datetime.min.time())
        end = datetime.combine(day, datetime.max.time())
        total = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.created_at >= start,
            Transaction.created_at <= end
        ).count()
        fraud = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.verdict == 'fraud',
            Transaction.created_at >= start,
            Transaction.created_at <= end
        ).count()
        trend_data.append({'date': day.strftime('%b %d'), 'total': total, 'fraud': fraud})
    return jsonify({'trend': trend_data})


@dashboard_bp.route('/dashboard/alerts/<int:alert_id>/resolve', methods=['POST'])
@jwt_required()
def resolve_alert(alert_id):
    user_id = int(get_jwt_identity())
    alert = FraudAlert.query.filter_by(id=alert_id, user_id=user_id).first()
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    alert.is_resolved = True
    from backend import db
    db.session.commit()
    return jsonify({'message': 'Alert resolved'})