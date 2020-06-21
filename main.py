from loader import Loader
from app import Runner
import os
import argparse


def main():
    parser = argparse.ArgumentParser(description="Loads and hosts a Tumblr blog download as a local website.")
    dogroup = parser.add_mutually_exclusive_group(required=True)
    dogroup.add_argument("-l", "--load", metavar="posts_xml", type=str, help="Load mode, using the posts.xml file for "
                                                                            "a blog.")
    dogroup.add_argument("-r", "--run", metavar="blog_name", type=str, help="The name of an already loaded blog to run. "
                                                                           "All other arguments are ignored.")
    mgroup = parser.add_mutually_exclusive_group(required=False)
    mgroup.add_argument("-n", "--online", action="store_true",
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
                        # metavar="media_folder", type=str,
                        action="store_true",
                        help="""
                                Load the blog's posts using the offline method.
                                This method assumes the media folder provided by Tumblr's blog download is in the same
                                folder as this program. The media folder contains all images, audio, and video you've
                                reblogged or posted, and will be used as the source of images, rather than Tumblr's
                                servers. This means you can view your posts exactly as they were when you downloaded
                                your blog, without an internet connection - if posts or content have been deleted
                                since your download, they will still be present with this method.
                             """
                        )
    parser.add_argument("-p", "--fix-photosets", action="store_true",
                        help="""
                                Load photosets properly by connecting to Tumblr to get the information for their layout.
                                Without this, photosets will consist of the photos stacked on top of each other.
                                Can only be specified when loading a blog. Reduces load speed considerably. 
                             """)

    args = parser.parse_args()

    if args.run:
        r = Runner(args.run)
        r.run_site()

    if args.load:
        if not os.path.exists(args.load):
            print(f"Couldn't find file {args.load}. Aborting!")
            return
        else:
            l = Loader(args.load)
            l.load_soup()
            counts = l.count_post_types()
            for ptype in counts.keys():
                print(f"found {counts[ptype]} {ptype} post(s)")
            l.init_db()
            l.insert_posts(args.fix_photosets)




if __name__ == "__main__":
    main()
