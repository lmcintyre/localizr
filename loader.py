import os
import shutil
import sys

import eyed3
import requests
import inspect
import contextlib
import tqdm
import mimetypes
import logging
import traceback
from bs4 import BeautifulSoup
from PIL import Image
from app import Runner, app, basepath
from model import db, Tag, Post, RegularPost, PhotoPost, Photo, LinkPost, AnswerPost, QuotePost, ConversationPost, \
    ConversationLine, VideoPost, AudioPost


request_session = requests.Session()
request_session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36"})


# this is from https://stackoverflow.com/a/42424890/1701048
# it allows for clean output during tqdm drawing, but not in pycharm
@contextlib.contextmanager
def redirect_to_tqdm():
    # Store builtin print
    old_print = print

    def new_print(*args, **kwargs):
        # If tqdm.tqdm.write raises error, use builtin print
        try:
            tqdm.tqdm.write(*args, **kwargs)
        except:
            old_print(*args, **kwargs)

    try:
        # Globaly replace print with new_print
        inspect.builtins.print = new_print
        yield
    finally:
        inspect.builtins.print = old_print


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

    def insert_posts(self, fix_photosets, blog_name="", offline_mode=False):
        if self.soup is None:
            raise ValueError("Loader's soup was None")

        posts = []
        ids = []

        eyed3.log.disabled = True
        eyed3.utils.log.disabled = True
        eyed3.log.setLevel(logging.CRITICAL)
        eyed3.utils.log.setLevel(logging.CRITICAL)

        post_index = 0
        with app.app_context():
            for post in tqdm.tqdm(self.soup.find_all("post")):
                if not Post.query.get(post["id"]) and post["id"] not in ids:
                    with redirect_to_tqdm():
                        try:
                            # print(f"processing post {post['id']}...")
                            base, specific = add_post(post, fix_photosets, blog_name, offline_mode)
                            posts.append(base)
                            posts.append(specific)
                            ids.append(post["id"])

                            post_index = post_index + 1
                            if post_index % 1000 == 0:
                                db.session.add_all(posts)
                                db.session.commit()
                                posts.clear()
                                ids.clear()
                        except Exception as e:
                            if isinstance(e, KeyboardInterrupt):
                                raise
                            print(traceback.format_exc())
                            print(f"encountered an error loading post {post['id']} {e}")

            print("posts loaded, committing changes to database...")

            db.session.add_all(posts)
            db.session.commit()
            print("done!")

        if offline_mode:
            if os.path.exists(os.path.join(basepath, "media_old")):
                print("found a 'media_old' folder, please handle renaming media_tmp and media_old manually")
                print("or, delete 'media_old' and 'media_tmp' and load the blog again.")
            else:
                os.rename(os.path.join(basepath, "media"), os.path.join(basepath, "media_old"))
                os.rename(os.path.join(basepath, "media_tmp"), os.path.join(basepath, "media"))
                print("most blog media is now located in the 'media' folder in the same directory as this program.")
                print("it is recommended to run through the error messages and replace community guideline notices,")
                print("copyright notices, and other images with the proper images from the 'media_old' folder, to")
                print("obtain the most accurate representation of your blog.")
                print("otherwise, if you don't care, you can delete the 'media_old' folder entirely.")
                print("as this program does not delete files, i am not responsible for lost data.")


def get_photoset_iframe_url(post, blog_name=""):
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
        page = request_session.get(iframe_url).content
    except requests.exceptions.RequestException:
        print(f"couldn't load photoset data for post {post['id']}")
        return None

    # only html.parser works here?
    soup = BeautifulSoup(page, "html.parser")
    row_counts = []
    for tag in soup.select(".photoset_row"):
        for css_class in tag["class"]:
            if "row_" in css_class:
                row_counts.append(int(css_class[css_class.rindex("_") + 1:]))
    image_rows = []
    for row_index, val in enumerate(row_counts):
        for index in range(0, val):
            image_rows.append(row_index + 1)
    return image_rows


def is_copyright(file):
    if os.stat(file).st_size == 62512:
        try:
            with Image.open(file) as img:
                width, height = img.size
                if width == 1280 and height == 960:
                    return True
        except ValueError:
            return False
        return False


def add_post(post, fix_photosets, blog_name="", offline_mode=False):
    tag_list = []
    for tag_element in post.find_all("tag"):
        this_tag = Tag(post_id=post["id"], tag=tag_element.text.strip())
        tag_list.append(this_tag)

    base_post = Post(
        id=post["id"],
        # url=post["url"],
        # url_with_slug=post["url-with-slug"],
        # slug=post["slug"],
        type=post["type"],
        # state=post["state"],
        # date_gmt=post["date-gmt"],
        # date=post["date"],
        unix_timestamp=post["unix-timestamp"],
        # format=post["format"],
        # reblog_key=post["reblog-key"],
        is_reblog=post["is_reblog"],
        tumblelog=post["tumblelog"],
        tags=tag_list,

        # private=post.get("private", "false"),

        # width=int(post.get("width")) if post.get("width") else None,
        # width=post.get("width"),
        # height=post.get("height"),

        # direct_video=post.get("direct-video"),

        audio_plays=post.get("audio-plays")
    )

    if offline_mode:
        replace_links(post, blog_name)

    specific_post = None
    if post["type"] == "regular":
        specific_post = make_regular(post)
    elif post["type"] == "photo":
        specific_post = make_photo(post, fix_photosets, blog_name)
    elif post["type"] == "link":
        specific_post = make_link(post)
    elif post["type"] == "answer":
        specific_post = make_answer(post)
    elif post["type"] == "quote":
        specific_post = make_quote(post)
    elif post["type"] == "conversation":
        specific_post = make_conversation(post)
    elif post["type"] == "video":
        specific_post = make_video(post)
    elif post["type"] == "audio":
        specific_post = make_audio(post)

    return base_post, specific_post


def make_regular(post):
    regular_post = RegularPost(id=post["id"])

    title_tag = post.find("regular-title")
    body_tag = post.find("regular-body")

    regular_post.title = title_tag.text.strip() if title_tag else None
    regular_post.caption = body_tag.text.strip() if body_tag else None
    return regular_post


def make_photo(post, fix_photosets, blog_name):
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

        rows_per_image = None
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
                        try:
                            this_photo.row = rows_per_image[i]
                        except IndexError:
                            # print(f"encountered IndexError for index {i} on post {post['id']}")
                            # print(f"rows per image: {rows_per_image}")
                            print(f"unable to obtain the row for image {i + 1} for post {post['id']} - this photoset "
                                  f"will not display properly.")
                            rows_per_image = None
                            for photo in photos:
                                photo.row = None
                            this_photo.row = None

                    photos.append(this_photo)
    else:
        photo_url_tags = post.find_all("photo-url")

        for img in photo_url_tags:
            if img["max-width"] == "1280":
                img_url = img.text.strip()
                this_photo = Photo(post_id=post["id"], offset=0, url=img_url)
                photos.append(this_photo)

    photo_post.is_photoset = is_photoset
    photo_post.photos = photos
    return photo_post


def make_link(post):
    link_post = LinkPost(id=post["id"])

    text_tag = post.find("link-text")
    url_tag = post.find("link-url")
    desc_tag = post.find("link-description")

    link_post.text = text_tag.text.strip() if text_tag else None
    link_post.url = url_tag.text.strip() if url_tag else None
    link_post.desc = desc_tag.text.strip() if desc_tag else None
    return link_post


def make_answer(post):
    answer_post = AnswerPost(id=post["id"])

    question_tag = post.find("question")
    answer_tag = post.find("answer")

    answer_post.question = question_tag.text.strip() if question_tag else None
    answer_post.answer = answer_tag.text.strip() if answer_tag else None
    return answer_post


def make_quote(post):
    quote_post = QuotePost(id=post["id"])

    text_tag = post.find("quote-text")
    source_tag = post.find("quote-source")

    quote_post.text = text_tag.text.strip() if text_tag else None
    quote_post.source = source_tag.text.strip() if source_tag else None
    return quote_post


def make_conversation(post):
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
        # db.session.add(this_line)

    conv_post.lines = lines
    return conv_post


def make_video(post):
    video_post = VideoPost(id=post["id"])

    caption_tag = post.find("video-caption")
    player_tag = post.find("video-player")
    video_post.caption = caption_tag.text.strip() if caption_tag else None

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

    # if we're using local media, we won't be linking to tumblr here
    # so this case catches both embedded videos and local media
    if "tumblr.com/" not in player_tag.text.strip():
        video_post.player = player_tag.text.strip() if player_tag else None
        video_post.source = post.find("video-source").text.strip()
    else:
        # transform the video tag to reference the direct video source
        soup2 = BeautifulSoup(player_tag.text.strip(), "html.parser")

        # this adds the necessary attribute to display video controls
        soup2.find("video")["controls"] = None

        src_tag = soup2.find("source")
        src_text = src_tag["src"]
        new_src = get_src_url(src_text, video_post.extension)
        src_tag["src"] = new_src
        video_post.player = str(soup2)
    return video_post


def make_audio(post):
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

    return audio_post


def get_src_url(old_src, extension):
    va_format = "https://va.media.tumblr.com/{}.{}"
    src = old_src[old_src.index("tumblr_"):]
    try:
        src = src[0:src.rindex("/")]
    except ValueError:
        pass

    return va_format.format(src, extension)


def process_caption(post, caption_tag, offset):
    caption_text = caption_tag.text.strip() if caption_tag else None
    if caption_text:
        soup2 = BeautifulSoup(caption_text, "html.parser")
        for index, image in enumerate(soup2.find_all("img")):
            url = image["src"]
            path = process_imgfile(post, index + offset, url)
            image["src"] = f"/{path}"
        return soup2


def replace_links(post, blog_name):
    if post["type"] == "regular":
        caption_tag = post.find("regular-body")
        if caption_tag:
            caption_tag.string = str(process_caption(post, caption_tag, 0))

    elif post["type"] == "photo":
        is_photoset = False if len(post.find_all("photo")) == 0 else True
        if not is_photoset:
            url, path = None, None

            # we don't want to download a tiny image, so always go with the biggest
            for photo_url_tag in post.find_all("photo-url"):
                if photo_url_tag["max-width"] == "1280":
                    # only trust id here, so give it -1
                    url = photo_url_tag.text.strip()
                    path = process_imgfile(post, -1, url)

            # set the tags
            for photo_url_tag in post.find_all("photo-url"):
                photo_url_tag.string = f"/{path}"

            # here, we always ignore images with _0 suffix. assume they are useless
            caption_tag = post.find("photo-caption")
            if caption_tag:
                caption_tag.string = str(process_caption(post, caption_tag, 1))

        if is_photoset:
            for index, photo_tag in enumerate(post.find_all("photo")):
                url, path = None, None

                for photo_url_tag in photo_tag.find_all("photo-url"):
                    if photo_url_tag["max-width"] == "1280":
                        url = photo_url_tag.text.strip()
                        path = process_imgfile(post, index, url)

                for photo_url_tag in photo_tag.find_all("photo-url"):
                    photo_url_tag.string = f"/{path}"

            # this number is the zero-based index where we start
            # counting the caption image indices
            oindex = len(post.find_all("photo")) * 2

            caption_tag = post.find("photo-caption")
            if caption_tag:
                caption_tag.string = str(process_caption(post, caption_tag, oindex))
    elif post["type"] == "link":
        caption_tag = post.find("link-desc")
        if caption_tag:
            caption_tag.string = str(process_caption(post, caption_tag, 0))
    elif post["type"] == "answer":
        caption_tag = post.find("answer")
        if caption_tag:
            caption_tag.string = str(process_caption(post, caption_tag, 0))
    elif post["type"] == "quote":
        caption_tag = post.find("quote-source")
        if caption_tag:
            caption_tag.string = str(process_caption(post, caption_tag, 0))
    elif post["type"] == "audio":
        audio_player = post.find("audio-player")
        if "tumblr_audio_player" in audio_player.text.strip():  # only works on tumblr player
            process_audiofile(post, blog_name)
    elif post["type"] == "video":
        video_player = post.find("video-player")
        if "tumblr.com/" in video_player.text.strip():  # only works on tumblr videos
            process_videofile(post, blog_name)


def process_videofile(post, blog_name):
    replacement_format = """<video controls poster="{}"><source src="{}" type="{}"></video>"""

    # requisite parsing
    extension = post.find("extension").text.strip()
    content_type = post.find("content-type").text.strip()

    caption_tag = post.find("video-caption")
    if caption_tag:
        soup2 = BeautifulSoup(post.find("video-caption").text.strip(), "html.parser")
        imgs = soup2.find_all("img")
        for index, img in enumerate(imgs):
            url = img["src"]
            # ignore the filesystem because posters are wack
            path = process_imgfile(post, index, url, True)
            img["src"] = f"/{path}"
        caption_tag.string = str(soup2)

    path = f"{post['id']}.{extension}"
    full_path = os.path.join("media", path)
    dest_path = os.path.join("media_tmp", path)

    video_player = post.find("video-player")
    url, poster = get_online_video_urls(post, video_player, extension, blog_name)

    video_exists = os.path.exists(full_path)

    if video_exists:
        shutil.copyfile(full_path, os.path.join(basepath, dest_path))
    else:
        download_media(url, os.path.join(basepath, dest_path))

    ext = poster[poster.rindex("."):]
    poster_dest = f"{post['id']}_poster{ext}"
    dest_poster_path = os.path.join("media_tmp", poster_dest)

    # we may get a new save path from download_media, as it handles our extensions properly
    poster_dest = download_media(poster, dest_poster_path)

    # this poster filename is different from where we expected to find it, so that's why we handle it differently here
    video_player.string = replacement_format.format(f"/media/{os.path.basename(poster_dest)}", f"/{full_path}", content_type)


def process_audiofile(post, blog_name):
    replacement_format_poster = """<video class="audio_player_video" controls poster="{}"><source src="{}" type="audio/mp3"></video>"""
    replacement_format_noposter = """<audio class="audio_player" controls src="{}"></audio>"""
    # todo: incorporate title and stuff into the template

    caption_tag = post.find("audio-caption")
    if caption_tag:
        soup2 = BeautifulSoup(post.find("audio-caption").text.strip(), "html.parser")
        imgs = soup2.find_all("img")
        for index, img in enumerate(imgs):
            url = img["src"]
            # ignore the filesystem because posters are wack
            path = process_imgfile(post, index, url, True)
            img["src"] = f"/{path}"
        caption_tag.string = str(soup2)

    path = f"{post['id']}.mp3"
    full_path = os.path.join("media", path)
    dest_path = os.path.join("media_tmp", path)

    audio_player = post.find("audio-player")
    url, poster = get_online_audio_urls(post, audio_player, blog_name)

    mp3_exists = os.path.exists(full_path)

    if mp3_exists:
        shutil.copyfile(full_path, os.path.join(basepath, dest_path))
    else:
        tmp_dest_path = os.path.join(basepath, dest_path)
        download_media(url, tmp_dest_path)
        # quit here for audio/poster processing
        if not verify_mp3(tmp_dest_path):
            if os.path.exists(tmp_dest_path):
                os.remove(tmp_dest_path)
            print(f"discarding {dest_path} as it was not a valid mp3 file")
            return "<h3>The media was not found.</h3>"

    dest_poster_path = None
    if poster:
        ext = poster[poster.rindex("."):]
        dest_poster = f"{post['id']}_poster{ext}"
        dest_poster_path = os.path.join("media_tmp", dest_poster)
        dest_poster_path = download_media(poster, os.path.join(basepath, dest_poster_path))

    if poster:
        ret = replacement_format_poster.format(f"/media/{os.path.basename(dest_poster_path)}", f"/{full_path}")
    else:
        ret = replacement_format_noposter.format(f"/{full_path}")

    audio_player.string = ret


def verify_mp3(path):
    return os.path.exists(path) and eyed3.load(path) is not None


def get_online_video_urls(post, video_player, extension, blog_name):
    soup2 = BeautifulSoup(video_player.text.strip(), "lxml")
    video = soup2.find("video")
    source = soup2.find("source")

    poster = video.get("poster")
    url = get_src_url(source["src"], extension)
    if blog_name:
        url = url.replace(post["tumblelog"], blog_name)

    return url, poster


def get_online_audio_urls(post, audio_player, blog_name):
    soup2 = BeautifulSoup(audio_player.text.strip(), "lxml")
    iframe = soup2.find("iframe")
    url = iframe["src"]
    if blog_name:
        url = url.replace(post["tumblelog"], blog_name)
    r = request_session.get(url)
    soup3 = BeautifulSoup(r.content, "lxml")
    native_container = soup3.select_one(".native-audio-container")
    url = native_container["data-stream-url"]
    poster = native_container.get("data-album-art")
    # audio urls do not use blog name, so we don't need to replace
    return url, poster


def process_imgfile(post, index, url, force_download=False):
    ext = url[url.rindex("."):]

    # because 0 is valid, -1 means "don't add a suffix at all"
    index_text = f"_{index}" if index != -1 else ""
    path = f"{post['id']}{index_text}{ext}"
    full_path = os.path.join("media", path)

    partial_dest = "media_tmp"
    dest_path = os.path.join(partial_dest, path)

    if not os.path.exists(partial_dest):
        os.makedirs(partial_dest)

    if force_download:
        download_media(url, dest_path)
        return full_path

    copyright_check = None
    exists = os.path.exists(full_path)

    if exists:
        copyright_check = is_copyright(full_path)
    if exists and copyright_check or not exists:
        download_media(url, os.path.join(basepath, dest_path))
    else:
        shutil.copyfile(full_path, os.path.join(basepath, dest_path))

    # "media_tmp" will become the new "media", so return that
    # so caller can update tags
    return full_path


# attempts to download from a URL, checks the content type, and fixes the save path if so.
# always returns the path saved to, or None if an error occurred
def download_media(url, savepath):
    error_path = os.path.basename(savepath[savepath.rindex(os.sep) + 1:])

    # try to get rid of queries and colons and stuff
    question = savepath.find("?")
    if question != -1:
        savepath = savepath[:question]

    colon = os.path.basename(savepath).find(":")
    if colon != -1:
        savepath = os.path.join(os.path.dirname(savepath), str(os.path.basename(savepath))[:colon])

    old_savepath = savepath
    old_error_path = os.path.basename(savepath[savepath.rindex(os.sep) + 1:])
    if os.path.exists(savepath):
        # print(f"skipping {savepath[savepath.rindex(os.sep) + 1:]} because it already exists")
        return savepath
    try:
        file = request_session.get(url)
        content_type = file.headers.get("Content-Type")

        ext = None
        if content_type:
            semi = content_type.find(";")
            if semi != -1:
                content_type = content_type[:semi]
            ext = mimetypes.guess_extension(content_type)
            if ext == ".html":
                print(f"download of {error_path} resulted in an html file, discarding")
                return old_savepath

        if ext is not None and not savepath.endswith(ext) and not savepath.endswith("mp3"):
            new_base = savepath[:savepath.index(".")]
            savepath = f"{new_base}{ext}"
            error_path = os.path.basename(savepath[savepath.rindex(os.sep) + 1:])

        reason = file_valid(file.content)
        if reason != "success":
            print(f"download of {old_error_path} failed because {reason}")
            return old_savepath

        with open(savepath, "w+b") as img:
            img.write(file.content)
            if len(file.history) > 0:
                print(f"download of {error_path} successful, but followed a redirect -"
                      " double check this post manually")
        return savepath
        # lets not print success messages, spam
        # else:
        #     print(f"download of {savepath[savepath.rindex(os.sep) + 1:]} success")
    except OSError as err:
        err_text = str(err)
        if "Max retries" in err_text:
            err_text = f"couldn't connect to {url}"
        print(f"download of {old_error_path} failed: {err_text}")
        # this is only necessary for filling out database with info when a file can't be downloaded
        # this way the user can replace the file if they do have it
        return old_savepath


def file_valid(content):
    access_strs = ["Access Denied", "AccessDenied", "Authorization Required"]
    fof_strs = ["not be found", "Not Found"]
    access_bytes = map(lambda x: bytes(x, encoding="ascii"), access_strs)
    fof_bytes = map(lambda x: bytes(x, encoding="ascii"), fof_strs)

    access = access_strs
    fof = fof_strs

    if isinstance(content, bytes):
        access = access_bytes
        fof = fof_bytes

    for test in access:
        if test in content:
            return "access was denied"
    for test in fof:
        if test in content:
            return "of a 404 error"

    return "success"
