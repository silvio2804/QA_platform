import random
from flask import Flask, redirect, url_for, render_template, request, session, flash, jsonify
import pymongo
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Connessione al database MongoDB
myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["qa_platform"]

# Collezioni del database
users_collection = mydb["users"]
questions_collection = mydb["questions"]
answers_collection = mydb["answers"]

def connect_to_db():
    '''Controlla la connessione al database.'''
    try:
        myclient = pymongo.MongoClient("mongodb://localhost:27017/")
        mydb = myclient["qa_platform"]
        return mydb
    except ConnectionFailure:
        return None

@app.route("/", methods=['GET'])
def show_home():
    '''Visualizza la home page con un elenco di domande casuali.'''
    db = connect_to_db()
    if db is None:
        return redirect(url_for("error_page"), code=500)

    questions = questions_collection.find()
    random_questions = random.sample(list(questions), 10)

    user_session = None
    if "username" in session:
        user_session = users_collection.find_one({"username": session["username"]})

    return render_template("questions/index.html", questions=random_questions, user=user_session)

@app.route("/registrazione", methods=["GET", "POST"])
def register():
    '''Gestisce la registrazione di un nuovo utente.'''
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return render_template("auth/register.html", error="Le password non corrispondono.")

        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return render_template("auth/register.html", error="Formato email non valido.")

        password_regex = r'^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+={};:,.<>?]).{8,}$'
        if not re.match(password_regex, password):
            return render_template("auth/register.html",
                                   error="La password deve avere almeno 8 caratteri, includere almeno un numero, una lettera maiuscola e un carattere speciale.")

        if users_collection.find_one({"username": username}):
            return render_template("auth/register.html", error="Username già in uso!")

        if users_collection.find_one({"email": email}):
            return render_template("auth/register.html", error="Email già in uso!")

        hashed_password = generate_password_hash(password)
        user_id = generate_unique_id()
        creation_date = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")

        try:
            users_collection.insert_one({
                "_id": user_id,
                "username": username,
                "email": email,
                "password": hashed_password,
                "created_at": creation_date
            })
            return redirect(url_for("login"))
        except DuplicateKeyError:
            return render_template("auth/register.html", error="Username o email già in uso!")

    return render_template("auth/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    '''Gestisce il login degli utenti.'''
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = users_collection.find_one({"email": email})

        if user and check_password_hash(user["password"], password):
            session["username"] = user["username"]
            return redirect(url_for("show_home"))
        else:
            return render_template("auth/login.html", error="Email o password non validi!")

    return render_template("auth/login.html")

@app.route("/ask", methods=["GET", "POST"])
def ask_question():
    '''Permette agli utenti di fare una domanda.'''
    if request.method == "POST":
        title = request.form.get("title")
        body = request.form.get("body")

        if not title or not body:
            return render_template("questions/ask.html", error="Il titolo e la descrizione sono obbligatori.")

        owner_user_id = session["username"] if "username" in session else "NA"
        question_id = generate_unique_question_id()

        question = {
            "questionID": question_id,
            "Title": title,
            "Body": body,
            "OwnerUserId": owner_user_id,
            "CreationDate": datetime.now().strftime("%d/%m/%Y - %H:%M:%S"),
            "Score": 0
        }

        questions_collection.insert_one(question)
        return redirect(url_for("show_home"))

    return render_template("questions/ask.html")

@app.route("/add_comment", methods=["POST"])
def add_comment():
    '''Permette agli utenti di aggiungere un commento a una domanda.'''
    comment_body = request.form.get("comment_body")
    question_id = request.form.get("question_id")

    if not comment_body:
        return redirect(url_for("show_home"))

    owner_user_id = session.get("username", "NA")
    answer_id = generate_unique_answer_id()

    comment = {
        "answerID": answer_id,
        "OwnerUserId": owner_user_id,
        "CreationDate": datetime.now().strftime("%d/%m/%Y - %H:%M:%S"),
        "QuestionId": question_id,
        "Score": 0,
        "Body": comment_body
    }

    answers_collection.insert_one(comment)
    flash("Il commento è stato inserito in modo corretto!", "success")
    return redirect(url_for("show_home"))

def search_questions(query):
    '''Esegue una ricerca nel database delle domande.'''
    collection = mydb.questions  # Usa la connessione globale
    results = collection.find({'Title': {'$regex': query, '$options': 'i'}})
    return list(results)  # Assicurati che i risultati siano restituiti come lista

@app.route('/search', methods=['POST'])
def search():
    '''Gestisce la ricerca delle domande.'''
    query = request.form.get('query')
    questions = search_questions(query)
    return render_template('questions/search_results.html', questions=questions, query=query)

@app.route("/logout")
def logout():
    '''Gestisce il logout degli utenti.'''
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/myQuestions", methods=['GET'])
def show_user_questions():
    '''Visualizza le domande dell'utente.'''
    user_session = users_collection.find_one({"username": session.get("username")})
    user_questions = questions_collection.find({"OwnerUserId": user_session["username"]})

    return render_template("questions/my_questions.html", questions=user_questions)

@app.route("/myAnswers", methods=['GET'])
def show_user_answers():
    '''Visualizza le risposte dell'utente.'''
    return "Visualizzazione delle risposte dell'utente"

def generate_unique_id():
    '''Genera un ID utente unico.'''
    while True:
        user_id = random.randint(10000, 99999)
        if not users_collection.find_one({"_id": user_id}):
            return user_id

def generate_unique_question_id():
    '''Genera un ID domanda unico.'''
    while True:
        question_id = random.randint(100000, 999999)
        if not questions_collection.find_one({"questionID": question_id}):
            return question_id

def generate_unique_answer_id():
    '''Genera un ID risposta unico.'''
    while True:
        answer_id = random.randint(1000000, 9999999)
        if not answers_collection.find_one({"answerID": answer_id}):
            return answer_id

if __name__ == "__main__":
    app.run(debug=True)
