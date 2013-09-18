import sys
import random
import logging
import time
import flask
from flask.ext.script import Manager
from werkzeug.wsgi import FileWrapper
import requests
from path import path
from hambar import model

harvest_manager = Manager()

URL_FORMAT = ('http://www.monitoruloficial.ro/emonitornew/php/services'
              '/view.php?doc=05{mof.year}{mof.number}&%66or%6d%61t=%70d%66')
FILENAME_FORMAT = 'mof{mof.part}_{mof.year}_{mof.number:04}.pdf'

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@harvest_manager.option('number', type=int)
@harvest_manager.option('part', type=int)
@harvest_manager.option('-f', '--fetch', action='store_true')
def new_editions(part, number, fetch=False):
    year = 2013
    latest_known = (model.Mof.query
                             .filter_by(year=year, part=part)
                             .order_by('-number')
                             .first())
    next_number = 1 if latest_known is None else latest_known.number + 1
    n = 0
    for number in range(next_number, number + 1):
        row = model.Mof(year=year, part=part, number=number)
        if fetch:
            row.fetchme = True
        model.db.session.add(row)
        n += 1
    model.db.session.commit()
    logger.info("Added %d records", n)


@harvest_manager.option('count', type=int)
def fetch(count):
    harvest_path = path(flask.current_app.instance_path) / 'harvest'
    harvest_path.makedirs_p()

    got_count = 0
    while True:
        model.db.session.rollback()
        mof_pool = model.Mof.query.filter_by(fetchme=True, part=4)
        remaining = mof_pool.count()
        if not remaining:
            logger.info("Nothing left to download!")
            break

        lucky = random.randrange(remaining)
        mof = mof_pool.offset(lucky).first()
        url = URL_FORMAT.format(mof=mof)
        file_path = harvest_path / FILENAME_FORMAT.format(mof=mof)
        mof.fetchme = False
        model.db.session.commit()

        if file_path.exists():
            logger.info("Skipping %s, already exists", file_path.name)
            continue

        logger.info("Fetching %s to %s", url, file_path.name)

        with file_path.open('wb') as f:
            agent_url = flask.current_app.config['HAMBAR_AGENT_URL']
            resp = requests.post(agent_url, data={'url': url}, stream=True)
            for chunk in FileWrapper(resp.raw):
                f.write(chunk)

        got_count += 1
        if got_count >= count:
            logger.info("Got %d files as requested. Stopping.", count)
            break

        t = random.randint(20, 30)
        logger.info("Sleeping for %d secods", t)
        time.sleep(t)
