from flask import Flask, session, url_for, redirect, request, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import bcrypt
from datetime import datetime, date, timedelta
import os

app = Flask(__name__)
app.secret_key = "sgozzoli"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Classi del database


class User(db.Model):
    __tablename__ = 'user'
    uid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    passwd = db.Column(db.LargeBinary, nullable=False)

    def __init__(self, username, passwd):
        self.username = username
        self.passwd = passwd

    def __repr__(self):
        return "{}-{}-{}".format(self.uid, self.username, self.passwd)


class Laboratorio(db.Model):
    __tablename__ = 'laboratorio'
    lid = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False, unique=True)
    sede = db.Column(db.String, nullable=True)
    strumenti = db.relationship('Strumento', backref='laboratorio', lazy=True)
    bot = db.relationship("Bot", back_populates="laboratorio")

    def __init__(self, nome, sede):
        self.nome = nome
        self.sede = sede

    def __repr__(self):
        return "{}, {}".format(self.lid, self.nome)


class Strumento(db.Model):
    __tablename__ = 'strumento'
    sid = db.Column(db.Integer, primary_key=True)
    identificatore_esterno = db.Column(db.Integer, unique=True, nullable=False)
    nome = db.Column(db.String, unique=True, nullable=False)
    marca = db.Column(db.String, nullable=True)
    modello = db.Column(db.String, nullable=True)
    proto = db.Column(db.Integer, nullable=True)
    valore_massimo = db.Column(db.Float, nullable=False)
    valore_minimo_allerta = db.Column(db.Float, nullable=False)
    valore_massimo_allerta = db.Column(db.Float, nullable=False)
    laboratorio_id = db.Column(db.Integer, db.ForeignKey('laboratorio.lid'), nullable=False)
    log = db.relationship("Log")

    def __init__(self, idee, nome, marca, modello, proto, valore_massimo, valore_minimo_allerta, valore_massimo_allerta):
        self.identificatore_esterno = idee
        self.nome = nome
        self.marca = marca
        self.modello = modello
        self.proto = proto
        self.valore_massimo = valore_massimo
        self.valore_minimo_allerta = valore_minimo_allerta
        self.valore_massimo_allerta = valore_massimo_allerta

    def __repr__(self):
        return "{}-{}-{}".format(self.sid, self.identificatoreEsterno, self.nome)


class Bot(db.Model):
    __tablename__ = 'bot'
    bid = db.Column(db.Integer, primary_key=True)
    laboratorio_id = db.Column(db.Integer, db.ForeignKey('laboratorio.lid'))
    laboratorio = db.relationship("Laboratorio", back_populates="bot")
    token = db.Column(db.String, nullable=False)
    nome = db.Column(db.String)

    def __init__(self, token, nome):
        self.token = token
        self.nome = nome

    def __repr__(self):
        return "{}-{}-{}".format(self.bid, self.nome, self.token)


class Log(db.Model):
    __tablename__ = "log"
    lid = db.Column(db.Integer, primary_key=True)
    livello = db.Column(db.Integer, nullable=False)
    error = db.Column(db.Integer, nullable=False)
    data = db.Column(db.DateTime, nullable=False)
    strumento_id = db.Column(db.Integer, db.ForeignKey("strumento.sid"))

    def __init__(self, livello, error, data):
        self.livello = livello
        self.error = error
        self.data = data

    def __repr__(self):
        return "{}-{}-{}".format(self.lid, self.strumento_id, self.data)


def login(username, password):
    user = User.query.filter_by(username=username).first()
    try:
        return bcrypt.checkpw(bytes(password, encoding="utf-8"), user.passwd)
    except AttributeError:
        # Se non esiste l'Utente
        return False


def find_user(username):
    return User.query.filter_by(username=username).first()


@app.route("/")
def page_home():
    if 'username' not in session:
        return redirect(url_for('page_login'))
    else:
        session.pop('username')
        return redirect(url_for('page_login'))


@app.route("/login", methods=['GET', 'POST'])
def page_login():
    if request.method == "GET":
        return render_template("login.htm")
    else:
        if login(request.form['username'], request.form['password']):
            session['username'] = request.form['username']
            return redirect(url_for('page_dashboard'))
        else:
            abort(403)


@app.route("/dashboard", methods=['GET'])
def page_dashboard():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        return render_template("dashboard.htm", utente=utente, laboratori=laboratori)


@app.route("/add_laboratorio", methods=['GET', 'POST'])
def page_laboratorio_add():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        if request.method == "GET":
            utente = find_user(session['username'])
            laboratori = Laboratorio.query.all()
            return render_template("/laboratorio/add.htm", utente=utente, laboratori=laboratori)
        else:
            nuovolaboratorio = Laboratorio(request.form['nome'], request.form['sede'])
            db.session.add(nuovolaboratorio)
            db.session.commit()
            return redirect(url_for('page_dashboard'))


if __name__ == "__main__":
    # Se non esiste il database viene creato
    #if not os.path.isfile("db.sqlite"):
    #    db.create_all()
    #    p = bytes("password", encoding="utf-8")
    #    cenere = bcrypt.hashpw(p, bcrypt.gensalt())
    #    admin = User("admin@admin.com", cenere)
    #    db.session.add(admin)
    #    db.session.commit()
    app.run()
