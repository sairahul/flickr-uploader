#!/usr/bin/env python

import os
import sys
import time
import glob
import sqlite3
import logging
import traceback
from optparse import OptionParser

import flickrapi

# API Key. You can get it from http://www.flickr.com/services/apps/create/noncommercial/?
API_KEY = ""
# API Secret
API_SECRET = ""
IMAGE_EXTENSIONS = ["jpg","jpeg","bmp","gif","png","tif","tiff","mov","mpg","mpeg","mp4","avi","wmv","3g2","3gp","m4v","asf"]

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def get_ext(file_name):
    return file_name.split(".")[-1].lower()

def is_image(file_name):
    ext = get_ext(file_name)
    if ext in IMAGE_EXTENSIONS:
        return True

    return False

def cursor(_dir):
    db_file = os.path.join(_dir, "flickr.sqlite")
    conn = sqlite3.connect(db_file)
    curr = conn.cursor()
    curr.execute("create table if not exists flickr_images (file text primary key, status text)")
    return conn, curr

def is_uploaded(curr, _file):
    curr.execute("select status from flickr_images where file = ?", (_file,))
    result = curr.fetchall()

    status = (result and result[0] and result[0][0]) or ""
    if status.lower() == "ok":
        logger.debug("Uploaded before. skipping %s"%(_file))
        return True

    return False

def upload_file(curr, conn, flickr, _file, update_tag, tag):
    rsp = None
    time_taken = 0
    try:
        t1 = time.time()
        if update_tag:
            rsp = flickr.upload(_file, tags=tag)
        else:
            rsp = flickr.upload(_file)

        time_taken = time.time() - t1
    except:
        logger.error(''.join(traceback.format_exception(*sys.exc_info()[:3])))
    else:
        if rsp and rsp.attrib and rsp.attrib["stat"].lower() == "ok":
            curr.execute("insert or replace into flickr_images (file, status) values (?, ?)",(_file, "ok"))
            conn.commit()
            return True, time_taken
        else:
            logger.error("Couldn't upload: %s :(, - rsp: %s "%(_file, rsp.attrib))

    return False, time_taken

def upload_to_flickr(update_tag, src_dirs):
    flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET)
    (token, frob) = flickr.get_token_part_one(perms='write')
    if not token: raw_input("Press ENTER after you authorized this program")
    flickr.get_token_part_two((token, frob))

    for _dir in src_dirs:
        if not os.path.exists(_dir):
            logger.error("%s directory does not exist !"%(_dir))
            continue

        files_to_upload = glob.glob(os.path.join(_dir,"*"))
        conn, curr = cursor(_dir)

        _uploaded = _errors = _skipped = total_time = 0

        tag = _dir.split("/")[-1]
        tag = repr(tag.strip())
        for _file in files_to_upload:
            if not is_image(_file):
                _skipped  += 1
                logger.error("Not an image. skipping .. %s"%(_file))

            if is_uploaded(curr, _file):
                _skipped  += 1
                continue

            logger.debug("Uploading %s ..."%(_file))

            uploaded, time_taken = upload_file(curr, conn, flickr, _file, update_tag, tag)
            total_time += time_taken
            if uploaded:
                _uploaded += 1
            else:
                _errors += 1


        _avg = (_uploaded and (total_time / float(_uploaded))) or 0
        logger.info("Dir Completed: %s"%(_dir))
        logger.info("Uploaded: %s\nErrors: %s\nSkipped: %s\nTotal: %s\nTotal Time:%s(s)\nAvg Upload Time: %s(s)"%(_uploaded, _errors, _skipped, len(files_to_upload), total_time, _avg))

        curr.close()
        conn.close()

if __name__=="__main__":
    parser = OptionParser()
    parser.add_option("-t", "--tags",
                     action="store_true", default=False,
                     help="Tag all the photos with the directory name.")

    parser.add_option("-f", "--file", dest="filename",
                     help="File contains list of directories to upload.",
                     metavar="FILE")
    (options, args) = parser.parse_args()

    src_dirs = args
    if options.filename:
        if not os.path.exists(options.filename):
            raise IOError("No such file or directory: %s"%options.filename)

        dirs = [line.strip() for line in open(options.filename) if line.strip()]
        src_dirs.extend(dirs)

    upload_to_flickr(options.tags, src_dirs)

