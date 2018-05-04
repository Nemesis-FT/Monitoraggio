from flask import Flask, session, url_for, redirect, request, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import bcrypt
from datetime import datetime, date, timedelta
import os
import random
import string
import requests

app = Flask(__name__)
app.secret_key = "dacambiare" #chiave per la cifratura dei cookie
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Classi del database, seguono le definizioni delle tabelle


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
    laboratorio_id = db.Column(db.Integer, db.ForeignKey('laboratorio.lid'), nullable=False)

    def __init__(self, idee, nome, marca, modello, proto, laboratorio_id):
        self.identificatore_esterno = idee
        self.nome = nome
        self.marca = marca
        self.modello = modello
        self.proto = proto
        self.laboratorio_id = laboratorio_id

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
    errorId = db.Column(db.String, nullable=False)
    error = db.Column(db.String, nullable=False)
    data = db.Column(db.DateTime, nullable=True)  # Solo per scopo di test
    strumento_id = db.Column(db.Integer, nullable=False)
    strumName = db.Column(db.String, nullable=False)
    laboratorio_id = db.Column(db.Integer, db.ForeignKey("laboratorio.lid"))
    laboratorio = db.relationship("Laboratorio", back_populates="log")

    def __init__(self, errorId, error, data, laboratorio_id, strumento_id, strumName):
        self.errorId = errorId
        self.error = error
        self.data = data
        self.laboratorio_id = laboratorio_id
        self.strumento_id = strumento_id
        self.strumName = strumName

    def __repr__(self):
        return "{}-{}-{}".format(self.loid, self.laboratorio_id, self.data)


# Funzioni di utility del sito


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):  # Generatore di token
    return ''.join(random.choice(chars) for _ in range(size))


def login(username, password):  # Funzione di controllo credenziali
    user = User.query.filter_by(username=username).first()
    try:
        return bcrypt.checkpw(bytes(password, encoding="utf-8"), user.passwd)
    except AttributeError:
        # Se non esiste l'Utente
        return False


def find_user(username):  # Restituisce l'utente corrispondente all'username
    return User.query.filter_by(username=username).first()


# Pagine del sito


@app.route("/")  # Radice del sito, viene usata per il logoff
def page_home():
    if 'username' not in session:
        return redirect(url_for('page_login'))
    else:
        session.pop('username')  # Logoff
        return redirect(url_for('page_login'))


@app.route("/monitoraggio", methods=["GET", "POST"])
def page_monitoraggio():
    if 'username' not in session or 'username' is None:  # Verifica accesso
        return redirect(url_for('page_login'))
    if request.method == "GET":
        logs = Log.query.join(Laboratorio).order_by(Log.data.desc()).limit(100).all()  # Log recenti
        utente = find_user(session['username'])
        laboratori = Laboratorio.query.all()
        return render_template("monitoraggio.htm", utente=utente, laboratori=laboratori, logs=logs)


@app.route("/strumquery", methods=['POST'])  # Funzione per la ricerca dinamica
def page_strumquery():
    if 'username' not in session or 'username' is None:
        abort(403)
    print(request.form['lab'])
    risultato = Strumento.query.filter_by(laboratorio_id=request.form['lab']).all()
    msg = ""
    for entita in risultato:
        msg = msg + "<a class=\"dropdown-item\" onclick=\"strumsense(" + str(
            entita.sid) + ")\">" + entita.nome + "</a>\n"
    return msg


@app.route("/logquery", methods=['POST'])  # Funzione per la ricerca dinamica
def page_logquery():
    if 'username' not in session or 'username' is None:
        abort(403)
    risultato = Log.query.filter_by(strumento_id=request.form['strum']).order_by(Log.data.desc()).all()
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
        if login(request.form['username'], request.form['password']):  # Autenticazione
            session['username'] = request.form['username']  # Aggiunta dell'utente alla sessione attiva
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
            rete = Strumento(0, "Rete", "Oggetto dummy", 1, 2, nuovolaboratorio.lid)  # Nota importante: questo strumento serve per i messaggi della connettività e viene creato a tal proposito. Non è possibile modificarlo.
            db.session.add(rete)
            db.session.commit()
            logdummy = Log("0", "Rete Creata", datetime.now(), nuovolaboratorio.lid, 0, "Rete")
            db.session.add(logdummy)
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
        statorete = Log.query.filter_by(laboratorio_id=lid, strumName="Rete").order_by(Log.data.desc()).first()
        return render_template("/laboratorio/details.htm", utente=utente, laboratori=laboratori, strumenti=strumenti,
                               entita=entita, statorete=statorete)


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
                                        request.form['modello'], request.form['proto'],
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
            logs = Log.query.filter_by(strumento_id=valore).order_by(Log.data.desc()).all()
        else:
            logs = Log.query.filter_by(laboratorio_id=valore).order_by(Log.data.desc()).all()
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
                return render_template("query.htm", query=request.form["query"], error=repr(e), utente=utente,
                                       laboratori=laboratori)
            return render_template("query.htm", query=request.form["query"], result=result, utente=utente,
                                   laboratori=laboratori)


@app.route('/recv_bot', methods=["POST"])
def page_recv_bot():
    telegram_token = ""
    identificatori_chat = []
    labId = request.form['labId']
    token = request.form['token']
    strum_id = request.form['strumId']
    event = request.form['event']
    eventId = request.form['eventId']
    if Bot.query.filter_by(laboratorio_id=labId, token=token).all():
        strumento = Strumento.query.filter_by(identificatore_esterno=strum_id, laboratorio_id=labId).first()
        if strumento:
            nuovolog = Log(eventId, event, datetime.today(), labId, strumento.sid, strumento.nome)
            db.session.add(nuovolog)
            db.session.commit()
            laboratorio = Laboratorio.query.filter_by(lid=labId).first()
            testo = "{}/{}/{} {}:{}\n{}, {}\n{} - {}".format(nuovolog.data.day, nuovolog.data.month, nuovolog.data.year,
                                                             nuovolog.data.hour, nuovolog.data.minute, laboratorio.nome,
                                                             strumento.nome, eventId, event)
            for chat in identificatori_chat:
                param = {"chat_id": chat, "text": testo}
                requests.get("https://api.telegram.org/bot" + telegram_token + "/sendMessage", params=param)
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


@app.route('/mod_bot/<int:bid>', methods=["GET"])
def page_mod_bot(bid):
    if 'username' not in session:
        abort(403)
    else:
        bot = Bot.query.get_or_404(bid)
        bot.token = id_generator()
        db.session.commit()
        return redirect(url_for('page_bot_list'))


@app.route('/delete_from_database/<int:object>/<int:id>', methods=["GET", "POST"])
def paage_delete(object, id):
    if 'username' not in session:
        abort(403)
    else:
        if request.method == "GET":
            utente = find_user(session['username'])
            laboratori = Laboratorio.query.all()
            return render_template("/delete.htm", utente=utente, laboratori=laboratori, object=object, id=id)
        else:
            if object == 0:  # Bot
                bot = Bot.query.get_or_404(id)
                db.session.delete(bot)
                db.session.commit()
                return redirect(url_for('page_list_bot'))
            elif object == 1:  # Laboratorio
                print("lab")
                laboratorio = Laboratorio.query.get_or_404(id)
                for oggetto in laboratorio.bot:
                    db.session.delete(oggetto)
                for oggetto in laboratorio.strumenti:
                    db.session.delete(oggetto)
                for oggetto in laboratorio.log:
                    db.session.delete(oggetto)
                db.session.delete(laboratorio)
                db.session.commit()
                return redirect(url_for('page_laboratorio_list'))
            elif object == 2:  # Strumento
                if id == 0:
                    abort(403)
                strumento = Strumento.query.get_or_404(id)
                db.session.delete(strumento)
                db.session.commit()
                return redirect(url_for('page_strumento_lista'))
            elif object == 3:  # Utente
                utente = User.query.get_or_404(id)
                db.session.delete(utente)
                db.session.commit()
                return redirect(url_for('page_list_user'))
            else:
                abort(404)


if __name__ == "__main__":
    # Se non esiste il database viene creato
    if not os.path.isfile("db.sqlite"):
        db.create_all()
        p = bytes("password", encoding="utf-8")
        cenere = bcrypt.hashpw(p, bcrypt.gensalt())
        admin = User("admin@admin.com", cenere, "Amministratore")
        db.session.add(admin)
        db.session.commit()
    app.run(host="0.0.0.0", debug=False)
