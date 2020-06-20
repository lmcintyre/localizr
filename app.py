from flask import Flask
from model import db
import os
import views
import webbrowser

# I LOVE this.
import click


def secho(text, file=None, nl=None, err=None, color=None, **styles):
    pass


def echo(text, file=None, nl=None, err=None, color=None, **styles):
    pass


click.echo = echo
click.secho = secho

# end workaround

app = Flask(__name__)


class Runner:
    def __init__(self, db_filename):
        if not os.path.exists(f"{db_filename}.db"):
            print(f"Couldn't find file {db_filename}.")
            print("Did you load your blog using --load?")
            return
        self.blog_name = db_filename
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_filename}.db"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    def run_site(self):
        import logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        app.register_blueprint(views.blog)
        db.init_app(app)
        webbrowser.open("http://localhost:5000/welcome")
        print(f"hosting {self.blog_name} on http://localhost:5000/ !")
        app.run()

    @staticmethod
    def create_database(db_filename):
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_filename}.db"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db.init_app(app)
        db.create_all(app=app)


if __name__ == '__main__':
    r = Runner("example.sqlite")
    r.run_site()
