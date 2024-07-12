from flask import Flask

app = Flask(__name__)

("This project implements a Questions and Answer platform like Stack Overflow. "
 "The main goal is to implement a MongoDB database for our University project.")

@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'




if __name__ == '__main__':
    app.run()
