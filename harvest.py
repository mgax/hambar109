import sys
import re
import logging
import tempfile
from path import path
import requests
from celery import Celery
from celery.signals import setup_logging
import flask


MOF_URL = 'http://kurtyan.org/MOF/'


celery = Celery()
celery.config_from_object('celeryconfig')


@setup_logging.connect
def configure_worker(sender=None, **extra):
    from utils import set_up_logging
    set_up_logging()

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

_links_pattern = re.compile(r'<a href="([^"]+)"')


def ignore(link):
    if link.startswith('/'):
        return True
    if link in ['/', '_htaccess.txt', '.DS_Store']:
        return True
    return False


def links(html):
    offset = 0
    while True:
        m = _links_pattern.search(html, offset)
        if m is None:
            break
        offset = m.end(0)
        link = m.group(1)
        if not ignore(link):
            yield link


def register_commands(manager):

    @manager.command
    def index():
        download_urls = []
        skip_urls = []
        resp = requests.get(MOF_URL)
        for link in links(resp.text):
            print>>sys.stderr, '>', link
            resp2 = requests.get(MOF_URL + link)
            for link2 in links(resp2.text):
                print>>sys.stderr, '>>>', link2
                resp3 = requests.get(MOF_URL + link + link2)
                for link3 in links(resp3.text):
                    print>>sys.stderr, '>>>>>', link3
                    print MOF_URL + link + link2 + link3
        print>>sys.stderr, len(MOF_URL)
