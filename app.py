from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Добро пожаловать в Новостной Блог!'

@app.route('/about')
def about():
    return 'О проекте: Это новостной блог с последними статьями и событиями.'

@app.route('/contact')
def contact():
    return 'Контакты: Email - abcde@newsblog.com, Телефон - +7 123 456 78 90'

if __name__ == '__main__':
    app.run(debug=True)