from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Cesta k databázi
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  # Tajný klíč pro session
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Nastavení pro přesměrování na přihlášení

# Definice modelu úkolů
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Přidání vztahu
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Přidání sloupce created_at

    user = db.relationship('User', backref='tasks')  # Definice vztahu

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Inicializace databáze
with app.app_context():
    db.create_all()  # Mějte na paměti, že byste měli spustit migrace

# Načtení uživatele při přihlašování
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        print(f"Received title: {request.form['title']}")  # Debug log
        new_task = Task(title=request.form['title'], user_id=current_user.id)
        db.session.add(new_task)
        db.session.commit()
        return jsonify({'id': new_task.id, 'title': new_task.title})  # Vrátí JSON s novým úkolem

    # Výpočet dokončených a probíhajících úkolů pro aktuální týden
    start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())  # Pondělí
    end_of_week = start_of_week + timedelta(days=7)  # Příští neděle
    completed_tasks_count = Task.query.filter_by(user_id=current_user.id, completed=True).filter(
        Task.created_at >= start_of_week).count()
    ongoing_tasks_count = Task.query.filter_by(user_id=current_user.id, completed=False).filter(
        Task.created_at >= start_of_week).count()

    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', tasks=tasks,
                           completed_count=completed_tasks_count,
                           ongoing_count=ongoing_tasks_count)  # Oprava názvu proměnné

@app.route('/complete/<int:task_id>', methods=['POST'])
@login_required
def complete(task_id):
    task = Task.query.get(task_id)
    if task:
        task.completed = True  # Změň splněné na True místo mazání úkolu
        db.session.commit()  # Ulož změny do databáze
    return '', 204  # Vrátíme prázdnou odpověď pro AJAX

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')  # Hasher pro heslo
        
        # Kontrola, zda už uživatel existuje
        if User.query.filter_by(username=username).first():
            return 'Username already exists. Please choose another one.', 400  # Zpráva o existujícím uživatelském jménu
        
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)  # Přidání uživatele do session
        db.session.commit()  # Uložení změn do databáze
        
        # Automatické přihlášení uživatele po registraci
        login_user(new_user)
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')  # Přidání chybové zprávy
    
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))  # Přesměrování na login po odhlášení

@app.route('/task-stats', methods=['GET'])
@login_required
def task_stats():
    # Výpočet dokončených a probíhajících úkolů pro aktuální týden
    start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())  # Pondělí
    completed_tasks_count = Task.query.filter_by(user_id=current_user.id, completed=True).filter(
        Task.created_at >= start_of_week).count()
    ongoing_tasks_count = Task.query.filter_by(user_id=current_user.id, completed=False).filter(
        Task.created_at >= start_of_week).count()

    return jsonify({'completed_count': completed_tasks_count, 'ongoing_count': ongoing_tasks_count})

if __name__ == '__main__':
    app.run(debug=True)