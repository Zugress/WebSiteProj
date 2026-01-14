from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import re
from jwt_auth import JWTManager, jwt_required, admin_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import secrets
from functools import wraps
from flask import jsonify, abort


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.ensure_ascii = False

# Middleware
@app.before_request
def check_jwt_for_api():
    """Проверяет JWT токен для API маршрутов"""
    if request.path.startswith('/api/'):
        public_routes = ['/auth/login', '/auth/refresh', '/auth/register']
        if request.path in public_routes:
            return
        
        if request.method == 'GET' and ('/articles' in request.path or '/comments' in request.path):
            return
        
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header is missing'}), 401
        
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            return jsonify({'error': 'Bearer token malformed'}), 401
        
        payload = JWTManager.verify_access_token(auth_token)
        if not payload or 'error' in payload:
            error_msg = payload.get('error') if payload and isinstance(payload, dict) else 'Invalid token'
            return jsonify({'error': error_msg}), 401
        
        request.user_id = payload['user_id']
        request.username = payload['username']
        
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
    
    refresh_tokens = db.Column(db.Text, default='[]')
    
    articles = db.relationship('Article', backref='author', lazy=True)
    
    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
    
    def add_refresh_token(self, token):
        import json
        tokens = json.loads(self.refresh_tokens)
        tokens.append(token)
        self.refresh_tokens = json.dumps(tokens[-5:])
    
    def has_refresh_token(self, token):
        import json
        tokens = json.loads(self.refresh_tokens)
        return token in tokens
    
    def remove_refresh_token(self, token):
        import json
        tokens = json.loads(self.refresh_tokens)
        if token in tokens:
            tokens.remove(token)
            self.refresh_tokens = json.dumps(tokens)
    
    def __repr__(self):
        return f'<User {self.name}>'
    
    @staticmethod
    def authenticate(email, password):
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            return user
        return None

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
    
    article = db.relationship('Article', backref=db.backref('comments', lazy=True, cascade='all, delete-orphan'))
    
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
    """GET /api/articles список всех статей с фильтрацией и сортировкой"""
    
    category = request.args.get('category')
    sort_by = request.args.get('sort', 'date')  
    limit = request.args.get('limit', type=int)  
    
    query = Article.query
    
    if category:
        valid_categories = ['general', 'technology', 'science', 'sports', 'entertainment', 'politics', 'business', 'health']
        if category in valid_categories:
            query = query.filter_by(category=category)
        else:
            return jsonify({
                'success': False,
                'error': f'Категория "{category}" не найдена. Доступные: {", ".join(valid_categories)}'
            }), 400
    
    if sort_by == 'date':
        query = query.order_by(Article.created_date.desc())  
    elif sort_by == 'date_asc':
        query = query.order_by(Article.created_date.asc())   
    elif sort_by == 'title':
        query = query.order_by(Article.title.asc())          
    else:
        return jsonify({
            'success': False,
            'error': f'Неправильный параметр сортировки. Доступные: date, date_asc, title'
        }), 400
    
    if limit and limit > 0:
        query = query.limit(limit)
    
    articles = query.all()
    
    articles_list = []
    for article in articles:
        articles_list.append({
            'id': article.id,
            'title': article.title,
            'text': article.text[:200] + '...' if len(article.text) > 200 else article.text,
            'category': article.category,
            'category_name': get_category_name(article.category),
            'created_date': article.created_date.isoformat(),
            'author': {
                'id': article.author.id,
                'name': article.author.name
            },
            'comments_count': len(article.comments)
        })
    
    return jsonify({
        'success': True,
        'count': len(articles_list),
        'filters': {
            'category': category if category else 'all',
            'sort_by': sort_by,
            'limit': limit if limit else 'none'
        },
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


@app.route('/api/articles', methods=['POST'])
@jwt_required
def api_create_article():
    """POST /api/articles создать статью через API"""
    
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type должен быть application/json'
        }), 400
    
    data = request.get_json()
    
    errors = []
    
    if not data.get('title'):
        errors.append('Поле "title" обязательно')
    elif len(data['title']) < 3:
        errors.append('Заголовок должен содержать минимум 3 символа')
    
    if not data.get('text'):
        errors.append('Поле "text" обязательно')
    elif len(data['text']) < 10:
        errors.append('Текст должен содержать минимум 10 символов')
    
    category = data.get('category', 'general')
    valid_categories = ['general', 'technology', 'science', 'sports', 
                       'entertainment', 'politics', 'business', 'health']
    if category not in valid_categories:
        category = 'general'
    
    if errors:
        return jsonify({
            'success': False,
            'errors': errors
        }), 400
    
    user_id = getattr(request, 'user_id', None)
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'Пользователь не авторизован'
        }), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({
            'success': False,
            'error': 'Пользователь не найден'
        }), 404
    
    new_article = Article(
        title=data['title'],
        text=data['text'],
        category=category,
        user_id=user.id
    )
    
    db.session.add(new_article)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Статья успешно создана',
        'article': {
            'id': new_article.id,
            'title': new_article.title,
            'category': new_article.category,
            'created_date': new_article.created_date.isoformat()
        }
    }), 201  


@app.route('/api/articles/<int:id>', methods=['PUT'])
@jwt_required
def api_update_article(id):
    """PUT /api/articles/<id> обновить статью через API"""
    
    article = Article.query.get(id)
    if not article:
        return jsonify({
            'success': False,
            'error': f'Статья с ID {id} не найдена'
        }), 404
    
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type должен быть application/json'
        }), 400
    
    data = request.get_json()
    
    errors = []
    
    if 'title' in data:
        if len(data['title']) < 3:
            errors.append('Заголовок должен содержать минимум 3 символа')
        else:
            article.title = data['title']
    
    if 'text' in data:
        if len(data['text']) < 10:
            errors.append('Текст должен содержать минимум 10 символов')
        else:
            article.text = data['text']
    
    if 'category' in data:
        valid_categories = ['general', 'technology', 'science', 'sports', 
                           'entertainment', 'politics', 'business', 'health']
        if data['category'] in valid_categories:
            article.category = data['category']
        else:
            errors.append('Некорректная категория')
    
    if errors:
        return jsonify({
            'success': False,
            'errors': errors
        }), 400
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Статья успешно обновлена',
        'article': {
            'id': article.id,
            'title': article.title,
            'text': article.text[:100] + '...',
            'category': article.category,
            'updated': True
        }
    })

@app.route('/api/articles/category/<category>', methods=['GET'])
def api_get_articles_by_category(category):
    """GET /api/articles/category/<category> фильтр по категории"""
    
    valid_categories = ['general', 'technology', 'science', 'sports', 'entertainment', 'politics', 'business', 'health']
    
    if category not in valid_categories:
        return jsonify({
            'success': False,
            'error': f'Категория "{category}" не найдена',
            'available_categories': valid_categories
        }), 404
    
    articles = Article.query.filter_by(category=category)\
               .order_by(Article.created_date.desc()).all()
    
    articles_list = []
    for article in articles:
        articles_list.append({
            'id': article.id,
            'title': article.title,
            'text': article.text[:150] + '...',
            'category': article.category,
            'created_date': article.created_date.isoformat(),
            'author_name': article.author.name
        })
    
    return jsonify({
        'success': True,
        'category': category,
        'category_name': get_category_name(category),
        'count': len(articles_list),
        'articles': articles_list
    })
    
@app.route('/api/articles/<int:id>', methods=['DELETE'])
@jwt_required
def api_delete_article(id):
    """DELETE /api/articles/<id> удалить статью через API"""
    
    article = Article.query.get(id)
    if not article:
        return jsonify({
            'success': False,
            'error': f'Статья с ID {id} не найдена'
        }), 404
    
    article_data = {
        'id': article.id,
        'title': article.title
    }
    
    db.session.delete(article)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Статья успешно удалена',
        'deleted_article': article_data
    })
    
@app.route('/api/comments', methods=['GET'])
def api_get_comments():
    """GET /api/comments список всех комментариев"""
    
    article_id = request.args.get('article_id', type=int)
    
    query = Comment.query
    
    if article_id:
        query = query.filter_by(article_id=article_id)
    
    query = query.order_by(Comment.created_date.desc())
    
    comments = query.all()
    
    comments_list = []
    for comment in comments:
        comments_list.append({
            'id': comment.id,
            'text': comment.text,
            'author_name': comment.author_name,
            'created_date': comment.created_date.isoformat(),
            'article': {
                'id': comment.article.id,
                'title': comment.article.title[:50] + '...'
            }
        })
    
    return jsonify({
        'success': True,
        'count': len(comments_list),
        'filters': {
            'article_id': article_id if article_id else 'all'
        },
        'comments': comments_list
    })
    
@app.route('/api/comments/<int:id>', methods=['GET'])
def api_get_comment(id):
    """GET /api/comments/<id> комментарий по ID"""
    
    comment = Comment.query.get(id)
    
    if not comment:
        return jsonify({
            'success': False,
            'error': f'Комментарий с ID {id} не найден'
        }), 404
    
    comment_data = {
        'id': comment.id,
        'text': comment.text,
        'author_name': comment.author_name,
        'created_date': comment.created_date.isoformat(),
        'article': {
            'id': comment.article.id,
            'title': comment.article.title,
            'author': comment.article.author.name
        }
    }
    
    return jsonify({
        'success': True,
        'comment': comment_data
    })
    
    
@app.route('/api/comments', methods=['POST'])
@jwt_required
def api_create_comment():
    """POST /api/comments создать комментарий с валидацией"""
    
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type должен быть application/json'
        }), 400
    
    data = request.get_json()
    
    errors = []
    
    if not data.get('text'):
        errors.append('Поле "text" обязательно')
    elif len(data['text']) < 3:
        errors.append('Текст должен содержать минимум 3 символа')
    elif len(data['text']) > 1000:
        errors.append('Текст не должен превышать 1000 символов')
    
    if not data.get('author_name'):
        errors.append('Поле "author_name" обязательно')
    elif len(data['author_name']) < 2:
        errors.append('Имя должно содержать минимум 2 символа')
    
    if not data.get('article_id'):
        errors.append('Поле "article_id" обязательно')
    else:
        article = Article.query.get(data['article_id'])
        if not article:
            errors.append(f'Статья с ID {data["article_id"]} не найдена')
    
    if errors:
        return jsonify({
            'success': False,
            'errors': errors
        }), 400
    
    new_comment = Comment(
        text=data['text'],
        author_name=data['author_name'],
        article_id=data['article_id']
    )
    
    db.session.add(new_comment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Комментарий успешно создан',
        'comment': {
            'id': new_comment.id,
            'text': new_comment.text,
            'author_name': new_comment.author_name,
            'article_id': new_comment.article_id
        }
    }), 201
    
@app.route('/api/comments/<int:id>', methods=['PUT'])
@jwt_required
def api_update_comment(id):
    """PUT /api/comments/<id> обновить комментарий с валидацией"""
    
    comment = Comment.query.get(id)
    
    if not comment:
        return jsonify({
            'success': False,
            'error': f'Комментарий с ID {id} не найден'
        }), 404
    
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type должен быть application/json'
        }), 400
    
    data = request.get_json()
    
    errors = []
    
    if 'text' in data:
        if len(data['text']) < 3:
            errors.append('Текст должен содержать минимум 3 символа')
        elif len(data['text']) > 1000:
            errors.append('Текст не должен превышать 1000 символов')
        else:
            comment.text = data['text']
    
    if 'author_name' in data:
        if len(data['author_name']) < 2:
            errors.append('Имя должно содержать минимум 2 символа')
        else:
            comment.author_name = data['author_name']
    
    if errors:
        return jsonify({
            'success': False,
            'errors': errors
        }), 400
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Комментарий успешно обновлен',
        'comment': {
            'id': comment.id,
            'text': comment.text,
            'author_name': comment.author_name
        }
    }), 200
    
    
@app.route('/api/comments/<int:id>', methods=['DELETE'])
@jwt_required
def api_delete_comment(id):
    """DELETE /api/comments/<id> удалить комментарий"""
    
    comment = Comment.query.get(id)
    
    if not comment:
        return jsonify({
            'success': False,
            'error': f'Комментарий с ID {id} не найден'
        }), 404
    
    comment_data = {
        'id': comment.id,
        'text': comment.text[:50] + '...',
        'author_name': comment.author_name
    }
    
    db.session.delete(comment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Комментарий успешно удален',
        'deleted_comment': comment_data
    })
    
    
@app.route('/auth/login', methods=['POST'])
def auth_login():
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type должен быть application/json'
        }), 400
    
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if not email or not password:
        return jsonify({
            'success': False,
            'error': 'Email и пароль обязательны'
        }), 400
    
    user = User.authenticate(email, password)
    if not user:
        return jsonify({
            'success': False,
            'error': 'Неверный email или пароль'
        }), 401
    
    access_token = JWTManager.create_access_token(user.id, user.name)
    refresh_token = JWTManager.create_refresh_token(user.id, user.name)
    
    user.add_refresh_token(refresh_token)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'expires_in': 900,  
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email
        }
    }), 200

@app.route('/auth/refresh', methods=['POST'])
def auth_refresh():
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type должен быть application/json'
        }), 400
    
    data = request.get_json()
    refresh_token = data.get('refresh_token', '').strip()
    
    if not refresh_token:
        return jsonify({
            'success': False,
            'error': 'Refresh токен обязателен'
        }), 400
    
    payload = JWTManager.verify_refresh_token(refresh_token)
    if not payload:
        return jsonify({
            'success': False,
            'error': 'Невалидный или истекший refresh токен'
        }), 401
    
    user = User.query.get(payload['user_id'])
    if not user or not user.has_refresh_token(refresh_token):
        return jsonify({
            'success': False,
            'error': 'Refresh токен не найден'
        }), 401
    
    new_access_token = JWTManager.create_access_token(user.id, user.name)
    
    return jsonify({
        'success': True,
        'access_token': new_access_token,
        'token_type': 'bearer',
        'expires_in': 900
    }), 200

@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type должен быть application/json'
        }), 400
    
    data = request.get_json()
    refresh_token = data.get('refresh_token', '').strip()
    
    if not refresh_token:
        return jsonify({
            'success': False,
            'error': 'Refresh токен обязателен'
        }), 400
    
    payload = JWTManager.verify_refresh_token(refresh_token)
    if payload:
        user = User.query.get(payload['user_id'])
        if user:
            user.remove_refresh_token(refresh_token)
            db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Успешный выход из системы'
    }), 200
    
    
@app.route('/auth/register', methods=['POST'])
def auth_register():
    """Регистрация нового пользователя через API"""
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Content-Type должен быть application/json'
        }), 400
    
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    errors = []
    
    if not name:
        errors.append('Имя обязательно для заполнения')
    elif len(name) < 2:
        errors.append('Имя должно содержать хотя бы 2 символа')
    
    if not email:
        errors.append('Email обязателен для заполнения')
    elif User.query.filter_by(email=email).first():
        errors.append('Пользователь с таким email уже существует')
    
    if not password:
        errors.append('Пароль обязателен для заполнения')
    elif len(password) < 6:
        errors.append('Пароль должен содержать хотя бы 6 символов')
    
    if errors:
        return jsonify({
            'success': False,
            'errors': errors
        }), 400
    
    new_user = User(name=name, email=email)
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()
    
    # Эндпоинты возращающие токены
    access_token = JWTManager.create_access_token(new_user.id, new_user.name)
    refresh_token = JWTManager.create_refresh_token(new_user.id, new_user.name)
    
    new_user.add_refresh_token(refresh_token)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Регистрация успешна',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'expires_in': 900,
        'user': {
            'id': new_user.id,
            'name': new_user.name,
            'email': new_user.email
        }
    }), 201
    
    
if __name__ == '__main__':
    app.run(debug=True)