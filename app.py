from flask import Flask, render_template, request, flash, redirect, url_for
import re

app = Flask(__name__)
app.secret_key = 'djjjjejejej1929731293' #только для flash сообщений 

@app.route('/')
def home():
    return render_template('home.html')

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
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$' #проверка на верный вид email
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

if __name__ == '__main__':
    app.run(debug=True)