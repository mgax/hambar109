import random
import logging
import time
from itertools import count
import subprocess
import tempfile
import csv
import flask
from flask.ext.rq import job
from flask.ext.script import Manager
from werkzeug.wsgi import FileWrapper
import requests
from path import path
from hambar.models import Mof, db
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
        logger.debug("Fetching %s (direct)", url)
        resp = requests.get(url, stream=True)

    else:
        logger.debug("Fetching %s (agent)", url)
        resp = requests.post(agent_url, data={'url': url}, stream=True)

    if resp.status_code == 404:
        return False
    elif resp.status_code == 200:
        for chunk in FileWrapper(resp.raw):
            out_file.write(chunk)
        return True
    else:
        raise RuntimeError("Can't understand status code %d", resp.status_code)


@harvest_manager.option('spec', nargs='+')
def new_editions(spec):
    for spec_item in spec:
        (part, number) = (int(i) for i in spec_item.split(':'))
        year = 2015
        latest_known = (
            Mof.query
            .filter_by(year=year, part=part)
            .order_by('-number')
            .first()
        )
        next_number = 1 if latest_known is None else latest_known.number + 1
        n = 0
        for number in range(next_number, number + 1):
            row = Mof(year=year, part=part, number=number, fetchme=True)
            db.session.add(row)
            n += 1
        db.session.commit()
        logger.info("Part %d: added %d records", part, n)


@harvest_manager.command
def fetch():
    while True:
        db.session.rollback()
        mof_pool = (
            Mof.query
            .filter(Mof.fetchme == True)
            .filter(Mof.errors == None)
            .filter(
                (Mof.unavailable == None) |
                (Mof.unavailable == False)
            )
            .filter(
                (Mof.in_local == None) |
                (Mof.in_local == False)
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
            mof.in_local = True
            db.session.commit()
            continue

        temp_path = path(tempfile.mkstemp(dir=mof.local_path.parent)[1])

        with temp_path.open('wb') as f:
            logger.info("Fetching %s", mof.pdf_filename)
            assert download(url, f)

        out = subprocess.check_output(['file', '-bi', temp_path])
        if not out.startswith('application/pdf'):
            mof.errors = "not-pdf"
            temp_path.unlink()
        else:
            temp_path.rename(mof.local_path)
            mof.in_local = True
            mof.fetchme = False
        db.session.commit()

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

    def upload(self, name, data_file):
        from boto.s3.key import Key
        key = Key(self.bucket)
        key.name = name
        key.set_contents_from_file(data_file)


@harvest_manager.command
def s3upload(index_year=None):
    bucket = S3Bucket(flask.current_app.config['AWS_S3_BUCKET'])
    years_to_reindex = set()
    mof_query = (
        Mof.query
        .filter_by(in_local=True)
        .filter(Mof.s3_name == None)
    )
    print mof_query.count(), "files to upload"
    for mof in mof_query:
        name = mof.pdf_filename
        print name
        with open(mof.local_path, 'rb') as f:
            bucket.upload(name, f)
        mof.s3_name = name
        years_to_reindex.add(mof.year)
        db.session.commit()

    if index_year:
        years_to_reindex.add(int(index_year))

    csv_header = ['part', 'year', 'number', 's3_name']
    for year in years_to_reindex:
        print 'Reindexing year', year
        with tempfile.TemporaryFile() as index_tmp:
            index_csv = csv.DictWriter(index_tmp, csv_header)
            year_query = (
                Mof.query
                .filter_by(year=year)
                .filter(Mof.s3_name != None)
                .order_by(Mof.part, Mof.number)
            )
            for mof in year_query:
                index_csv.writerow({k: getattr(mof, k) for k in csv_header})
            index_tmp.seek(0)
            bucket.upload('%d.csv' % year, index_tmp)


@job
def text_mof(pdf_part, pdf_year, pdf_number, pdf_name):

    s3_url = "https://mgax-mof.s3.amazonaws.com"

    pdf_url = s3_url + "/" + pdf_name

    with temp_dir() as tmp:
        pdf_local_path = tmp / pdf_name
        text_path = tmp / 'plain.txt'

        with pdf_local_path.open('wb') as f:
            resp = requests.get(pdf_url, stream=True)
            assert resp.status_code == 200
            for chunk in FileWrapper(resp.raw):
                f.write(chunk)

        subprocess.check_call(['pdftotext', pdf_local_path, text_path])

        with text_path.open('r') as f:
            raw_text = f.read()

        json = dict([('part', int(pdf_part)),
                     ('year', int(pdf_year)),
                     ('number', int(pdf_number)),
                     ('slug', pdf_name.split('.')[0]),
                     ('text', raw_text)])

        resp = requests.put(flask.current_app.config['ELASTIC_SEARCH_URL']
                            + pdf_name.split('.')[0],
                            data=flask.json.dumps(json))
        assert 200 <= resp.status_code < 300, repr(resp)

@harvest_manager.command
def text():
    csv_url = "https://mgax-mof.s3.amazonaws.com/2015.csv"

    resp = requests.get(csv_url, stream=True)
    assert resp.status_code == 200

    for doc in resp.raw:
        pdf_part = doc.split(',')[0].strip()
        pdf_year = doc.split(',')[1].strip()
        pdf_number = doc.split(',')[2].strip()
        pdf_name = doc.split(',')[3].strip()

        # Check whether he have already processed this document.
        es_url = flask.current_app.config['ELASTIC_SEARCH_URL']
        slug = pdf_name.split('.')[0]
        resp = requests.head(es_url + slug)
        if resp.status_code != 200:
            text_mof(pdf_part, pdf_year, pdf_number, pdf_name)

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

        mof = Mof.query.filter_by(**kwargs).first()
        if mof is None:
            mof = Mof(**kwargs)
            db.session.add(mof)

        if mof.text_json is not None:
            continue

        logger.info("Getting %d/%d/%d", part, year, number)
        pages = get_pages(**kwargs)

        mof.text_json = flask.json.dumps(pages)
        db.session.commit()

        logger.info("Got %d/%d/%d, %d pages, %d seconds",
                    part, year, number, len(pages), time.time() - t0)
