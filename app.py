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

# Index
questions_collection.create_index({"Title": 'text'})


@app.route("/question/<question_id>", methods=['GET','POST'])
def show_question(question_id):
    print(question_id)
    '''show single question with comments'''
    #print(question_id)
    user_session = users_collection.find_one({"username": session.get("username")}) if "username" in session else None

    pipeline = [
        {
            "$match": {
                "Id": int(question_id)
            }
        },
        {
            "$lookup": {
                "from": "answers",  # Collezione di destinazione
                "localField": "Id",  # Campo della collezione `questions`
                "foreignField": "QuestionId",  # Campo della collezione `answers`
                "as": "answers"  # Si aggiungono le answers come oggetto embedded nel documento question
            }
        }
    ]

    questions_with_comments = list(questions_collection.aggregate(pipeline))
    #print(questions_with_comments)
    # Estrai gli ID degli utenti dai commenti

    for question in questions_with_comments:
        user_ids = [comment['OwnerUserId'] for comment in
                    question.get('answers', [])]  # prendi id di chi ha fatto il commento
        #print(f"user_ids: {user_ids}")

        users = list(db['users'].find({"Id": {"$in": user_ids}},
                                      {"Id": 1, "username": 1, "_id": 0}))  # prendi gli username di chi ha commentato
        #print(f"users: {list(users)}")

        # aggiungili all'oggetto questio_with_answers

        user_map = {user['Id']: user['username'] for user in users}

        for comment in question.get('answers', []):
            comment['username'] = user_map.get(comment['OwnerUserId'], 'NA')

        # Ora il documento `question` contiene i commenti con gli username
    #print(f"question_with_comments: {questions_with_comments}")

    answer_counter = len(questions_with_comments[0]['answers'])
    return render_template("questions/show_question.html", questions=questions_with_comments, user=user_session, answer_counter=answer_counter)

@app.route("/", methods=['GET','POST'])
def show_home():
    '''Show random questions in home page'''
    questions = list(questions_collection.find().limit(10))
    random_question = random.sample(questions,10)
    user_session = users_collection.find_one({"username": session.get("username")}) if "username" in session else None
    question_user_id = [ids['OwnerUserId'] for ids in random_question]

    # Estrai gli ID degli utenti dai commenti
    user_ids = [ids for ids in question_user_id]  # prendi id di chi ha fatto le domande
    #print(f"user_ids: {user_ids}")

    for question in questions:

        users = list(users_collection.find({"Id": {"$in": user_ids}}, {"Id":1, "username": 1, "_id": 0})) #prendi gli username di chi ha fatto la domanda
        #print(f"users: {list(users)}")

        #aggiungi username alla domanda
        user_map = {user['Id']: user['username'] for user in users}

        #print(f"user_map: {user_map}")
        question['username'] = user_map.get(question['OwnerUserId'], 'NA')

    """
    answers = questions_with_comments[0]['answers'] # Prelevo le risposte
    answer_counter = len(answers) # Contatore risposte

    answer_user_ids = [id_ans['OwnerUserId'] for id_ans in answers] #Prelevo tutti gli id degli utenti che hanno risposto

    print("stampa id utenti risposte")
    print(answer_user_ids)

    answers_cursor = list(users_collection.find(  # Prelevo gli utenti che hanno risposto alle domande
        {"id": {"$in": answer_user_ids}},  # Criteri di query
        {"username": 1, "_id": 0}  # Proiezione: includi 'username', escludi '_id'
    ))
    for i in answers_cursor:
        print(i)
    #answers_cursor.pop(0)

    usernames_response = [doc['username'] for doc in answers_cursor]

    print(usernames_response)
    # Visualizzazione dei risultati
    '''for question in questions_with_comments:
        print(f"Domanda: {question['Title']}")
        print(f"Descrizione: {question['Body']}")
        print("Commenti:")
        for comment in question.get('answers', []):
            print(f" - {comment['Body']}")
        print("\n")'''
        """
    return render_template("questions/index.html", questions=questions, user=user_session)

@app.route("/registrazione", methods=["GET", "POST"])
def register():
    ''' Registration users'''
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
                "Id": user_id,
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
    '''Login users'''
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
    '''Allow users to ask a question'''

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
                owner_user_id = user["Id"]
            else:
                owner_user_id = "NA"
        else:
            owner_user_id = "NA"

        question_id = generate_unique_question_id()

        question = {
            "Id": question_id,
            "Title": title,
            "Body": body,
            "OwnerUserId": owner_user_id,
            "CreationDate": datetime.now().strftime("%d/%m/%Y - %H:%M:%S"),
            "Score": 0
        }

        questions_collection.insert_one(question)
        return jsonify({'success': True})

    return render_template("questions/ask.html")

@app.route("/add_comment", methods=["POST"])
def add_comment():
    '''Allow user to add a comment'''

    comment_body = request.form.get("comment_body")
    question_id = request.form.get("question_id")

    if not comment_body:
        return jsonify({'success': False, 'error': "Il commento non può essere vuoto."})

    # Recupera l'ID dell'utente loggato, se presente
    username = session.get("username")
    #print(username)
    if username:
        user = users_collection.find_one({"username": username})
        if user:
            owner_user_id = user["Id"]
        else:
            owner_user_id = "NA"
    else:
        owner_user_id = "NA"

    answer_id = generate_unique_answer_id()

    comment = {
        "Id": answer_id,
        "OwnerUserId": owner_user_id,
        "CreationDate": datetime.now().strftime("%d/%m/%Y - %H:%M:%S"),
        "QuestionId": int(question_id),
        "Score": 0,
        "Body": comment_body
    }
    #print(comment)
    answers_collection.insert_one(comment)

    return redirect(url_for("show_question",question_id=int(question_id)))
    """Fare redirect alla home, inserendo la domanda commentata al top della lista"""
    # flash("Il commento è stato inserito in modo corretto!", "success")
    # return jsonify({'success': True})

def search_questions(query):
    #questions_collection.createIndex({"Title": 1})
    #query2 = questions_collection.find({'Title': {'$regex': query, '$options': 'i'}}).explain()
    query2 = questions_collection.find({"$text": {"$search": query}}) #query con indice -> piu veloce
    return list(query2)


@app.route('/search', methods=['POST'])
def search():
    '''Allow user to search a question by title'''
    query = request.form.get('query').strip()  # Rimuove gli spazi bianchi
    if not query:  # Verifica se la query è vuota
        return render_template('questions/search_results.html', questions=[], query=query,
                               error="Inserisci una query per cercare.")

    questions = search_questions(query)
    # print(f"domande ricercate: {questions}")
    # Recupera l'utente loggato, se presente
    user_session = users_collection.find_one({"username": session.get("username")}) if "username" in session else None

    return render_template('questions/search_results.html', questions=questions, query=query, user=user_session)

@app.route('/vote_question', methods=['POST'])
def vote_question():
    data = request.get_json()
    question_id = data['question_id']
    vote_type = data['vote_type']

    for question in questions:
        if question['Id'] == int(question_id):
            if vote_type == 'up':
                question['Score'] += 1
            elif vote_type == 'down':
                question['Score'] -= 1
            return jsonify({'success': True, 'new_score': question['Score']})

    return jsonify({'success': False, 'error': 'Question not found.'})


@app.route("/logout")
def logout():
    ''' Logout users'''

    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/myQuestions", methods=['GET','POST'])
def show_user_questions():
    '''Allow show user questions'''

    user_session = users_collection.find_one({"username": session.get("username")})
    id = int(user_session["Id"])
    questions = list(questions_collection.find({"OwnerUserId": id}))
    print(questions)
    return render_template("questions/my_questions.html", user=user_session, questions=questions)

@app.route('/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    try:
        # Converti l'ID della domanda in un ObjectId

        print(question_id)
        result = questions_collection.delete_one({'Id': question_id})
        answers_collection.delete_many({'QuestionId': question_id})
        if result.deleted_count == 1:
            flash('Domanda eliminata con successo!', 'success')
        else:
            flash('Domanda non trovata.', 'danger')
    except Exception as e:
        flash(f'Errore durante l\'eliminazione della domanda: {str(e)}', 'danger')

    return redirect(url_for('show_user_questions'))


@app.route('/update_question/<question_id>', methods=['POST'])
def update_question(question_id):

    title = request.form.get('title')
    body = request.form.get('body')

    print(f"{title, body}")

    try:
        result = questions_collection.update_one(
            {'Id': int(question_id)},
            {'$set': {'Title': title, 'Body': body}}
        )
        print(result)
        if result.matched_count == 1:
            print("sium")
            flash('Domanda aggiornata con successo!', 'success')
        else:
            print("nooo")
            flash('Domanda non trovata.', 'danger')
    except Exception as e:
        flash(f'Errore durante l\'aggiornamento della domanda: {str(e)}', 'danger')

    return redirect(url_for('show_user_questions'))


# Altre rotte e logiche dell'app

if __name__ == '__main__':
    app.run(debug=True)
def generate_unique_id():
    '''Generate a random  user Id'''

    while True:
        user_id = random.randint(10000, 99999)
        if not users_collection.find_one({"Id": user_id}):
            return user_id

def generate_unique_question_id():
    '''Generate a random Id'''

    while True:
        question_id = random.randint(10000, 99999)
        if not questions_collection.find_one({"Id": question_id}):  # Corretto il campo da 'questionID' a 'Id'
            return question_id

def generate_unique_answer_id():
    '''Generate a random Id'''

    while True:
        answer_id = random.randint(10000, 99999)
        if not answers_collection.find_one({"Id": answer_id}):
            return answer_id

if __name__ == "__main__":
    app.run(debug=True)
