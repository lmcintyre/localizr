from flask import Flask, render_template
from model import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///example.sqlite"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


@app.route('/', defaults={"page": 1})
@app.route("/page/<int:page>")
def base_page(page):
    if page == 0:
        page = 1
    pagination = Post.query.order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)

    return render_template("theme.html", posts=pagination.items, pagination=pagination)


@app.route("/tagged/<string:query>", defaults={"page": 1})
@app.route("/tagged/<string:query>/page/<int:page>")
def tagged_page(query, page):
    if page == 0:
        page = 1

    pagination = Post.query \
        .filter(Post.id.in_(db.session.query(Tag.post_id)
                            .filter(Tag.tag == query))) \
        .order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)

    return render_template("theme.html", query=query, posts=pagination.items, pagination=pagination)


@app.route("/post/<int:post_id>")
def post_page(post_id):
    this_post = [Post.query.get(post_id)]

    return render_template("theme.html", posts=this_post)


@app.route("/type/<string:post_type>", defaults={"page": 1})
@app.route("/type/<string:post_type>/page/<int:page>")
def type_page(post_type, page):
    if page == 0:
        page = 1

    pagination = Post.query.filter(Post.type == post_type).order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)
    return render_template("theme.html", type=post_type, posts=pagination.items, pagination=pagination)


if __name__ == '__main__':
    db.init_app(app)
    app.run()
