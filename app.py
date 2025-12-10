from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import re


app = Flask(__name__)
app.secret_key = 'djjjjejejej1929731293' #только для flash сообщений 

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.route('/')
def home():
    articles = [
        {'id': 1, 'title': 'ЗАГОЛОВОК СТАТЬИ НОМЕР ОДИН', 'date': datetime.now().date()},
        {'id': 2, 'title': 'ЗАГОЛОВОК ДЛЯ ВТОРОЙ СТАТЬИ НА САЙТЕ', 'date': (datetime.now() - timedelta(days=1)).date()},
        {'id': 3, 'title': 'ТРЕТИЙ ЗАГОЛОВОК ДЛЯ СТАТЬИ', 'date': datetime.now().date()},
        {'id': 4, 'title': 'СТАТЬЯ НОМЕР ЧЕТЫРЕ И ЕЕ ЗАГОЛОВОК', 'date': (datetime.now() - timedelta(days=3)).date()},
        {'id': 5, 'title': 'ПОСЛЕДНЯЯ - ПЯТАЯ СТАТЬЯ', 'date': (datetime.now() - timedelta(days=2)).date()}
    ]
    
    today = datetime.now().date()
    for article in articles:
        article['is_today'] = article['date'] == today
    
    return render_template('home.html', articles=articles, today=today)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    hashed_password = db.Column(db.String(200), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    articles = db.relationship('Article', backref='author', lazy=True)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Article {self.title}>'

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        
        errors = {}
        form_data = {'name': name, 'email': email, 'message': message}
        
        if not name:
            errors['name'] = 'Имя обязательно для заполнения'
        elif len(name) < 2:
            errors['name'] = 'Имя должно содержать минимум 2 символа'
        
        if not email:
            errors['email'] = 'Email обязателен для заполнения'
        else:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$' #шаблон для email
            if not re.match(email_pattern, email):
                errors['email'] = 'Введите корректный email адрес'
        
        if not message:
            errors['message'] = 'Сообщение обязательно для заполнения'
        elif len(message) < 10:
            errors['message'] = 'Сообщение должно содержать минимум 10 символов'
        
        if errors:
            return render_template('feedback.html', error=errors, form_data=form_data)
        
        flash('Спасибо! Ваше сообщение отправлено.')
        return render_template('feedback.html', submitted_data=form_data)
    
    return render_template('feedback.html')

@app.route('/news/<int:id>')
def news_detail(id):
    return f"Статья {id}"

with app.app_context():
    db.create_all()
    
    if not User.query.first():
        test_user = User(
            name='Первый пользователь',
            email='tester@dvfu.ru',
            hashed_password='password123'
        )
        db.session.add(test_user)
        db.session.commit()
        print("Создан тестовый пользователь")

if __name__ == '__main__':
    app.run(debug=True)