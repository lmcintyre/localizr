from collections import defaultdict

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from hashlib import blake2b
import os
import time
import timeago
import timeago.locales.en

db = SQLAlchemy()


class Post(db.Model):
    __tablename__ = "posts"
    # Common fields, commented out unneeded ones in order to save db space
    # Can uncomment here and in loader.py if you want these fields
    id = db.Column(db.Integer, primary_key=True)                # Post id
    # url = db.Column(db.Text, nullable=False)                    # Post original url
    # url_with_slug = db.Column(db.Text, nullable=False)          # Post original url with slug
    # slug = db.Column(db.Text, nullable=False)                   # Post slug
    type = db.Column(db.Text, nullable=False)                   # Post type (photo, regular, video, answer, link, conversation, quote)
    # state = db.Column(db.Text, nullable=False)                  # Post state (published, submission)
    # date_gmt = db.Column(db.Text, nullable=False)               # GMT posting time, string, "YYYY-MM-DD HH:MM:SS GMT"
    # date = db.Column(db.Text, nullable=False)                   # local posting time, string, "DAY, DD MON YYYY HH:MM:SS"
    unix_timestamp = db.Column(db.Integer, nullable=False)      # Unix post time
    # format = db.Column(db.Text, nullable=False)                 # either "html" or "markdown". TODO: figure out how it works
    # reblog_key = db.Column(db.Text, nullable=False)             # must be used internally, we keep it (for now) but we don't care
    is_reblog = db.Column(db.Text, nullable=False)              # was the post a reblog? "true" or "false"
    tumblelog = db.Column(db.Text, nullable=False)              # the blog posted to
    tags = db.relationship("Tag")

    # Everything from here on is optional
    # private = db.Column(db.Text, nullable=False)                # if the post is private or not

    # Photo fields
    # width = db.Column(db.Integer, nullable=True)                # Image width
    # height = db.Column(db.Integer, nullable=True)               # Image height

    # Video fields
    # direct_video = db.Column(db.Text, nullable=True)            # Unknown, is always "true" in my blog

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

    @staticmethod
    def not_found(id):
        ret = Post()
        ret.id = id
        ret.unix_timestamp = datetime.now().timestamp()
        ret.type = "regular"
        content = RegularPost()
        content.title = "Not Found"
        content.caption = "<p>The URL you requested could not be found.</p>"
        ret.regular_post = [content]
        return ret

    @staticmethod
    def welcome():
        ret = Post()
        ret.id = "welcome"
        ret.unix_timestamp = datetime.now().timestamp()
        ret.type = "regular"
        content = RegularPost()
        content.caption = \
            """
            <p>Welcome to localizr!</p>
            <p>This example post is included with localizr, and is not part of your blog. It'll show you how to use
            all of localizr's features to view the posts of a loaded blog.</p>
            <p>To start, localizr already supports the common Tumblr features such as tagged posts. Maybe your blog
            has a "me" tag? Try going to this link: <a href="/tagged/me">/tagged/me</a>.</p>
            <p>You can access any tag the same way, including tags with spaces and other symbols.</p>
            <p>Obviously, pages work - you can go through all of the pages on anything that has them. This "post"
            behaves like any other post, so there's no pages at the bottom here.</p>
            <p>localizr has a few extra tricks up its sleeve, self and type. You may already have tagged all of your
            posts of a certain type, i.e. "video" or "audio", but on localizr, you can just go to
            <a href="/type/video">/type/video</a> or <a href="/type/audio">/type/audio</a>.</p>
            <p>The valid post types are:
            <ul>
                <li>"regular" (text posts)</li>
                <li>answer</li>
                <li>conversation</li>
                <li>link</li>
                <li>photo</li>
                <li>photoset</li>
                <li>quote</li>
                <li>audio</li>
                <li>video</li>
            </ul>
            <p>localizr's next feature is <a href="/self">/self</a>. This link will filter posts to only show posts that
            you made, excluding all reblogs. This is an easy way to go through all of your original content. In
            addition, you can combine self and tagged, or self and type. If you want to find posts you've made
            and tagged "Pokemon", simply go to <a href="/self/tagged/pokemon">/self/tagged/pokemon</a>. If you want
            to find audio posts that you've made, you can go to <a href="/self/type/audio">/self/type/audio</a>!</p>
            <p>That's about it. Except there's one more thing. localizr is open source, so if it doesn't do something
            that you want it to do - you or somebody else with programming knowledge can add a new feature.</p>
            <p>That's actually it, so click "localizr" at the top of this page to go to your blog.</p>
            """

        ret.regular_post = [content]
        return ret

    def permalink(self):
        if isinstance(self.id, int):
            return f"/post/{self.id}"
        else:
            return f"/{self.id}"

    def has_readmore(self):
        more_flag = "<!-- more -->"

        if self.type == "regular":
            if self.regular_post[0].caption is not None:
                return more_flag in self.regular_post[0].caption
        elif self.type == "photo":
            if self.photo_post[0].caption is not None:
                return more_flag in self.photo_post[0].caption
        elif self.type == "quote":
            if self.quote_post[0].source is not None:
                return more_flag in self.quote_post[0].caption
        elif self.type == "answer":
            if self.answer_post[0].answer is not None:
                return more_flag in self.answer_post[0].answer
        elif self.type == "link":
            if self.link_post[0].desc is not None:
                return more_flag in self.link_post[0].desc
        elif self.type == "audio":
            if self.audio_post[0].caption is not None:
                return more_flag in self.audio_post[0].caption
        elif self.type == "video":
            if self.video_post[0].caption is not None:
                return more_flag in self.video_post[0].caption
        else:
            return False

    def day_of_week(self):
        return time.strftime("%A", time.localtime(self.unix_timestamp))

    def day_of_month(self):
        return time.strftime("%d", time.localtime(self.unix_timestamp))

    def month(self):
        return time.strftime("%B", time.localtime(self.unix_timestamp))

    def year(self):
        return time.strftime("%Y", time.localtime(self.unix_timestamp))

    def hour24(self):
        return time.strftime("%H", time.localtime(self.unix_timestamp))

    def minute(self):
        return time.strftime("%M", time.localtime(self.unix_timestamp))

    def seconds(self):
        return time.strftime("%S", time.localtime(self.unix_timestamp))

    def timeago(self):
        return timeago.format(datetime.fromtimestamp(self.unix_timestamp),
                              datetime.now())


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))

    tag = db.Column(db.Text, nullable=False)

    def __cmp__(self, other):
        return self.tag == other.tag


class RegularPost(db.Model):
    __tablename__ = "regular_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="regular_post")

    title = db.Column(db.Text, nullable=True)
    caption = db.Column(db.Text, nullable=True)

    def readmore_caption(self):
        try:
            return self.caption[0:self.caption.index("<!-- more --")]
        except ValueError:
            return self.caption


class PhotoPost(db.Model):
    __tablename__ = "photo_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="photo_post")

    caption = db.Column(db.Text, nullable=True)
    is_photoset = db.Column(db.Boolean, nullable=False)

    photos = db.relationship("Photo", lazy="dynamic")

    def readmore_caption(self):
        try:
            return self.caption[0:self.caption.index("<!-- more --")]
        except ValueError:
            return self.caption

    def urls(self):
        ret = []

        for photo in self.photos:
            ret.append(photo.url)

        return ret

    def has_iframe(self):
        return self.photos[0].row is not None

    def iframe_height(self, width):
        photos_per_row = defaultdict(list)
        for photo in self.photos:
            photos_per_row[photo.row].append(photo)

        total_height = len(photos_per_row.keys()) * 10
        for row in photos_per_row.keys():
            row_len = len(photos_per_row[row])
            new_width = (width - ((row_len - 1) * 10)) / row_len
            smallest_photo_height = float("inf")
            for photo in photos_per_row[row]:
                if photo.height < smallest_photo_height:
                    smallest_photo_height = photo.height
                    row_height = int(round((photo.height / photo.width) * new_width))
            total_height += row_height
        return total_height

    def process_photoset(self, width):
        if not self.is_photoset:
            raise ValueError("Not a photoset")

        photos_per_row = defaultdict(list)
        ret_rows = []

        for photo in self.photos:
            photos_per_row[photo.row].append(photo)

        for row in photos_per_row.keys():
            current_row = {"width": width}

            row_len = len(photos_per_row[row])
            new_width = (width - ((row_len - 1) * 10)) / row_len

            smallest_photo_height = float("inf")

            for photo in photos_per_row[row]:
                if photo.height < smallest_photo_height:
                    smallest_photo_height = photo.height
                    current_row["height"] = int(round((photo.height / photo.width) * new_width))

            for photo in photos_per_row[row]:
                new_height = int(round((photo.height / photo.width) * new_width))
                margin = (current_row["height"] - new_height) / 2

                new_photo = {"width": new_width,
                             "height": new_height,
                             "topmargin": margin,
                             "url": photo.url}

                if current_row.get("photos") is None:
                    current_row["photos"] = [new_photo]
                else:
                    current_row["photos"].append(new_photo)

            ret_rows.append(current_row)
        return ret_rows


class Photo(db.Model):
    __tablename__ = "photos"
    post_id = db.Column(db.Integer, db.ForeignKey("photo_posts.id"), primary_key=True)
    offset = db.Column(db.Integer, primary_key=True)
    row = db.Column(db.Integer, nullable=True)

    height = db.Column(db.Integer, nullable=True)
    width = db.Column(db.Integer, nullable=True)

    url = db.Column(db.Text, nullable=False)
    # local_url = db.Column(db.text, nullable=True)
    caption = db.Column(db.Text, nullable=True)

    photo_post = db.relationship("PhotoPost", back_populates="photos")


class LinkPost(db.Model):
    __tablename__ = "link_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="link_post")

    text = db.Column(db.Text, nullable=True)
    url = db.Column(db.Text, nullable=True)
    desc = db.Column(db.Text, nullable=True)

    def readmore_caption(self):
        try:
            return self.desc[0:self.desc.index("<!-- more --")]
        except ValueError:
            return self.desc


class AnswerPost(db.Model):
    __tablename__ = "answer_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="answer_post")

    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=True)

    def readmore_caption(self):
        try:
            return self.answer[0:self.answer.index("<!-- more --")]
        except ValueError:
            return self.answer


class QuotePost(db.Model):
    __tablename__ = "quote_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="quote_post")

    text = db.Column(db.Text, nullable=False)
    source = db.Column(db.Text, nullable=True)

    def readmore_caption(self):
        try:
            return self.source[0:self.source.index("<!-- more --")]
        except ValueError:
            return self.source


class ConversationPost(db.Model):
    __tablename__ = "conv_posts"
    id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    base_post = db.relationship("Post", back_populates="conversation_post")

    title = db.Column(db.Text, nullable=True)
    lines = db.relationship("ConversationLine")


class ConversationLine(db.Model):
    __tablename__ = "conv_lines"
    post_id = db.Column(db.Integer, db.ForeignKey("conv_posts.id"), primary_key=True)
    line_num = db.Column(db.Integer, primary_key=True)

    label = db.Column(db.Text, nullable=True)
    text = db.Column(db.Text, nullable=False)

    def name(self):
        if self.label:
            return str(self.label).replace(":", "")


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

    def readmore_caption(self):
        try:
            return self.caption[0:self.caption.index("<!-- more --")]
        except ValueError:
            return self.caption


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

    def readmore_caption(self):
        try:
            return self.caption[0:self.caption.index("<!-- more --")]
        except ValueError:
            return self.caption

    def is_local(self):
        return "<video " in self.player or "<audio " in self.player

    def table_class(self):
        if "<video " in self.player:
            return "audio_video_table"
        else:
            return "audio_table"


class MediaEntry(db.Model):
    __tablename__ = "media_entries"
    id = db.Column(db.String, nullable=False, primary_key=True)
    file_hash = db.Column(db.String, nullable=False)
    data = db.relationship("Media")


class Media(db.Model):
    __tablename__ = "media"
    file_hash = db.Column(db.String, db.ForeignKey("media_entries.file_hash"), primary_key=True)
    data = db.Column(db.BLOB, nullable=False)


def get_file_hash(path):
    hasher = blake2b(digest_size=16)
    size = os.stat(path).st_size
    with open(path, "rb") as file:
        while size >= 8192:
            current_data = file.read(8192)
            hasher.update(current_data)
            size = size - 8192
        current_data = file.read(size)
        hasher.update(current_data)
        return hasher.hexdigest()
