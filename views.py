from flask import render_template, Blueprint
from sqlalchemy import func
from model import *

blog = Blueprint("blog", __name__)


@blog.route("/welcome")
def welcome_page():

    posts = [Post.welcome()]
    return render_template("theme.html", posts=posts)


@blog.route('/', defaults={"page": 1})
@blog.route("/page/<int:page>")
def base_page(page):
    if page == 0:
        page = 1

    pagination = Post.query.order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)
    return render_template("theme.html", posts=pagination.items, pagination=pagination)


@blog.route("/post/<int:post_id>/photoset_iframe/", defaults={"width": 500})
@blog.route("/post/<int:post_id>/photoset_iframe/<int:width>")
def photoset_iframe(post_id, width):
    this_post = Post.query.get(post_id)
    this_post.photo_post[0].process_photoset(width)
    return render_template("photoset_iframe.html", post=this_post, width=width)


@blog.route("/tagged/<string:query>", defaults={"page": 1})
@blog.route("/tagged/<string:query>/page/<int:page>")
def tagged_page(query, page):
    if page == 0:
        page = 1

    pagination = Post.query \
        .filter(Post.id.in_(db.session.query(Tag.post_id)
                            .filter(func.lower(Tag.tag) == func.lower(query)))) \
        .order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)

    return render_template("theme.html", query=query, posts=pagination.items, pagination=pagination)


@blog.route("/type/<string:post_type>", defaults={"page": 1})
@blog.route("/type/<string:post_type>/page/<int:page>")
def type_page(post_type, page):
    if page == 0:
        page = 1

    pagination = Post.query.filter(Post.type == post_type).order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)
    return render_template("theme.html", type=post_type, posts=pagination.items, pagination=pagination)


@blog.route("/self/", defaults={"page": 1})
@blog.route("/self/page/<int:page>")
@blog.route("/self/tagged/<string:query>")
@blog.route("/self/tagged/<string:query>/page/<int:page>")
def self_page(page, query=""):
    if page == 0:
        page = 1

    if query:
        filtered = Post.query \
            .filter(Post.is_reblog == "false") \
            .filter(Post.id.in_(db.session.query(Tag.post_id).filter(func.lower(Tag.tag) == func.lower(query))))
    else:
        filtered = Post.query.filter(Post.is_reblog == "false")

    pagination = filtered.order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)
    return render_template("theme.html", posts=pagination.items, pagination=pagination)


@blog.route("/post/<int:post_id>")
def post_page(post_id):
    this_post = [Post.query.get(post_id)]
    return render_template("theme.html", posts=this_post)
