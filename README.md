# localizr
localizr is an application designed to allow you to host a Tumblr blog's download archive as a standalone website.

The current state of localizr on the development side is as follows:
 - [x] Database model of data from the posts.xml file
 - [x] Local hosting of a blog
 - [x] Online mode which uses links to media still hosted by Tumblr
 - [x] Offline mode with uses the media folder and downloads supplemental media from Tumblr
 - [x] All post types supported by both online and offline methods of loading
 - [x] Photoset arrangement support without loading the iframe from Tumblr every time
 - [x] More features than a Tumblr blog with the addition of self/ and type/ endpoints to display only original posts, or sort by post type
 - [x] Full support for changed blog URLs
 - [ ] Fast loading using parallel requests
 - [x] Insert media into database for monolithic blog storage
 - [ ] Theme support
 - [ ] A user friendly GUI
 - [ ] Support for the messages.xml with an interface for viewing messages
 
As of now, development is relatively finished outside of bug fixes. Unfinished features listed here are distant goals that I may not complete. See Contributions as PRs are welcome.

## How to use localizr
localizr comes with a simple command-line interface.
You should obtain your posts.xml file from the zip file you downloaded from Tumblr of your blog archive. You can load a blog by typing:
```
localizr.exe -l posts.xml [--online | --offline [blog_name]] [--monolithic] [--fix-photosets [blog_name]]
```
where `-l` means "load", `(posts.xml)` is the required path to the posts.xml file of the blog you want to load, `[--online | --offline [blog_name]]` are optional, as online mode is the default, and `--fix-photosets` is to process accurate photoset arrangements, which is an option because it requires an internet connection and reduces speed. `--monolithic` is also an option for blog storage, but limits your ability to fix your blog after localizr loads it.

Loading a blog will create a "blogname.db" file in the same folder as localizr.
To display that blog as a website, run:
```
localizr.exe -r (blogname)
```
Your default web browser should open to `http://localhost:5000/welcome`. This welcome page provides information on how to navigate the localizr website using tags, pages, and features Tumblr never had, such as self/ and type/.

## Online mode
Online mode exists for users simply looking to access their blog posts in a user-friendly manner, for example, if a blog has been deactivated. In the case of a deactivated blog, photoset arrangements and audio posts will not function properly. This is the fastest method of loading a blog and only takes about 3 minutes with tens of thousands of posts without processing photoset arrangements.
## Offline mode
Offline mode exists so that a user can create a full copy of their blog as it once was, including reblogged media such as images, video, and audio. In online mode, audio and video posts still access Tumblr's servers to obtain media. In offline mode, the localizr website is completely standalone - and will function the same even if you don't have an internet connection, after loading is done, as long as the media folder is in the same folder as localizr.exe. In addition, the media folder should be in the same folder as localizr.exe to load the blog initially, and localizr will not clean up the media folder afterwards. Because some media may still be missing or incorrectly downloaded, it is up to the user to delete the original media folder as to prevent data loss. This is an important step because the media folder can be tens of gigabytes in size.
Offline mode decreases load speed drastically because the blog download does not include all of the media that it should, so localizr downloads that media from Tumblr's servers, provided it's still online.
## Monolithic mode
Monolithic mode is another form of offline mode. Rather than creating a media directory and serving files from there, monolithic mode will place all media into the database used for post content. With this option, you will not have access to the data that localizr serves as media - and you will not be able to fix any media. However, when storing your blog, the only two files you need would be localizr and the database.
## Photoset arrangements
Photosets are a huge part of Tumblr. In order to get them to work properly, localizr needs to know which row which image is on in the photoset. Unfortunately, this information is not included in the posts.xml file Tumblr includes with blog downloads, so the `--fix-photosets` option tells localizr to load the information for each photoset from Tumblr.

# Known Issues
Due to the nature of Tumblr's export on top of using internet connections and taking up to multiple hours, offline mode is extremely unpredictable. I've done my best to mitigate this behavior by having localizr continue where it left off on subsequent loads, and having almost no outright failure states. Any post where something doesn't go exactly as expected is logged and can be fixed manually later. A few different issues can occur, such as:
- Missing audio, video, or images that cannot be downloaded
- Images that were downloaded, but instead download the community guidelines notice
    - This is due to the way that localizr handles video and audio posts. Both video and audio posts copy the video or audio, but download the poster/cover art and all caption images, regardless of if they are in the media folder. This means users can fix this issue manually.
- Images that were copied from the media folder but were actually the copyright notice
- (In photoset mode) Photosets that localizr was unable to get row data for

It's not always easy but using an SQLite tool such as SQLiteStudio or copying the proper post files from the media folder will allow you to fix these issues.

# Contributing
localizr is open source for a reason. If you would like to add support for one of the listed features that hasn't been complete, feel free to submit a pull request. Otherwise, still feel free to use localizr's database loading feature to your heart's content. It may be useful for blog analytics or batch processing or exporting or otherwise.