from flask import Blueprint, render_template

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    return render_template('index.html')

@views_bp.route('/watch')
def watch_video():
    return render_template('player.html')

@views_bp.route('/login')
def login():
    return render_template('login.html')

@views_bp.route('/register_security')
def register_security():
    return render_template('register_security.html')
