
from bs4 import BeautifulSoup
import urllib.parse
from model import db, Tag, Post, RegularPost, PhotoPost, Photo, LinkPost, AnswerPost, QuotePost, ConversationPost, \
    ConversationLine, VideoPost, AudioPost

# mini = True
mini = False


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
        # if post_element["type"] == "audio":
        #     player_tag = post_element.find("audio-player")
        #     if "tumblr_audio_player" in player_tag.text:
        #         subsoup = BeautifulSoup(player_tag.text.strip(), "lxml")
        #         src = subsoup.find("iframe")["src"]
        #         audio_file = src[src.index("?audio_file=") + len("?audio_file="):]
        #         audio_file = urllib.parse.unquote(audio_file)
        #
        #         if not audio_file.endswith(".mp3"):
        #             identifier = audio_file[audio_file.index("tumblr_"):]
        #             audio_file = f"https://a.tumblr.com/{identifier}o1.mp3"
        #
        #         print(audio_file)


def add_post(post):
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

        regular_post.regular_title = title_tag.text.strip() if title_tag else None
        regular_post.regular_body = body_tag.text.strip() if body_tag else None

        db.session.add(regular_post)
    elif post["type"] == "photo":
        photo_post = PhotoPost(id=post["id"])

        caption_tag = post.find("photo-caption")
        if caption_tag:
            photo_post.photo_caption = caption_tag.text.strip()

        # Only photosets have photo tags as children
        is_photoset = False if len(post.find_all("photo")) == 0 else True

        photos = []
        # TODO: combine these two cases intelligently maybe possibly perhaps
        if is_photoset:
            # Here, we ignore the base photo-url tags
            photo_tags = post.find_all("photo")

            for i, photo_tag in enumerate(photo_tags):
                photo_url_tags = photo_tag.find_all("photo-url")

                for img in photo_url_tags:
                    img_url = img.text.strip()
                    caption = photo_tag["caption"] or None
                    this_photo = Photo(post_id=post["id"], caption=caption, offset=i + 1,
                                       max_width=img["max-width"], url=img_url)
                    photos.append(this_photo)
        else:
            photo_url_tags = post.find_all("photo-url")

            for img in photo_url_tags:
                img_url = img.text.strip()
                this_photo = Photo(post_id=post["id"], offset=0, max_width=img["max-width"], url=img_url)
                photos.append(this_photo)

        for photo in photos:
            db.session.add(photo)
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

        line_tags = post.find_all("line")
        lines = []
        for index, line_tag in enumerate(line_tags):
            line_text = line_tag.text.strip()
            this_line = ConversationLine(post_id=post["id"], line_num=index + 1, text=line_text)
            lines.append(this_line)
            db.session.add(this_line)

        conv_post.lines = lines
        db.session.add(conv_post)
    elif post["type"] == "video":
        video_post = VideoPost(id=post["id"])

        caption_tag = post.find("video-caption")
        player_tag = post.find("video-player")
        video_post.caption = caption_tag.text.strip() if caption_tag else None
        video_post.player = player_tag.text.strip() if player_tag else None

        if post.find("revision") is None:
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


if __name__ == "__main__":
    main()
