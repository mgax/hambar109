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
              '/view.php?doc=05{mof.year}{mof.number}&format=pdf')
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
    print next_number, number
    for number in range(next_number, number + 1):
        row = model.Mof(year=year, part=part, number=number)
        if fetch:
            row.fetchme = True
        model.db.session.add(row)
    model.db.session.commit()


@harvest_manager.option('count', type=int)
def fetch(count):
    harvest_path = path(flask.current_app.instance_path) / 'harvest'
    harvest_path.makedirs_p()

    for c in xrange(count):
        model.db.session.rollback()
        mof_pool = model.Mof.query.filter_by(fetchme=True, part=4)
        lucky = random.randrange(mof_pool.count())
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

        t = random.randint(20, 30)
        logger.info("Sleeping for %d secods", t)
        time.sleep(t)
