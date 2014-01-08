import random
import logging
import time
from itertools import count
import subprocess
import flask
from flask.ext.rq import job
from flask.ext.script import Manager
from werkzeug.wsgi import FileWrapper
import requests
from path import path
from hambar import models
from hambar.utils import get_result, temp_dir

harvest_manager = Manager()

PAGE_JPG_URL = ('http://www.expert-monitor.ro:8080'
                '/Monitoare/{year}/{part}/{number}/Pozemartor/{page}.jpg')
URL_FORMAT = ('http://www.monitoruloficial.ro/emonitornew/php/services'
              '/view.php?doc={code}&%66or%6d%61t=%70d%66')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_mof_url(mof):
    part_number = 1 if mof.part == 1 else mof.part + 1
    code = '%02d%04d%04d' % (part_number, mof.year, mof.number)
    return URL_FORMAT.format(code=code)


def download(url, out_file):
    agent_url = flask.current_app.config.get('HAMBAR_AGENT_URL')
    if agent_url is None:
        logger.info("Fetching %s (direct)", url)
        resp = requests.get(url, stream=True)

    else:
        logger.info("Fetching %s (agent)", url)
        resp = requests.post(agent_url, data={'url': url}, stream=True)

    if resp.status_code == 404:
        return False
    elif resp.status_code == 200:
        for chunk in FileWrapper(resp.raw):
            out_file.write(chunk)
        return True
    else:
        raise RuntimeError("Can't understand status code %d", resp.status_code)


@harvest_manager.option('number', type=int)
@harvest_manager.option('part', type=int)
@harvest_manager.option('-f', '--fetch', action='store_true')
def new_editions(part, number, fetch=False):
    year = 2014
    latest_known = (models.Mof.query
                             .filter_by(year=year, part=part)
                             .order_by('-number')
                             .first())
    next_number = 1 if latest_known is None else latest_known.number + 1
    n = 0
    for number in range(next_number, number + 1):
        row = models.Mof(year=year, part=part, number=number)
        if fetch:
            row.fetchme = True
        models.db.session.add(row)
        n += 1
    models.db.session.commit()
    logger.info("Added %d records", n)


@harvest_manager.option('count', type=int)
def fetch(count):
    got_count = 0
    while True:
        models.db.session.rollback()
        mof_pool = (
            models.Mof.query
            .filter(models.Mof.fetchme == True)
            .filter(models.Mof.errors == None)
            .filter(
                (models.Mof.unavailable == None) |
                (models.Mof.unavailable == False)
            )
            .filter(
                (models.Mof.in_local == None) |
                (models.Mof.in_local == False)
            )
        )
        remaining = mof_pool.count()
        if not remaining:
            logger.info("Nothing left to download!")
            break

        lucky = random.randrange(remaining)
        mof = mof_pool.offset(lucky).first()
        url = create_mof_url(mof)

        if mof.local_path.exists():
            logger.info("Skipping %s, already exists", mof.pdf_filename)
            continue

        with mof.local_path.open('wb') as f:
            assert download(url, f)

        out = subprocess.check_output(['file', '-bi', mof.local_path])
        if not out.startswith('application/pdf'):
            mof.errors = "not-pdf"
            mof.local_path.unlink()
        else:
            mof.in_local = True
            mof.fetchme = False
        models.db.session.commit()

        got_count += 1
        if got_count >= count:
            logger.info("Got %d files as requested. Stopping.", count)
            break

        t = random.randint(20, 30)
        logger.info("Sleeping for %d secods", t)
        time.sleep(t)


class S3Bucket(object):

    def __init__(self, bucket_name):
        import boto
        config = flask.current_app.config
        s3 = boto.connect_s3(
            config['AWS_ACCESS_KEY_ID'],
            config['AWS_SECRET_ACCESS_KEY'],
        )
        self.bucket = s3.get_bucket(bucket_name)

    def upload(self, name, local_path):
        from boto.s3.key import Key
        key = Key(self.bucket)
        key.name = name
        key.set_contents_from_filename(local_path)


@harvest_manager.command
def s3upload():
    bucket = S3Bucket(flask.current_app.config['AWS_S3_BUCKET'])
    mof_query = (
        models.Mof.query
        .filter_by(in_local=True)
        .filter(models.Mof.s3_name == None)
    )
    print mof_query.count(), "files to upload"
    for mof in mof_query:
        name = mof.pdf_filename
        print name
        bucket.upload(name, mof.local_path)
        mof.s3_name = name
        models.db.session.commit()


@job
def text_mof(mof_id):
    mof = models.Mof.query.get(mof_id)
    with temp_dir() as tmp:
        text_path = tmp / 'plain.txt'

        if mof.in_local:
            pdf_path = mof.local_path

        else:
            pdf_path = tmp / mof.pdf_filename
            with pdf_path.open('wb') as f:
                resp = requests.get(mof.s3_url, stream=True)
                assert resp.status_code == 200
                for chunk in FileWrapper(resp.raw):
                    f.write(chunk)

        subprocess.check_call(['pdftotext', pdf_path, text_path])
        mof.text = text_path.text(encoding='utf-8')

    models.db.session.commit()


@harvest_manager.command
def text():
    mof_query = (
        models.Mof.query
        .filter(models.Mof.text_row == None)
        .filter((models.Mof.in_local == True) | (models.Mof.s3_name != None))
        .filter(models.Mof.extension == None)
    )
    print mof_query.count(), "texts to add"
    for mof in mof_query:
        text_mof.delay(mof.id)


def ocr(image_path):
    cmd = ['tesseract', image_path, image_path, '-l', 'ron']
    with open('/dev/null', 'wb') as devnull:
        subprocess.check_call(cmd, stderr=devnull)

    text_path = path(image_path + '.txt')
    text = text_path.text(encoding='utf-8')
    image_path.unlink()
    text_path.unlink()
    return text


@job
def get_and_ocr(url):
    with temp_dir() as tmp:
        image_path = tmp / 'page.jpg'

        with image_path.open('wb') as f:
            if not download(url, f):
                return None

        return ocr(image_path)


def get_pages(part, year, number):
    jobs = []
    for p in range(1, 33):
        url = PAGE_JPG_URL.format(year=year, part=part,
                                  number=number, page=p)
        jobs.append(get_and_ocr.delay(url))

    return [r for r in (get_result(j) for j in jobs) if r is not None]


@harvest_manager.option('number_range')
@harvest_manager.option('year', type=int)
@harvest_manager.option('part', type=int)
def get_images(part, year, number_range):
    number_start, number_end = map(int, number_range.split('..'))
    for number in xrange(number_start, number_end):
        t0 = time.time()
        kwargs = {'part': part, 'year': year, 'number': number}

        mof = models.Mof.query.filter_by(**kwargs).first()
        if mof is None:
            mof = models.Mof(**kwargs)
            models.db.session.add(mof)

        if mof.text_json is not None:
            continue

        logger.info("Getting %d/%d/%d", part, year, number)
        pages = get_pages(**kwargs)

        mof.text_json = flask.json.dumps(pages)
        models.db.session.commit()

        logger.info("Got %d/%d/%d, %d pages, %d seconds",
                    part, year, number, len(pages), time.time() - t0)
