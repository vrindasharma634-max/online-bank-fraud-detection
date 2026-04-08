"""
CryptoGuard - URL Fraud Checker Route
Add this to your Flask backend (e.g. backend/routes/url_checker.py)
Then register it in create_app() with:
    from .routes.url_checker import url_checker_bp
    app.register_blueprint(url_checker_bp)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import re
import urllib.parse

url_checker_bp = Blueprint('url_checker', __name__, url_prefix='/api')


# ── Heuristic rule-based fraud signals ──────────────────────────────────────

SUSPICIOUS_KEYWORDS = [
    'login', 'signin', 'verify', 'account', 'update', 'secure', 'banking',
    'wallet', 'crypto', 'bitcoin', 'ethereum', 'binance', 'metamask',
    'confirm', 'password', 'paypal', 'support', 'helpdesk', 'recovery',
    'airdrop', 'claim', 'free', 'bonus', 'prize', 'winner', 'urgent',
]

TRUSTED_CRYPTO_DOMAINS = {
    'coinbase.com', 'binance.com', 'kraken.com', 'gemini.com',
    'crypto.com', 'uniswap.org', 'opensea.io', 'etherscan.io',
    'blockchain.com', 'metamask.io', 'ledger.com', 'trezor.io',
}

KNOWN_PHISHING_TLDS = ['.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.click', '.link']


def analyse_url(url: str) -> dict:
    """
    Returns a risk breakdown dict:
        score        – 0-100 (higher = riskier)
        verdict      – 'safe' | 'suspicious' | 'fraud'
        flags        – list of human-readable warning strings
        details      – structured metadata about the URL
    """
    flags = []
    score = 0

    # ── Normalise ────────────────────────────────────────────────────────────
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return {
            'score': 100,
            'verdict': 'fraud',
            'flags': ['Could not parse URL'],
            'details': {},
        }

    hostname = parsed.hostname or ''
    path     = parsed.path.lower()
    full_url = url.lower()

    # ── 1. Protocol ──────────────────────────────────────────────────────────
    if parsed.scheme == 'http':
        flags.append('No HTTPS – connection is unencrypted')
        score += 15

    # ── 2. IP address instead of domain ──────────────────────────────────────
    ip_pattern = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')
    if ip_pattern.match(hostname):
        flags.append('IP address used instead of a domain name')
        score += 30

    # ── 3. Suspicious TLD ────────────────────────────────────────────────────
    for tld in KNOWN_PHISHING_TLDS:
        if hostname.endswith(tld):
            flags.append(f'High-risk free TLD detected: {tld}')
            score += 25
            break

    # ── 4. Homograph / typosquatting (basic) ─────────────────────────────────
    for trusted in TRUSTED_CRYPTO_DOMAINS:
        base = trusted.split('.')[0]
        # present in hostname but not an exact match → typosquatting
        if base in hostname and hostname != trusted and not hostname.endswith('.' + trusted):
            flags.append(f'Possible typosquatting of trusted site: {trusted}')
            score += 35
            break

    # ── 5. Excessive subdomains ───────────────────────────────────────────────
    parts = hostname.split('.')
    if len(parts) > 4:
        flags.append(f'Unusual number of subdomains ({len(parts) - 2})')
        score += 20

    # ── 6. Suspicious keywords in URL ────────────────────────────────────────
    hit_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in full_url]
    if hit_keywords:
        flags.append(f'Phishing keywords in URL: {", ".join(hit_keywords[:5])}')
        score += min(len(hit_keywords) * 8, 30)

    # ── 7. Very long URL ─────────────────────────────────────────────────────
    if len(url) > 100:
        flags.append(f'Unusually long URL ({len(url)} chars) – often used to obscure destination')
        score += 10

    # ── 8. URL shorteners ────────────────────────────────────────────────────
    shorteners = ['bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'buff.ly', 'rebrand.ly']
    if any(s in hostname for s in shorteners):
        flags.append('URL shortener detected – real destination is hidden')
        score += 20

    # ── 9. Hex / percent encoded characters ──────────────────────────────────
    if re.search(r'%[0-9a-fA-F]{2}', url):
        flags.append('URL contains encoded characters (possible obfuscation)')
        score += 10

    # ── 10. Double slashes / redirect patterns ────────────────────────────────
    if '//' in path or 'redirect' in full_url or 'url=' in full_url:
        flags.append('Redirect pattern detected in URL path')
        score += 15

    # ── Cap at 100 ────────────────────────────────────────────────────────────
    score = min(score, 100)

    if score < 30:
        verdict = 'safe'
    elif score < 60:
        verdict = 'suspicious'
    else:
        verdict = 'fraud'

    return {
        'score':   score,
        'verdict': verdict,
        'flags':   flags if flags else ['No suspicious signals detected'],
        'details': {
            'protocol':  parsed.scheme,
            'hostname':  hostname,
            'path':      parsed.path,
            'query':     parsed.query,
            'url_length': len(url),
        },
    }


# ── Route ────────────────────────────────────────────────────────────────────

@url_checker_bp.route('/check-url', methods=['POST'])
@jwt_required()
def check_url():
    """
    POST /api/check-url
    Body: { "url": "https://example.com" }
    Returns analysis result.
    Authentication: Bearer JWT (same as other CryptoGuard endpoints).
    """
    data = request.get_json(silent=True) or {}
    url  = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    if len(url) > 2048:
        return jsonify({'error': 'URL too long (max 2048 chars)'}), 400

    result = analyse_url(url)
    result['url']       = url
    result['checked_at'] = datetime.utcnow().isoformat()

    return jsonify(result), 200


# ── Optional: public (no auth) lightweight endpoint ──────────────────────────

@url_checker_bp.route('/check-url/public', methods=['POST'])
def check_url_public():
    """
    POST /api/check-url/public  (no JWT required)
    Rate-limit this in production (e.g. flask-limiter).
    """
    data = request.get_json(silent=True) or {}
    url  = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    result = analyse_url(url)
    result['url']        = url
    result['checked_at'] = datetime.utcnow().isoformat()

    return jsonify(result), 200