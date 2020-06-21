import requests
from bs4 import BeautifulSoup

from app import Runner, app
from tqdm import tqdm
from model import db, Tag, Post, RegularPost, PhotoPost, Photo, LinkPost, AnswerPost, QuotePost, ConversationPost, \
    ConversationLine, VideoPost, AudioPost

# mini = True
mini = False


class Loader:
    def __init__(self, filename):
        self.filename = filename
        self.soup = None
        self.blog_name = None

    def load_soup(self):
        with open(self.filename, encoding="utf-8") as posts:
            text = posts.read()
        self.soup = BeautifulSoup(text, "xml")
        self.blog_name = self.soup.find("post")["tumblelog"]
        print(f"loaded {self.filename} for blog {self.blog_name}!")

    def init_db(self):
        Runner.create_database(self.blog_name)
        print(f"created database {self.blog_name}.db!")

    def count_post_types(self):
        if self.soup is None:
            raise ValueError("Loader's soup was None")

        results = {}
        for post in self.soup.find_all("post"):
            value = results.get(post["type"])
            if value is not None:
                results[post["type"]] = value + 1
            else:
                results[post["type"]] = 1
        return results

    def insert_posts(self, fix_photosets, blog_name=""):
        if self.soup is None:
            raise ValueError("Loader's soup was None")

        with app.app_context():
            for post in tqdm(self.soup.find_all("post")):
                if not Post.query.get(post["id"]):
                    add_post(post, fix_photosets, blog_name)
            db.session.commit()


def main():
    if mini:
        file = "posts_mini.xml"
    else:
        file = "posts.xml"

    with open(file, encoding="utf-8") as posts:
        text = posts.read()
    soup = BeautifulSoup(text, "xml")

    post_tags = soup.find_all("post")
    print("loaded")

    num_posts = len(post_tags)

    for index, post_element in enumerate(post_tags):
        print(f"{index:05}/{num_posts}")

        # Yes, have to check if it doesn't exist already
        # Some post tags are duplicated...
        if not Post.query.get(post_element["id"]):
            add_post(post_element)

    db.session.commit()


def get_photoset_iframe_url(post, blog_name=""):
    # format = "https://tacticalravioli.tumblr.com/post/93759219776/photoset_iframe/tacticalravioli/tumblr_n9rti43cev1swkprh/700/false"
    iframe_format = "https://{}.tumblr.com/post/{}/photoset_iframe/{}/{}/500/false"
    full_url = post.find("photo-url").text.strip()
    url_file = full_url[full_url.index("tumblr_"):]
    media_key = url_file[0:url_file.rindex("o")]
    if not blog_name:
        blog_name = post["tumblelog"]
    return iframe_format.format(blog_name, post["id"], blog_name, media_key)


def get_image_rows(post, blog_name=""):
    iframe_url = get_photoset_iframe_url(post, blog_name)
    try:
        page = requests.get(iframe_url).content
    except requests.exceptions.RequestException:
        print(f"couldn't load photoset data for post {post['id']}")
        return None

    soup = BeautifulSoup(page, "xml")
    row_counts = []
    for tag in soup.select(".photoset_row"):
        for css_class in tag["class"].split():
            if "row_" in css_class:
                row_counts.append(int(css_class[css_class.rindex("_") + 1:]))
    image_rows = []
    for row_index, val in enumerate(row_counts):
        for index in range(0, val):
            image_rows.append(row_index + 1)
    return image_rows


def add_post(post, fix_photosets, blog_name=""):
    tag_list = []
    for tag_element in post.find_all("tag"):
        this_tag = Tag(post_id=post["id"], tag=tag_element.text.strip())
        db.session.add(this_tag)
        tag_list.append(this_tag)

    db.session.add(Post(
        id=post["id"],
        url=post["url"],
        url_with_slug=post["url-with-slug"],
        slug=post["slug"],
        type=post["type"],
        state=post["state"],
        date_gmt=post["date-gmt"],
        date=post["date"],
        unix_timestamp=post["unix-timestamp"],
        format=post["format"],
        reblog_key=post["reblog-key"],
        is_reblog=post["is_reblog"],
        tumblelog=post["tumblelog"],
        tags=tag_list,

        private=post.get("private", "false"),

        # width=int(post.get("width")) if post.get("width") else None,
        width=post.get("width"),
        height=post.get("height"),

        direct_video=post.get("direct-video"),

        audio_plays=post.get("audio-plays")
    ))

    if post["type"] == "regular":
        regular_post = RegularPost(id=post["id"])

        title_tag = post.find("regular-title")
        body_tag = post.find("regular-body")

        regular_post.title = title_tag.text.strip() if title_tag else None
        regular_post.caption = body_tag.text.strip() if body_tag else None

        db.session.add(regular_post)
    elif post["type"] == "photo":
        photo_post = PhotoPost(id=post["id"])

        caption_tag = post.find("photo-caption")
        if caption_tag:
            photo_post.caption = caption_tag.text.strip()

        # Only photosets have photo tags as children
        is_photoset = False if len(post.find_all("photo")) == 0 else True

        photos = []
        # TODO: combine these two cases intelligently maybe possibly perhaps
        if is_photoset:
            # Here, we ignore the base photo-url tags
            photo_tags = post.find_all("photo")

            if fix_photosets:
                rows_per_image = get_image_rows(post, blog_name)

            for i, photo_tag in enumerate(photo_tags):
                photo_url_tags = photo_tag.find_all("photo-url")

                for img in photo_url_tags:
                    if img["max-width"] == "1280":
                        img_url = img.text.strip()
                        caption = photo_tag["caption"] or None
                        this_photo = Photo(post_id=post["id"],
                                           caption=caption,
                                           offset=i + 1,
                                           width=photo_tag["width"],
                                           height=photo_tag["height"],
                                           url=img_url)

                        if fix_photosets and rows_per_image is not None:
                            this_photo.row = rows_per_image[i]

                        photos.append(this_photo)
        else:
            photo_url_tags = post.find_all("photo-url")

            for img in photo_url_tags:
                if img["max-width"] == "1280":
                    img_url = img.text.strip()
                    this_photo = Photo(post_id=post["id"], offset=0, url=img_url)
                    photos.append(this_photo)

        for photo in photos:
            db.session.add(photo)
        photo_post.is_photoset = is_photoset
        photo_post.photos = photos
        db.session.add(photo_post)
    elif post["type"] == "link":
        link_post = LinkPost(id=post["id"])

        text_tag = post.find("link-text")
        url_tag = post.find("link-url")
        desc_tag = post.find("link-description")

        link_post.text = text_tag.text.strip() if text_tag else None
        link_post.url = url_tag.text.strip() if url_tag else None
        link_post.desc = desc_tag.text.strip() if desc_tag else None
        db.session.add(link_post)
    elif post["type"] == "answer":
        answer_post = AnswerPost(id=post["id"])

        question_tag = post.find("question")
        answer_tag = post.find("answer")

        answer_post.question = question_tag.text.strip() if question_tag else None
        answer_post.answer = answer_tag.text.strip() if answer_tag else None
        db.session.add(answer_post)
    elif post["type"] == "quote":
        quote_post = QuotePost(id=post["id"])

        text_tag = post.find("quote-text")
        source_tag = post.find("quote-source")

        quote_post.text = text_tag.text.strip() if text_tag else None
        quote_post.source = source_tag.text.strip() if source_tag else None
        db.session.add(quote_post)
    elif post["type"] == "conversation":
        conv_post = ConversationPost(id=post["id"])

        title_tag = post.find("conversation-title")

        conv_post.title = title_tag.text.strip() if title_tag else None

        line_tags = post.find_all("line")
        lines = []
        for index, line_tag in enumerate(line_tags):
            line_text = line_tag.text.strip()
            this_line = ConversationLine(post_id=post["id"], line_num=index + 1, text=line_text)
            this_line.label = line_tag.get("label")
            lines.append(this_line)
            db.session.add(this_line)

        conv_post.lines = lines
        db.session.add(conv_post)
    elif post["type"] == "video":
        video_post = VideoPost(id=post["id"])

        caption_tag = post.find("video-caption")
        player_tag = post.find("video-player")
        video_post.caption = caption_tag.text.strip() if caption_tag else None

        if post.find("revision") is None:
            video_post.player = player_tag.text.strip() if player_tag else None
            video_post.source = post.find("video-source").text.strip()
        else:
            content_tag = post.find("content-type")
            extension_tag = post.find("extension")
            width_tag = post.find("width")
            height_tag = post.find("height")
            duration_tag = post.find("duration")
            revision_tag = post.find("revision")

            video_post.content_type = content_tag.text.strip() if content_tag else None
            video_post.extension = extension_tag.text.strip() if extension_tag else None
            video_post.width = width_tag.text.strip() if width_tag else None
            video_post.height = height_tag.text.strip() if height_tag else None
            video_post.duration = duration_tag.text.strip() if duration_tag else None
            video_post.revision = revision_tag.text.strip() if revision_tag else None

            soup2 = BeautifulSoup(player_tag.text.strip(), "html.parser")

            # this adds the necessary attribute to display video controls
            soup2.find("video")["controls"] = None

            src_tag = soup2.find("source")
            src_text = src_tag["src"]
            new_src = get_src_url(src_text, video_post.extension)
            src_tag["src"] = new_src
            video_post.player = str(soup2)

        db.session.add(video_post)
    elif post["type"] == "audio":
        audio_post = AudioPost(id=post["id"])

        caption_tag = post.find("audio-caption")
        player_tag = post.find("audio-player")

        artist_tag = post.find("id3-artist")
        album_tag = post.find("id3-album")
        title_tag = post.find("id3-title")
        track_tag = post.find("id3-track")
        year_tag = post.find("id3-year")

        audio_post.caption = caption_tag.text.strip() if caption_tag else None
        audio_post.player = player_tag.text.strip() if player_tag else None
        audio_post.artist = artist_tag.text.strip() if artist_tag else None
        audio_post.album = album_tag.text.strip() if album_tag else None
        audio_post.title = title_tag.text.strip() if title_tag else None
        audio_post.track = track_tag.text.strip() if track_tag else None
        audio_post.year = year_tag.text.strip() if year_tag else None

        db.session.add(audio_post)

    # db.session.commit()


def get_src_url(old_src, extension):
    va_format = "https://va.media.tumblr.com/{}.{}"
    src = old_src[old_src.index("tumblr_"):]
    try:
        src = src[0:src.rindex("/")]
    except ValueError:
        pass

    return va_format.format(src, extension)

if __name__ == "__main__":
    main()
