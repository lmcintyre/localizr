import io
import sys

from flask import Blueprint, render_template, send_from_directory, send_file
from sqlalchemy import func
from model import *

blog = Blueprint("blog", __name__)


@blog.route("/welcome")
def welcome_page():
    post = Post.welcome()
    return render_template("theme.html", posts=[post])


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

    if post_type == "photoset":
        pagination = Post.query.join(PhotoPost)\
                            .filter(Post.type == "photo")\
                            .filter(PhotoPost.is_photoset)\
                            .order_by(-Post.unix_timestamp)\
                            .paginate(page=page, per_page=15)
    # elif post_type == "text":
    #     pagination = Post.query\
    #         .filter(Post.type == post_type).order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)
    else:
        pagination = Post.query\
                        .filter(Post.type == post_type)\
                        .order_by(-Post.unix_timestamp)\
                        .paginate(page=page, per_page=15)
    return render_template("theme.html", type=post_type, posts=pagination.items, pagination=pagination)


@blog.route("/self/", defaults={"page": 1})
@blog.route("/self/page/<int:page>")
@blog.route("/self/type/<string:post_type>", defaults={"page": 1})
@blog.route("/self/type/<string:post_type>/page/<int:page>")
@blog.route("/self/tagged/<string:query>", defaults={"page": 1})
@blog.route("/self/tagged/<string:query>/page/<int:page>")
def self_page(page, post_type="", query=""):
    if page == 0:
        page = 1

    filtered = Post.query.filter(Post.is_reblog == "false")

    if post_type:
        if post_type == "photoset":
            filtered = filtered.join(PhotoPost).filter(Post.type == "photo").filter(PhotoPost.is_photoset)
        else:
            filtered = filtered.filter(Post.type == post_type)

    if query:
        filtered = filtered\
            .filter(Post.id.in_(db.session.query(Tag.post_id)
                                .filter(func.lower(Tag.tag) == func.lower(query))))

    pagination = filtered.order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)
    return render_template("theme.html", posts=pagination.items, type=post_type, pagination=pagination)


@blog.route("/post/<int:post_id>")
def post_page(post_id):
    this_post = Post.query.get(post_id)
    if not this_post:
        this_post = Post.not_found(post_id)
    return render_template("theme.html", posts=[this_post])


@blog.route("/media/<path:filename>")
def media(filename):
    key = f"{filename}"
    media_entry = MediaEntry.query.join(Media).filter(MediaEntry.id == key).first()

    if media_entry is not None:
        data = media_entry.data[0].data
        return send_file(io.BytesIO(data), attachment_filename=filename)

    basepath = ""
    if getattr(sys, "frozen", False):
        basepath = os.path.dirname(sys.executable)
    return send_from_directory(os.path.join(basepath, "media"), filename)
