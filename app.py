from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from urllib.parse import urlparse

app = Flask(__name__)

# Secret key for sessions (required for Flask-Login)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
# DEBUG: Print environment variables (remove after fixing!)
print("🔍 DATABASE_URL from env:", os.environ.get('DATABASE_URL'))
print("🔍 All env keys:", list(os.environ.keys()))

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres'):
    # Handle Render's PostgreSQL URL
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("✅ Using PostgreSQL:", database_url)
else:
    # ONLY use MySQL in development (when RENDER env is not set)
    if os.environ.get('RENDER'):
        raise RuntimeError("❌ DATABASE_URL not set in production!")
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Harsha%40%401@localhost/my_saas_db'
        print("✅ Using local MySQL (development)")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ENV'] = 'development'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page if not authenticated

# User model (now inherits from UserMixin for Flask-Login)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    subscription_tier = db.Column(db.String(20), default='free')  # New field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # New field
    todos = db.relationship('Todo', backref='owner', lazy=True)
# Todo model
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('index.html', users=users)

@app.route('/dashboard')
@login_required
def dashboard():
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', user=current_user, todos=todos)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        subscription_tier = request.form.get('subscription_tier', 'free')  # Get subscription tier
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'error')
            return render_template('register.html')
        
        # Hash the password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Create new user with subscription tier
        new_user = User(
            name=name, 
            email=email, 
            password=hashed_password,
            subscription_tier=subscription_tier  # Add subscription tier
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add-todo', methods=['POST'])
@login_required
def add_todo():
    title = request.form['title']
    new_todo = Todo(title=title, user_id=current_user.id)
    db.session.add(new_todo)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/complete-todo/<int:todo_id>')
@login_required
def complete_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    # Make sure user owns this todo
    if todo.user_id == current_user.id:
        todo.completed = not todo.completed
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete-todo/<int:todo_id>')
@login_required
def delete_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    # Make sure user owns this todo
    if todo.user_id == current_user.id:
        db.session.delete(todo)
        db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Only create tables in development
    if app.config['ENV'] == 'development':
        with app.app_context():
            db.create_all()
            print("✅ Database tables created/verified!")
    app.run(debug=True)