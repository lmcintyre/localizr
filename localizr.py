from flask import Flask
from model import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///example.sqlite"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


def render_post(post):
    ret = f"<a href=\"/post/{post.id}\">----------</a><br/>"

    if post.type == "regular":
        title = post.regular_post[0].regular_title
        body = post.regular_post[0].regular_body
        title = title if title else ""
        body = body if body else ""

        ret += f"<h2>{title}</h2>" \
               f"{body}"

        return ret
    elif post.type == "photo":
        caption = post.photo_post[0].photo_caption
        caption = caption if caption else ""
        photos = post.photo_post[0].photos.filter(Photo.max_width == 1280)

        for photo in photos:
            ret += f"<img src=\"{photo.url}\">\n"
        ret += f"<br>{caption}"
    elif post.type == "audio":
        caption = post.audio_post[0].caption
        caption = caption if caption else ""

        iframe = post.audio_post[0].player

        ret += iframe + "<br/>"
        ret += caption

    else:
        return "not a text or photo post"

    for tag in post.tags:
        ret += f"<br/>{tag.tag}<br />"

    return ret + "<br/>---------------<br/>"


@app.route('/', defaults={"page": 1})
@app.route("/page/<int:page>")
def load_page(page):
    if page == 0:
        page = 1
    pagination = Post.query.order_by(-Post.unix_timestamp).paginate(page=page, per_page=15)
    posts = pagination.items

    ret = ""

    for post in posts:
        ret += render_post(post)

    return ret


@app.route("/post/<int:post_id>")
def post_page(post_id):
    this_post = Post.query.get(post_id)
    return render_post(this_post)


if __name__ == '__main__':
    print("hey")
    db.init_app(app)
    app.run()
