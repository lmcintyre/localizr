from flask_sqlalchemy import SQLAlchemy
from localizr import app

db = SQLAlchemy(app)


class Post(db.Model):
    __tablename__ = "posts"
    # Common fields
    id = db.Column(db.Integer, primary_key=True)                # Post id
    url = db.Column(db.Text, nullable=False)                    # Post original url
    url_with_slug = db.Column(db.Text, nullable=False)          # Post original url with slug
    slug = db.Column(db.Text, nullable=False)                   # Post slug
    type = db.Column(db.Text, nullable=False)                   # Post type (photo, regular, video, answer, link, conversation, quote)
    state = db.Column(db.Text, nullable=False)                  # Post state (published, submission)
    date_gmt = db.Column(db.Text, nullable=False)               # GMT posting time, string, "YYYY-MM-DD HH:MM:SS GMT"
    date = db.Column(db.Text, nullable=False)                   # local posting time, string, "DAY, DD MON YYYY HH:MM:SS"
    unix_timestamp = db.Column(db.Integer, nullable=False)      # Unix post time
    format = db.Column(db.Text, nullable=False)                 # either "html" or "markdown". TODO: figure out how it works
    reblog_key = db.Column(db.Text, nullable=False)             # must be used internally, we keep it (for now) but we don't care
    is_reblog = db.Column(db.Text, nullable=False)              # was the post a reblog? "true" or "false"
    tumblelog = db.Column(db.Text, nullable=False)              # the blog posted to
    private = db.Column(db.Text, nullable=False)                # if the post is private or not

    tags = db.relationship("Tag")

    # Photo fields
    width = db.Column(db.Integer, nullable=True)                # Image width
    height = db.Column(db.Integer, nullable=True)               # Image height

    # Video fields
    direct_video = db.Column(db.Text, nullable=True)            # Unknown, is always "true" in my blog

    # Audio fields
    audio_plays = db.Column(db.Integer, nullable=True)          # Number of plays on tracks

    # Relationships
    regular_post = db.relationship("RegularPost")
    photo_post = db.relationship("PhotoPost")


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))

    tag = db.Column(db.Text, nullable=False)


class RegularPost(db.Model):
    __tablename__ = "regular_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", backref="base_post")

    regular_title = db.Column(db.Text, nullable=False)
    regular_body = db.Column(db.Text, nullable=False)


# class PhotoPost(db.Model):
#     __tablename__ = "photo_posts"
#     id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
#     base_post = db.relationship("Post", backref="base_post")
#
#     photo_caption = db.Column(db.Text, nullable=False)
#     photo_url = db.Column(db.Text, nullable=False)
#     photoset = db.Column(db.Text, nullable=False)
#     photo = db.Column(db.Text, nullable=False)
#     photo_link_url = db.Column(db.Text, nullable=False)
