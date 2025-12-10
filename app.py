from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import re
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import secrets
from functools import wraps
from flask import jsonify, abort


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.context_processor
def utility_processor():
    def get_category_name(category):
        category_names = {
            'general': 'Общее',
            'technology': 'Технологии', 
            'science': 'Наука',
            'sports': 'Спорт',
            'entertainment': 'Развлечения',
            'politics': 'Политика',
            'business': 'Бизнес',
            'health': 'Здоровье'
        }
        return category_names.get(category, 'Неизвестная категория')
    return dict(get_category_name=get_category_name)

@app.route('/')
def home():
    articles = Article.query.order_by(Article.created_date.desc()).limit(5).all()
    
    today = datetime.now().date()
    for article in articles:
        article.is_today = article.created_date.date() == today
    
    return render_template('home.html', articles=articles, today=today)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    hashed_password = db.Column(db.String(200), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    articles = db.relationship('Article', backref='author', lazy=True)
    
    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
    
    def __repr__(self):
        return f'<User {self.name}>'

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Article {self.title}>'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    article = db.relationship('Article', backref=db.backref('comments', lazy=True))
    
    def __repr__(self):
        return f'<Comment {self.text[:20]}...>'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему чтобы получить доступ к этой странице', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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
        
        flash('Спасибо ваше сообщение отправлено.')
        return render_template('feedback.html', submitted_data=form_data)
    
    return render_template('feedback.html')

@app.route('/news/<int:id>')
def article_detail(id):
    article = Article.query.get_or_404(id)
    return render_template('article_detail.html', article=article)

@app.route('/create-article', methods=['GET', 'POST'])
@login_required
def create_article():
    if request.method == 'POST':

        title = request.form.get('title', '').strip()
        text = request.form.get('text', '').strip()
        category = request.form.get('category', 'general').strip()
        

        if not title or not text:
            flash('Заполните все поля', 'danger')
            return render_template('create_article.html')
        
        user = User.query.first()
        if not user:
            flash('Нет пользователей в базе', 'danger')
            return render_template('create_article.html')
        
        new_article = Article(
            title=title,
            text=text,
            category=category,
            user_id=user.id
        )
        
        db.session.add(new_article)
        db.session.commit()
        
        flash('Статья успешно создана', 'success')
        return redirect(url_for('articles_list'))
    
    return render_template('create_article.html')


@app.route('/edit-article/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_article(id):
    article = Article.query.get_or_404(id)
    
    if request.method == 'POST':
        
        article.title = request.form.get('title', '').strip()
        article.text = request.form.get('text', '').strip()
        article.category = request.form.get('category', 'general').strip()  
        
        if not article.title or not article.text:
            flash('Заполните вс поля', 'danger')
            return render_template('edit_article.html', article=article)
        
        db.session.commit()
        
        flash('Статья успешно обновлена', 'success')
        return redirect(url_for('article_detail', id=article.id))
    
    return render_template('edit_article.html', article=article)

@app.route('/delete-article/<int:id>', methods=['POST'])
def delete_article(id):
    article = Article.query.get_or_404(id)
    
    db.session.delete(article)
    db.session.commit()
    
    flash('СТАТЬЯ УСПЕШНО УНИЧТОЖЕНАААА', 'success')
    return redirect(url_for('articles_list'))


@app.route('/articles')
def articles_list():
    articles = Article.query.order_by(Article.created_date.desc()).all()
    return render_template('articles_list.html', articles=articles)

@app.route('/articles/<category>')
def articles_by_category(category):
    valid_categories = ['general', 'technology', 'science', 'sports', 'entertainment', 'politics', 'business', 'health']
    
    if category not in valid_categories:
        flash(f'Категория "{category}" не найдена', 'danger') # не успевает отобразиться, ну и ладно
        return redirect(url_for('articles_list'))
    
    articles = Article.query.filter_by(category=category)\
.order_by(Article.created_date.desc()).all()
    
    return render_template('articles_by_category.html', articles=articles, category=category, category_name=get_category_name(category))

@app.route('/article/<int:article_id>/add-comment', methods=['GET', 'POST'])
def add_comment(article_id):
    article = Article.query.get_or_404(article_id)
    
    if request.method == 'POST':
        author_name = request.form.get('author_name', '').strip()
        text = request.form.get('text', '').strip()
        
        errors = {}
        form_data = {'author_name': author_name, 'text': text}
        
        if not author_name:
            errors['author_name'] = 'Имя обязательно для заполнения'
        elif len(author_name) < 2:
            errors['author_name'] = 'Имя должно содержать хотя бы 2 символа'
            
        if not text:
            errors['text'] = 'Текст комментария обязателен'
        elif len(text) > 1000:
            errors['text'] = 'Комментарий не должен превышать 1000 символов'
        
        if errors:
            return render_template('add_comment.html', article=article, errors=errors, form_data=form_data)
        
        new_comment = Comment(
            text=text,
            author_name=author_name,
            article_id=article.id
        )
        
        db.session.add(new_comment)
        db.session.commit()
        
        flash('Комментарий успешно добавлен!', 'success')
        return redirect(url_for('article_detail', id=article.id))
    
    return render_template('add_comment.html', article=article)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        errors = {}
        form_data = {'name': name, 'email': email}
        
        if not name:
            errors['name'] = 'Имя обязательно для заполнения'
        elif len(name) < 2:
            errors['name'] = 'Имя должно содержать хотя бы 2 символа'
        
        if not email:
            errors['email'] = 'Email обязателен для заполнения'
        elif User.query.filter_by(email=email).first():
            errors['email'] = 'Пользователь с таким email уже существует'
        
        if not password:
            errors['password'] = 'Пароль обязателен для заполнения'
        elif len(password) < 6:
            errors['password'] = 'Пароль должен содержать хотя бы 6 символов'
        
        if not confirm_password:
            errors['confirm_password'] = 'Подтверждение пароля обязательно'
        elif password != confirm_password:
            errors['confirm_password'] = 'Пароли не совпадают'
        
        if errors:
            return render_template('register.html', errors=errors, form_data=form_data)
        
        new_user = User(name=name, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        errors = {}
        form_data = {'email': email}
        
        if not email:
            errors['email'] = 'Email обязателен для заполнения'
        
        if not password:
            errors['password'] = 'Пароль обязателен для заполнения'
        
        if errors:
            return render_template('login.html', errors=errors, form_data=form_data)
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Неверный email или пароль', 'danger')
            return render_template('login.html', form_data=form_data)
        
        session['user_id'] = user.id
        session['user_name'] = user.name
        
        flash(f'Добро пожаловать, {user.name}!', 'success')
        return redirect(url_for('home'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('home'))

def get_category_name(category):
    category_names = {
        'general': 'Общее',
        'technology': 'Технологии',
        'science': 'Наука',
        'sports': 'Спорт',
        'entertainment': 'Развлечения',
        'politics': 'Политика',
        'business': 'Бизнес',
        'health': 'Здоровье'
    }
    return category_names.get(category, 'Неизвестная категория')


with app.app_context():
    db.create_all()
    
    if not User.query.first():
        test_user = User(name='Первый пользователь', email='tester@dvfu.ru')
        test_user.set_password('password123')
        db.session.add(test_user)
        db.session.commit()
        print("Создан тестовый пользователь: tester@dvfu.ru / password123")

# API МАРШРУТЫ
@app.route('/api/articles', methods=['GET'])
def api_get_articles():
    articles = Article.query.order_by(Article.created_date.desc()).all()
    
    articles_list = []
    for article in articles:
        articles_list.append({
            'id': article.id,
            'title': article.title,
            'text': article.text[:200] + '...' if len(article.text) > 200 else article.text,
            'category': article.category,
            'created_date': article.created_date.isoformat(),
            'author': {
                'id': article.author.id,
                'name': article.author.name,
                'email': article.author.email
            },
            'comments_count': len(article.comments)
        })
    
    return jsonify({
        'success': True,
        'count': len(articles_list),
        'articles': articles_list
    })


@app.route('/api/articles/<int:id>', methods=['GET'])
def api_get_article(id):
    article = Article.query.get(id)
    
    if not article:
        abort(404, description=f"Статья с ID {id} не найдена")
    
    article_data = {
        'id': article.id,
        'title': article.title,
        'text': article.text,
        'category': article.category,
        'created_date': article.created_date.isoformat(),
        'author': {
            'id': article.author.id,
            'name': article.author.name,
            'email': article.author.email
        },
        'comments': [
            {
                'id': comment.id,
                'text': comment.text,
                'author_name': comment.author_name,
                'created_date': comment.created_date.isoformat()
            }
            for comment in article.comments
        ]
    }
    
    return jsonify({
        'success': True,
        'article': article_data
    })


if __name__ == '__main__':
    app.run(debug=True)