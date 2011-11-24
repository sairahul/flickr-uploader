#!/usr/bin/env python

import os
import sys
import time
import glob
import sqlite3
import logging
import traceback

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

def upload_to_flickr(src_dirs):
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

        for _file in files_to_upload:
            if not is_image(_file):
                logger.error("Not an image. skipping .. %s"%(_file))
                _skipped  += 1
                continue

            curr.execute("select status from flickr_images where file = ?", (_file,))
            result = curr.fetchall()

            status = (result and result[0] and result[0][0]) or ""
            if status.lower() == "ok":
                _skipped  += 1
                logger.debug("Uploaded before. skipping %s"%(_file))
                continue

            logger.debug("Uploading %s ..."%(_file))

            rsp = {}
            try:
                t1 = time.time()
                rsp = flickr.upload(_file)
                total_time += (time.time() - t1)
            except:
                logger.error(''.join(traceback.format_exception(*sys.exc_info()[:3])))
                _errors += 1
            else:
                if rsp and rsp.attrib and rsp.attrib["stat"].lower() == "ok":
                    _uploaded += 1
                    curr.execute("insert or replace into flickr_images (file, status) values (?, ?)",(_file, "ok"))
                    conn.commit()
                else:
                    logger.error("Couldn't upload: %s :(, - rsp: %s "%(_file, rsp.attrib))
                    _errors += 1

        _avg = (_uploaded and (total_time / float(_uploaded))) or 0
        logger.info("Dir Completed: %s"%(_dir))
        logger.info("Uploaded: %s\nErrors: %s\nSkipped: %s\nTotal: %s\nTotal Time:%s(s)\nAvg Upload Time: %s(s)"%(_uploaded, _errors, _skipped, len(files_to_upload), total_time, _avg))

        curr.close()
        conn.close()

if __name__=="__main__":
    src_dirs = sys.argv[1:]
    upload_to_flickr(src_dirs)

