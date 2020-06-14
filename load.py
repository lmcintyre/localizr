
from bs4 import BeautifulSoup
from collections import defaultdict
from model import db, Post, PhotoPost, RegularPost

def main():
    with open("posts.xml", encoding="utf-8") as posts:
        text = posts.read()
    soup = BeautifulSoup(text, "xml")

    # used_attrs = defaultdict(list)
    used_descendants = defaultdict(list)

    post_tags = soup.find_all("post")
    print("loaded")

    # with open("posts_formatted.xml", "w", encoding="utf-8") as out:
    #     out.write(soup.prettify())
    i = 0
    for post_element in post_tags:
        if i >= 10:
            return

        # add_post(post_element)
        post_type = post_element["type"]
    #     for attr in post_element.attrs.keys():
    #         if attr not in used_attrs[post_type]:
    #             used_attrs[post_type].append(attr)
    #
        for child in post_element.children:
            # print(f"--\n{child}\n--")
            if child.name not in used_descendants[post_type]:
                used_descendants[post_type].append(child.name)
    #
    # for key in used_attrs.keys():
    #     print(f"{key}: {used_attrs[key]}")
    #
    # for key in used_descendants.keys():
    #     print(f"{key}: {used_descendants[key]}")

def add_post(post):
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
        is_reblog=post["is-reblog"],
        tumblelog=post["tumblelog"],
        private=post["private"],

        width=post["width"],
        height=post["height"],

        direct_video=post["direct-video"],

        audio_plays=post["audio-play"]
    ))

    if post["type"] == "regular":
        regular_post = RegularPost(id=post["id"])

        for child in post.children:
            if child.name == "regular-title":
                regular_post.regular_title = child.text
            elif child.name == "regular-body":
                regular_post.regular_body = child.text

        db.session.add(RegularPost(
            id=post["id"],
            regular_title=post.children["regular-title"],
            regular_body=post.children["regular-body"]
        ))
    elif post["type"] == "photo":
        db.session.add(RegularPost(
            id=post["id"],
            photo_caption=post.children
        ))


if __name__ == "__main__":
    main()
