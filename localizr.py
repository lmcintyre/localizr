from flask import Flask
from model import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///example.sqlite"


@app.route('/')
def hello_world():
    users = User.query.all()
    text = ""
    for user in users:
        text += str(user) + "\n"
    return text


if __name__ == '__main__':
# db.session.add(User(username="Flask9", email="exmple@extrle.com"))
# db.session.commit()
    print("hey")
    app.run()
