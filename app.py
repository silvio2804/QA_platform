from flask import Flask, redirect, url_for, render_template
import pymongo
from pymongo.errors import ConnectionFailure
from pymongo.errors import OperationFailure
app = Flask(__name__)

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["question_anserw_multiple"]

@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'

@app.route("/home")
def home():
    return render_template("questions/home.html")

@app.route("/myQuestions",methods=['GET'])
def show_user_questions():
    #Test db connection
    if not connect_to_db():
        return redirect("error_page.html", code=500)

    '''Authentication'''

    question_collection = mydb["questions"]
    questions = question_collection.find();
    for question in questions:
        print(question)

    return render_template("questions/home.html",questions=questions)

@app.route("/myAnswers",methods=['GET'])
def show_user_answers():
    '''Authentication'''
    return "showing user answers"

def connect_to_db():
    try:
        myclient = pymongo.MongoClient("mongodb://localhost:27017/")
        mydb = myclient["question_anserw_multiple_csv"]
        print(mydb)
    except ConnectionFailure as e:
        print("Connection failed")
        print(e)
    return True

if __name__ == '__main__':
    app.run()
