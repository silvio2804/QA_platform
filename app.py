import random

from flask import Flask, redirect, url_for, render_template
import pymongo
from pymongo.errors import ConnectionFailure
from pymongo.errors import OperationFailure
app = Flask(__name__)

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["qa_platform"]


@app.route("/",methods=['GET'])
def show_home():
    #Test db connection
    if not connect_to_db():
        return redirect("error_page.html", code=500)

    '''Authentication'''
    question_collection = mydb["questions"] #riferimento alla collezione
    questions = question_collection.find() #lista di domande

    random_questions = random.sample(list(questions), 10) #lista di domande random

    return render_template("questions/index.html", questions=random_questions)

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

if __name__ == '__main__':
    app.run()
