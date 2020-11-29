from loader import Loader
from app import Runner
import os
import argparse
import sys


# build commend: pyinstaller --hidden-import=pkg_resources.py2_warn -F main.py --add-data "templates;templates" -n localizr
def main():
    parser = argparse.ArgumentParser(description="Loads and hosts a Tumblr blog download as a local website.")
    dogroup = parser.add_mutually_exclusive_group(required=True)
    dogroup.add_argument("-l", "--load", metavar="posts_xml", type=str, help="Load mode, using the posts.xml file for "
                                                                             "a blog.")
    dogroup.add_argument("-r", "--run", metavar="blog_name", type=str, help="The name of an already loaded blog to run."
                                                                            " All other arguments are ignored.")
    mgroup = parser.add_mutually_exclusive_group(required=False)
    mgroup.add_argument("-n", "--online",
                        action="store_true",
                        help="""
                                Load the blog's posts using the online method.
                                This method will not require an internet connection to load the blog into the database,
                                but will require an internet connection to view images and other linked media,
                                such as audio and video posts. Text posts will always work fine.
                                If content such as images or video has been removed since being posted on Tumblr,
                                that content will not be present using this method.
                                This is the default if no method is specified.
                             """
                        )
    mgroup.add_argument("-f", "--offline",
                        # action="store_true",
                        metavar="blog_name",
                        nargs="?",
                        default="not_present",
                        const="",
                        help="""
                                Load the blog's posts using the offline method.
                                This method assumes the media folder provided by Tumblr's blog download is in the same
                                folder as this program. The media folder contains all images, audio, and video you've
                                reblogged or posted, and will be used as the source of images, rather than Tumblr's
                                servers. This means you can view your posts exactly as they were when you downloaded
                                your blog, without an internet connection - if posts or content have been deleted
                                since your download, they will still be present with this method.
                                This method requires an internet connection to fill in gaps in content.
                                If your blog title has changed since your export, you must specify it
                                with this option, or it will not work.
                             """
                        )
    parser.add_argument("-m", "--monolithic",
                        action="store_true",
                        help="""
                                Another form of offline method - offline mode must be enabled.
                                Inserts all images, videos, and audio files into the database file along with your
                                posts. If this is enabled, you will not be able to fix media that was not available.
                                The advantage with this option is that you will no longer need the media folder,
                                everything will be kept in the database file. On the other hand, you will not be able
                                to fix missing or broken media, and requires three times the media folder size amount of
                                disk space in order to process properly. Without this option, you need only twice the
                                media folder size to process properly.
                             """)
    parser.add_argument("-p", "--fix-photosets",
                        # action="store_true",
                        metavar="blog_name",
                        nargs="?",
                        default="not_present",
                        const="",
                        help="""
                                Load photosets properly by connecting to Tumblr to get the information for their layout.
                                Without this, photosets will consist of the photos stacked on top of each other.
                                Can only be specified when loading a blog. Reduces load speed considerably.
                                If your blog title has changed since your export, you must specify it
                                with this option, or it will not work.
                             """)

    args = parser.parse_args()

    if args.run:
        r = Runner(args.run)
        r.run_site()
    elif args.load:
        if not os.path.exists(args.load):
            print(f"couldn't find file {args.load}. aborting!")
            return
        else:
            # get options
            offline_mode = not args.offline == "not_present"
            fix_photosets = not args.fix_photosets == "not_present"
            monolithic = args.monolithic

            mode = "offline" if offline_mode else "online"

            if monolithic and mode == "online":
                print("monolithic mode is only available with offline mode.")
                return

            blog_name = ""
            if fix_photosets:
                if fix_photosets != "present":
                    blog_name = args.fix_photosets

            if offline_mode:
                if fix_photosets:
                    if args.offline != blog_name:
                        print("if specifying a blog name for offline mode and photoset mode, please use the same name")
                        return
                blog_name = args.offline

            extra = ""
            if blog_name:
                extra = f" with blog name {blog_name}"
            print(f"loading posts from {args.load} in {mode} mode{extra}")

            if fix_photosets:
                print(f"fixing photosets{extra}")

            basepath = ""
            if getattr(sys, "frozen", False):
                basepath = os.path.dirname(sys.executable)
            if offline_mode and not os.path.exists(os.path.join(basepath, "media")):
                print("could not locate a media folder in the same folder as localizr.exe")
                print("if this was a mistake, please press Control-C to quit and move the folder")
                print("otherwise, please note that in offline mode without a media folder, all media")
                print("will be downloaded - this may take a LONG time")

            l = Loader(args.load)
            l.load_soup()
            counts = l.count_post_types()
            for ptype in counts.keys():
                print(f"found {counts[ptype]} {ptype} post(s)")

            l.init_db()
            l.insert_posts(fix_photosets, blog_name, offline_mode, args.monolithic)


if __name__ == "__main__":
    main()
