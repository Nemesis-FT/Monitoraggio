from flask import Flask, session, url_for, redirect, request, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import bcrypt
from datetime import datetime, date, timedelta
import os
import random
import string

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
    nome = db.Column(db.String)

    def __init__(self, username, passwd, nome):
        self.username = username
        self.passwd = passwd
        self.nome = nome

    def __repr__(self):
        return "{}-{}-{}".format(self.uid, self.username, self.passwd)


class Laboratorio(db.Model):
    __tablename__ = 'laboratorio'
    lid = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False, unique=True)
    sede = db.Column(db.String, nullable=True)
    strumenti = db.relationship('Strumento', backref='laboratorio', lazy=True)
    bot = db.relationship("Bot", back_populates="laboratorio")
    log = db.relationship("Log", back_populates="laboratorio")

    def __init__(self, nome, sede):
        self.nome = nome
        self.sede = sede

    def __repr__(self):
        return "{}, {}".format(self.lid, self.nome)


class Strumento(db.Model):
    __tablename__ = 'strumento'
    sid = db.Column(db.Integer, primary_key=True)
    identificatore_esterno = db.Column(db.Integer, nullable=False)
    nome = db.Column(db.String, unique=True, nullable=False)
    marca = db.Column(db.String, nullable=True)
    modello = db.Column(db.String, nullable=True)
    proto = db.Column(db.Integer, nullable=True)
    valore_massimo = db.Column(db.Float, nullable=False)
    valore_minimo_allerta = db.Column(db.Float, nullable=False)
    valore_massimo_allerta = db.Column(db.Float, nullable=False)
    laboratorio_id = db.Column(db.Integer, db.ForeignKey('laboratorio.lid'), nullable=False)

    def __init__(self, idee, nome, marca, modello, proto, fs, valore_minimo_allerta,
                 valore_massimo_allerta, laboratorio_id):
        self.identificatore_esterno = idee
        self.nome = nome
        self.marca = marca
        self.modello = modello
        self.proto = proto
        self.valore_minimo_allerta = valore_minimo_allerta
        self.valore_massimo_allerta = valore_massimo_allerta
        self.laboratorio_id = laboratorio_id
        self.valore_massimo = fs

    def __repr__(self):
        return "{}-{}-{}".format(self.sid, self.identificatore_esterno, self.nome)


class Bot(db.Model):
    __tablename__ = 'bot'
    bid = db.Column(db.Integer, primary_key=True)
    laboratorio_id = db.Column(db.Integer, db.ForeignKey('laboratorio.lid'))
    laboratorio = db.relationship("Laboratorio", back_populates="bot")
    token = db.Column(db.String, nullable=False)
    nome = db.Column(db.String)

    def __init__(self, token, nome, laboratorio):
        self.token = token
        self.nome = nome
        self.laboratorio_id = laboratorio

    def __repr__(self):
        return "{}-{}-{}".format(self.bid, self.nome, self.token)


class Log(db.Model):
    __tablename__ = "log"
    loid = db.Column(db.Integer, primary_key=True)
    livello = db.Column(db.Integer, nullable=False)
    error = db.Column(db.String, nullable=False)
    data = db.Column(db.DateTime, nullable=True)  # Solo per scopo di test
    strumento_id = db.Column(db.Integer, nullable=False)
    strumName = db.Column(db.String, nullable=False)
    laboratorio_id = db.Column(db.Integer, db.ForeignKey("laboratorio.lid"))
    laboratorio = db.relationship("Laboratorio", back_populates="log")

    def __init__(self, tipo, error, data, laboratorio_id, strumento_id, strumName):
        self.livello = tipo
        self.error = error
        self.data = data
        self.laboratorio_id = laboratorio_id
        self.strumento_id = strumento_id
        self.strumName = strumName

    def __repr__(self):
        return "{}-{}-{}".format(self.loid, self.laboratorio_id, self.data)


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


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


@app.route("/monitoraggio", methods=["GET", "POST"])
def page_monitoraggio():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    if request.method == "GET":
        logs = Log.query.join(Laboratorio).order_by(Log.data.desc()).limit(100).all()
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        return render_template("monitoraggio.htm", utente=utente, laboratori=laboratori, logs=logs)


@app.route("/strumquery", methods=['POST']) # Queste funzioni sono orrende.
def page_strumquery():
    if 'username' not in session or 'username' is None:
        abort(403)
    print(request.form['lab'])
    risultato = Strumento.query.filter_by(laboratorio_id=request.form['lab']).all()
    msg = ""
    for entita in risultato:
        msg = msg + "<a class=\"dropdown-item\" onclick=\"strumsense(" + str(entita.sid) + ")\">" + entita.nome + "</a>\n"
    return msg


@app.route("/logquery", methods=['POST'])
def page_logquery():
    if 'username' not in session or 'username' is None:
        abort(403)
    risultato = Log.query.filter_by(strumento_id=request.form['strum']).all()
    msg = ""
    for entita in risultato:
        msg = msg + """
        <tr>
                <td>{}</td>
                <td>{}</td>
                <td> </td>
        </tr>
        """.format(entita.data, entita.error)
    return msg


@app.route("/login", methods=['GET', 'POST'])
def page_login():
    if request.method == "GET":
        return render_template("login.htm")
    else:
        if login(request.form['username'], request.form['password']):
            session['username'] = request.form['username']
            return redirect(url_for('page_monitoraggio'))
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
            rete = Strumento(0,"Rete","Oggetto dummy",1,2,0,0,0,nuovolaboratorio.lid)
            db.session.add(rete)
            db.session.commit()
            return redirect(url_for('page_dashboard'))


@app.route("/list_laboratorio")
def page_laboratorio_list():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        return render_template("/laboratorio/list.htm", utente=utente, laboratori=laboratori)


@app.route("/details_laboratorio/<int:lid>")
def page_laboratorio_details(lid):
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        entita = Laboratorio.query.get_or_404(lid)
        strumenti = Laboratorio.query.filter_by(lid=lid).join(Strumento).all()
        statorete = Log.query.filter_by(laboratorio_id=lid, strumento_id=0).order_by(Log.data.desc()).first()
        logs = Laboratorio.query.filter_by(lid=lid).join(Log).all()  # TODO: Da rimuovoere
        return render_template("/laboratorio/details.htm", utente=utente, laboratori=laboratori, strumenti=strumenti,
                               logs=logs, entita=entita, statorete=statorete)


@app.route("/add_strumento", methods=['GET', 'POST'])
def page_strumento_add():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        if request.method == 'GET':
            utente = find_user(session['username'])
            laboratori = Laboratorio.query.all()
            return render_template("/strumenti/add.htm", utente=utente, laboratori=laboratori)
        else:
            nuovo_strumento = Strumento(request.form['iden'], request.form['nome'], request.form['marca'],
                                        request.form['modello'], request.form['proto'], request.form['fs'],
                                        request.form['vma'], request.form['vMa'],
                                        request.form['lab'])
            db.session.add(nuovo_strumento)
            db.session.commit()
            return redirect(url_for('page_dashboard'))


@app.route("/details_strumento/<int:sid>", methods=['GET'])
def page_strumento_details(sid):
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        if request.method == 'GET':
            strumento = Strumento.query.filter_by(sid=sid).join(Laboratorio).first()
            utente = find_user(session['username'])
            laboratori = Laboratorio.query.all()
            return render_template("/strumenti/details.htm", utente=utente, laboratori=laboratori, strumento=strumento)


@app.route("/list_strumento/<int:lid>", methods=["GET"])
def page_strumento_lista(lid):
    if 'username' not in session or 'username' is None:
        abort(403)
    else:
        strumenti = Strumento.query.filter_by(laboratorio_id=lid).all()
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        return render_template("/strumenti/list.htm", utente=utente, laboratori=laboratori, strumenti=strumenti)


@app.route('/mod_strumento/<int:sid>', methods=["GET", "POST"])
def page_mod_strumento(sid):
    if 'username' not in session:
        abort(403)
    else:
        if request.method == "GET":
            utente = find_user(session['username'])
            laboratori = Laboratorio.query.all()
            entita = Strumento.query.get_or_404(sid)
            return render_template("/strumenti/mod.htm", utente=utente, laboratori=laboratori, entita=entita)
        else:
            entita = Strumento.query.get_or_404(sid)
            entita.identificatore_esterno = request.form['eid']
            entita.valore_minimo_allerta = request.form['vmin']
            entita.valore_massimo_allerta = request.form['vmax']
            db.session.commit()
            return redirect(url_for('page_dashboard'))



@app.route("/list_log/<int:valore>/<int:mode>")
def page_log_list(valore, mode):
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        if mode == 0:  # ricerca per strumento
            logs = Log.query.filter_by(strumento_id=valore).all()
        else:
            logs = Log.query.filter_by(laboratorio_id=valore).all()
        return render_template("/log/list.htm", utente=utente, laboratori=laboratori, logs=logs)


@app.route("/list_bot")
def page_bot_list():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        bots = Bot.query.join(Laboratorio).all()
        return render_template("/bot/list.htm", utente=utente, laboratori=laboratori, bots=bots)


@app.route("/add_bot", methods=['GET', 'POST'])
def page_bot_add():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        if request.method == 'GET':
            utente = find_user(session['username'])
            laboratori = Laboratorio.query.all()
            return render_template("/bot/add.htm", utente=utente, laboratori=laboratori)
        else:
            token = id_generator()
            nuovo_bot = Bot(token, request.form['nome'], request.form['lab'])
            db.session.add(nuovo_bot)
            db.session.commit()
            return redirect(url_for('page_dashboard'))


@app.route('/ricerca', methods=["GET", "POST"])  # Funzione scritta da Stefano Pigozzi nel progetto Estus
def page_ricerca():
    if 'username' not in session:
        abort(403)
    else:
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        if request.method == 'GET':
            return render_template("query.htm", utente=utente, laboratori=laboratori)
        else:
            try:
                result = db.engine.execute("SELECT " + request.form["query"] + ";")
            except Exception as e:
                return render_template("query.htm", query=request.form["query"], error=repr(e), utente=utente, laboratori=laboratori)
            return render_template("query.htm", query=request.form["query"], result=result, utente=utente, laboratori=laboratori)


@app.route('/recv_bot', methods=["POST"])
def page_recv_bot():
    labId = request.form['labId']
    token = request.form['token']
    strum_id = request.form['strumId']
    message = request.form['message']
    type = request.form['type']
    if Bot.query.filter_by(laboratorio_id=labId, token=token).all():
        strumento = Strumento.query.filter_by(identificatore_esterno=strum_id, laboratorio_id=labId).first()
        if strumento:
            nuovolog = Log(type, message, datetime.today(), labId, strumento.sid, strumento.nome)
            db.session.add(nuovolog)
            db.session.commit()
            return "200 - QUERY OK, DATA INSERT SUCCESSFUL."
        else:
            abort(404)
    else:
        abort(403)


@app.route('/add_user', methods=["GET", "POST"])
def page_add_user():
    if 'username' not in session:
        abort(403)
    else:
        if request.method == "GET":
            utente = find_user(session['username'])
            laboratori = Laboratorio.query.all()
            return render_template("/user/add.htm", utente=utente, laboratori=laboratori)
        else:
            cenere = bcrypt.hashpw(bytes(request.form['password'], encoding="utf-8"), bcrypt.gensalt())
            nuovo_utente = User(request.form['email'], cenere, request.form['nome'])
            db.session.add(nuovo_utente)
            db.session.commit()
            return redirect(url_for('page_dashboard'))


@app.route('/list_user', methods=["GET"])
def page_list_user():
    if 'username' not in session:
        abort(403)
    else:
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        utenze = User.query.all()
        return render_template("/user/list.htm", utente=utente, laboratori=laboratori, utenze=utenze)


@app.route('/mod_user/<int:uid>', methods=["GET", "POST"])
def page_mod_user(uid):
    if 'username' not in session:
        abort(403)
    else:
        if request.method == "GET":
            utente = find_user(session['username'])
            laboratori = Laboratorio.query.all()
            entita = User.query.get_or_404(uid)
            return render_template("/user/mod.htm", utente=utente, laboratori=laboratori, entita=entita)
        else:
            entita = User.query.get_or_404(uid)
            cenere = bcrypt.hashpw(bytes(request.form['password'], encoding="utf-8"), bcrypt.gensalt())
            entita.passwd = cenere
            entita.nome = request.form['nome']
            entita.username = request.form['email']
            db.session.commit()
            return redirect(url_for('page_list_user'))


if __name__ == "__main__":
    # Se non esiste il database viene creato
    # if not os.path.isfile("db.sqlite"):
    #    db.create_all()
    #    p = bytes("password", encoding="utf-8")
    #    cenere = bcrypt.hashpw(p, bcrypt.gensalt())
    #    admin = User("admin@admin.com", cenere, "Amministratore")
    #    db.session.add(admin)
    #    db.session.commit()
    app.run(host="0.0.0.0", debug=False)
