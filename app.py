import random

from flask import Flask, redirect, url_for, render_template, request, session, jsonify
import pymongo
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from pymongo.errors import OperationFailure
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["qa_platform"]

# Collezioni del database
users_collection = mydb["users"]
questions_collection = mydb["questions"]
answers_collection = mydb["answers"]

@app.route("/",methods=['GET'])
def show_home():
    #Test db connection
    if not connect_to_db():
        return redirect("error_page.html", code=500)

    '''Authentication'''
    question_collection = mydb["questions"] #riferimento alla collezione
    questions = question_collection.find() #lista di domande

    random_questions = random.sample(list(questions), 10) #lista di domande random

    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("questions/index.html")
    #return render_template("questions/index.html", questions=random_questions)

#@app.route("/registrazione")
#def register():
 #   return render_template("auth/register.html")

@app.route("/registrazione", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return render_template("auth/register.html", error="Le password non corrispondono.")

        # Validazione dell'email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            #return "Formato email non valido!"
            return render_template("auth/register.html", error="Formato email non valido.")

        # Validazione della password
        password_regex = r'^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+={};:,.<>?]).{8,}$'
        if not re.match(password_regex, password):
            #return "La password deve avere almeno 8 caratteri, includere almeno un numero, una lettera maiuscola e un carattere speciale!"
            return render_template("auth/register.html", error="La password deve avere almeno 8 caratteri, includere almeno un numero, una lettera maiuscola e un carattere speciale.")

        # Controllo se username o email esistono già
        if users_collection.find_one({"username": username}):
            #return "Username già in uso!"
            return render_template("auth/register.html", error="Username già in uso!")

        if users_collection.find_one({"email": email}):
            #return jsonify({'message': 'Email already exists'}), 400
            #return "Email già in uso!"
            return render_template("auth/register.html", error="Email già in uso!")

        # Hash della password
        hashed_password = generate_password_hash(password)

        # Genera un ID univoco di 7 cifre
        user_id = generate_unique_id()
        creation_date = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")

        try:
            # Inserimento del nuovo utente nel database
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


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/myQuestions",methods=['GET'])
def show_user_questions():
    #Test db connection
    if not connect_to_db():
        return redirect("error_page.html", code=500)

    '''Authentication'''
    question_collection = mydb["questions"]
    user_collection = mydb["users"]


    user = user_collection.find_one({"id":14008})
    print("Il nome utente è: ")
    print(user)

    pipeline = [
        {
            '$lookup': {
                'from': 'users',
                'localField': 'OwnerUserId',
                'foreignField': 'id',
                'as': 'joinedResult'
            }
        }
    ]
    user_questions = list(question_collection.aggregate(pipeline))
    '''printare userquestions'''
    return render_template("questions/my_questions.html", questions=user_questions)

@app.route("/myAnswers",methods=['GET'])
def show_user_answers():
    '''Authentication'''
    return "showing user answers"

def connect_to_db():
    try:
        myclient = pymongo.MongoClient("mongodb://localhost:27017/")
        mydb = myclient["qa_platform"]
        print(mydb)
    except ConnectionFailure as e:
        print("Connection failed")
        print(e)
    return True

def generate_unique_id():
    while True:
        user_id = random.randint(1000000, 9999999)  # Genera un numero casuale di 7 cifre
        if not users_collection.find_one({"_id": user_id}):  # Verifica che l'ID non esista già
            return user_id

if __name__ == '__main__':
    app.run()
