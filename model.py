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
    tags = db.relationship("Tag")

    # Everything from here on is optional
    private = db.Column(db.Text, nullable=False)                # if the post is private or not

    # Photo fields
    width = db.Column(db.Integer, nullable=True)                # Image width
    height = db.Column(db.Integer, nullable=True)               # Image height

    # Video fields
    direct_video = db.Column(db.Text, nullable=True)            # Unknown, is always "true" in my blog

    # Audio fields
    audio_plays = db.Column(db.Integer, nullable=True)             # Number of plays on tracks

    # Relationships
    regular_post = db.relationship("RegularPost", back_populates="base_post")
    photo_post = db.relationship("PhotoPost", back_populates="base_post")
    link_post = db.relationship("LinkPost", back_populates="base_post")
    answer_post = db.relationship("AnswerPost", back_populates="base_post")
    quote_post = db.relationship("QuotePost", back_populates="base_post")
    conversation_post = db.relationship("ConversationPost", back_populates="base_post")
    video_post = db.relationship("VideoPost", back_populates="base_post")
    audio_post = db.relationship("AudioPost", back_populates="base_post")


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))

    tag = db.Column(db.Text, nullable=False)


class RegularPost(db.Model):
    __tablename__ = "regular_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="regular_post")

    regular_title = db.Column(db.Text, nullable=True)
    regular_body = db.Column(db.Text, nullable=True)


class PhotoPost(db.Model):
    __tablename__ = "photo_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="photo_post")

    photo_caption = db.Column(db.Text, nullable=True)

    photos = db.relationship("Photo", lazy="dynamic")


class Photo(db.Model):
    __tablename__ = "photos"
    post_id = db.Column(db.Integer, db.ForeignKey("photo_posts.id"), primary_key=True)
    offset = db.Column(db.Integer, primary_key=True)
    max_width = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text, nullable=False)

    caption = db.Column(db.Text, nullable=True)

    photo_post = db.relationship("PhotoPost", back_populates="photos")

    def __repr__(self):
        return f"{self.post_id}, {self.offset},{self.max_width}: " \
               f"{self.url}, {self.caption}"


class LinkPost(db.Model):
    __tablename__ = "link_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="link_post")

    text = db.Column(db.Text, nullable=True)
    url = db.Column(db.Text, nullable=True)
    desc = db.Column(db.Text, nullable=True)


class AnswerPost(db.Model):
    __tablename__ = "answer_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="answer_post")

    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=True)


class QuotePost(db.Model):
    __tablename__ = "quote_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="quote_post")

    text = db.Column(db.Text, nullable=False)
    source = db.Column(db.Text, nullable=True)


class ConversationPost(db.Model):
    __tablename__ = "conv_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="conversation_post")

    lines = db.relationship("ConversationLine")


class ConversationLine(db.Model):
    __tablename__ = "conv_lines"
    post_id = db.Column(db.Integer, db.ForeignKey("conv_posts.id"), primary_key=True)
    line_num = db.Column(db.Integer, primary_key=True)

    text = db.Column(db.Text, nullable=False)


class VideoPost(db.Model):
    __tablename__ = "video_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="video_post")

    caption = db.Column(db.Text, nullable=True)

    # This either has children or is a youtube link
    source = db.Column(db.Text, nullable=True)

    # This information does not exist for youtube links
    content_type = db.Column(db.Text, nullable=True)
    extension = db.Column(db.Text, nullable=True)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.Integer, nullable=True)
    revision = db.Column(db.Integer, nullable=True)

    # This may only be necessary for youtube links in the future
    player = db.Column(db.Text, nullable=True)


class AudioPost(db.Model):
    __tablename__ = "audio_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="audio_post")

    caption = db.Column(db.Text, nullable=True)
    player = db.Column(db.Text, nullable=True)

    # May not be present at all
    artist = db.Column(db.Text, nullable=True)
    album = db.Column(db.Text, nullable=True)
    title = db.Column(db.Text, nullable=True)
    track = db.Column(db.Text, nullable=True)
    year = db.Column(db.Integer, nullable=True)


