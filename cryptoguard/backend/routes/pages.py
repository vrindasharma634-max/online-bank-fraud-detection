from flask import Blueprint, render_template, send_from_directory
import os

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index():
    return render_template('login.html')

@pages_bp.route('/login')
def login_page():
    return render_template('login.html')

@pages_bp.route('/signup')
def signup_page():
    return render_template('signup.html')

@pages_bp.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@pages_bp.route('/url-checker')
def url_checker_page():
    return render_template('url_checker.html')