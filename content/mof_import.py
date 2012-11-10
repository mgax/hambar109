import os
import logging
from path import path
import simplejson as json
from .tika import invoke_tika
from .mof_parser import MofParser


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def all_files(directory):
    for item in directory.listdir():
        if item.isdir():
            for subitem in all_files(item):
                yield subitem
        elif item.isfile():
            yield item


def find_mof(name):
    mof_dir = path(os.environ['MOF_DIR']).abspath()
    for item in all_files(mof_dir):
        if item.name == name + '.pdf':
            return item
    else:
        raise KeyError("Can't find MOF %r" % name)


def register_commands(manager):

    @manager.option('-r', '--raw-html', action='store_true',
                    help="Print unparsed HTML")
    @manager.option('name', help="Name of document to be loaded")
    def mof_import(name, raw_html=False):
        pdf_path = find_mof(name)

        log.info("Importing pdf %s", pdf_path)

        with pdf_path.open('rb') as pdf_file:
            html = ''.join(invoke_tika(pdf_file))

        if raw_html:
            print html
            return

        articles = MofParser(html).parse()
        log.info("%d articles found", len(articles))
        print json.dumps(articles, indent=2, sort_keys=True)
