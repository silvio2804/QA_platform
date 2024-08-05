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
def connect_to_db():
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["qa_platform"]
        return db
    except ConnectionFailure:
        return None

db = connect_to_db()
if db is None:
    raise Exception("Database connection failed")

# Collezioni del database
users_collection = db["users"]
questions_collection = db["questions"]
answers_collection = db["answers"]

@app.route("/", methods=['GET'])
def show_home():
    '''Visualizza la home page con un elenco di domande casuali.'''
    questions = list(questions_collection.find())
    random_questions = random.sample(questions, min(len(questions), 10))
    user_session = users_collection.find_one({"username": session.get("username")}) if "username" in session else None
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
                "id": user_id,
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
            return jsonify({'success': False, 'error': "Il titolo e la descrizione sono obbligatori."})

        # Recupera l'ID dell'utente loggato, se presente
        username = session.get("username")
        if username:
            user = users_collection.find_one({"username": username})
            if user:
                owner_user_id = user["_id"]
            else:
                owner_user_id = "NA"
        else:
            owner_user_id = "NA"

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
        return jsonify({'success': False, 'error': "Il commento non può essere vuoto."})

    # Recupera l'ID dell'utente loggato, se presente
    username = session.get("username")
    if username:
        user = users_collection.find_one({"username": username})
        if user:
            owner_user_id = user["_id"]
        else:
            owner_user_id = "NA"
    else:
        owner_user_id = "NA"

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
    return jsonify({'success': True})

def search_questions(query):
    '''Esegue una ricerca nel database delle domande.'''
    results = questions_collection.find({'Title': {'$regex': query, '$options': 'i'}})
    return list(results)


@app.route('/search', methods=['POST'])
def search():
    '''Gestisce la ricerca delle domande.'''
    query = request.form.get('query').strip()  # Rimuove gli spazi bianchi
    if not query:  # Verifica se la query è vuota
        return render_template('questions/search_results.html', questions=[], query=query,
                               error="Inserisci una query per cercare.")

    questions = search_questions(query)

    # Recupera l'utente loggato, se presente
    user_session = users_collection.find_one({"username": session.get("username")}) if "username" in session else None

    return render_template('questions/search_results.html', questions=questions, query=query, user=user_session)

@app.route('/vote_question', methods=['POST'])
def vote_question():
    '''Gestisce il voto per una domanda.'''
    question_id = request.form.get('question_id')
    vote_type = request.form.get('vote_type')
    username = session.get('username')
    #user_id = session.get('id')
    #user_id = session.get('user_session')
    user_session = users_collection.find_one({"username": session.get("username")}) if "username" in session else None
    user_id = user_session['id']

    print(question_id)
    print(vote_type)
    print(username)
    print(user_id)

    if not username:
        return jsonify({'success': False, 'error': 'Bisogna essere loggati per effettuare modifiche allo score.'})
    if not vote_type:
        return jsonify({'success': False, 'error': 'Tipo di voto obbligatorio.'})
    if not question_id:
        return jsonify({'success': False, 'error': 'ID della domanda obbligatorio.'})

    if vote_type not in ['up', 'down']:
        return jsonify({'success': False, 'error': 'Tipo di voto non valido.'})

    question = questions_collection.find_one({"Id": int(question_id)})
    if not question:
        return jsonify({'success': False, 'error': 'Domanda non trovata.'})

    # Verifica se l'utente sta cercando di votare la propria domanda
    if question['OwnerUserId'] == user_id:
        return jsonify({'success': False, 'error': 'Non puoi votare la tua domanda.'})

    print(username)



    # Memorizza i voti dell'utente in sessione
    if 'voted_questions' not in session:
        session['voted_questions'] = []

    # Verifica se l'utente ha già votato questa domanda
    if question_id in session['voted_questions']:
        return jsonify({'success': False, 'error': 'Hai già votato su questa domanda.'})

    current_score = question['Score']
    new_score = current_score + (1 if vote_type == 'up' else -1)

    result = questions_collection.update_one(
        {"Id": int(question_id)},
        {"$set": {"Score": new_score}}
    )

    if result.modified_count == 1:
        session['voted_questions'].append(question_id)
        return jsonify({'success': True, 'new_score': new_score})
    else:
        return jsonify({'success': False, 'error': 'Impossibile aggiornare il voto.'})


@app.route("/logout")
def logout():
    '''Gestisce il logout degli utenti.'''
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/myQuestions", methods=['GET'])
def show_user_questions():
    '''Visualizza le domande dell'utente.'''
    user_session = users_collection.find_one({"username": session.get("username")})
    id = int(user_session["_id"])
    questions = list(questions_collection.find({"OwnerUserId": id}))
    return render_template("questions/my_questions.html", user=user_session, questions=questions)

@app.route("/myAnswers", methods=['GET'])
def show_user_answers():
    '''Visualizza le risposte dell'utente.'''
    return "Visualizzazione delle risposte dell'utente"

@app.route('/get_answer_count/<int:question_id>', methods=['GET'])
def get_answer_count(question_id):
    '''Ritorna il numero di risposte per una domanda.'''
    try:
        answer_count = answers_collection.count_documents({"QuestionId": question_id})
        return jsonify({'answer_count': answer_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_unique_id():
    '''Genera un ID utente unico.'''
    while True:
        user_id = random.randint(10000, 99999)
        if not users_collection.find_one({"_id": user_id}):
            return user_id

def generate_unique_question_id():
    '''Genera un ID domanda unico.'''
    while True:
        question_id = random.randint(10000, 99999)
        if not questions_collection.find_one({"Id": question_id}):  # Corretto il campo da 'questionID' a 'Id'
            return question_id

def generate_unique_answer_id():
    '''Genera un ID risposta unico.'''
    while True:
        answer_id = random.randint(10000, 99999)
        if not answers_collection.find_one({"answerID": answer_id}):
            return answer_id

if __name__ == "__main__":
    app.run(debug=True)
