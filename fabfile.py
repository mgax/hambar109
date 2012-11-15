from StringIO import StringIO
import tempfile
import json
from fabric.api import *
from fabric.contrib.files import exists
from path import path


env['use_ssh_config'] = True

SARGE_HOME = path('/var/local/pubdocs')
REDIS_VAR = SARGE_HOME / 'var' / 'pubdocs-redis'
ES_KIT = ('https://github.com/downloads/elasticsearch/'
          'elasticsearch/elasticsearch-0.19.11.tar.gz')
PUBDOCS_VENV = SARGE_HOME / 'var' / 'pubdocs-venv'
PUBDOCS_ES_BIN = (SARGE_HOME / 'var' / 'pubdocs-es' /
                  'elasticsearch-0.19.11' / 'bin')
PUBDOCS_TIKA_URL = 'http://www.eu.apache.org/dist/tika/tika-app-1.2.jar'

PUBDOCS_CONFIG = {
    'REDIS_VAR': REDIS_VAR,
    'PUBDOCS_REDIS_PORT': '27301',
    'SENTRY_DSN': ('http://326f1cd02a1b474a9b973f5e2c74d76c'
                         ':cc011e2b752945b6895938893a8fa14a'
                         '@sentry.gerty.grep.ro/3'),
    'PUBDOCS_FILE_REPO': SARGE_HOME / 'var' / 'pubdocs-file-repo',
    'PUBDOCS_LINKS': '/home/alexm/links.txt',
    'ES_HEAP_SIZE': '256m',
    'ES_PATH_DATA': SARGE_HOME / 'var' / 'pubdocs-es-data',
    'PUBDOCS_ES_URL': 'http://localhost:27302',
    'PUBDOCS_VENV': PUBDOCS_VENV,
    'PUBDOCS_ES_BIN': PUBDOCS_ES_BIN,
    'PYTHONPATH': '.',
    'PUBDOCS_TIKA_PORT': '27303',
    'PUBDOCS_TIKA_JAR': PUBDOCS_VENV / 'tika-app-1.2.jar',
    'MOF_DIR': SARGE_HOME / 'var' / 'pubdocs-file-repo' / 'MOF1',
    'DATABASE': 'sqlite:///' + SARGE_HOME / 'var' / 'pubdocs-db' / 'db.sqlite',
}


env.update({
    'host_string': 'pubdocs@gerty',
    'pubdocs_python_bin': '/usr/local/Python-2.7.3/bin/python',
    'sarge_home': SARGE_HOME,
    'pubdocs_venv': PUBDOCS_VENV,
    'pubdocs_bin': SARGE_HOME / 'var' / 'pubdocs-bin',
    'pubdocs_redis_var': REDIS_VAR,
    'pubdocs_es': SARGE_HOME / 'var' / 'pubdocs-es',
    'pubdocs_es_kit': ES_KIT,
    'pubdocs_es_bin': PUBDOCS_ES_BIN,
    'pubdocs_es_data': PUBDOCS_CONFIG['ES_PATH_DATA'],
    'pubdocs_tika_url': PUBDOCS_TIKA_URL,
})


@task
def configure():
    etc_app = env['sarge_home'] / 'etc' / 'app'
    run('mkdir -p {etc_app}'.format(**locals()))
    put(StringIO(json.dumps(PUBDOCS_CONFIG, indent=2)),
        str(etc_app / 'config.json'))


@task
def virtualenv():
    if not exists(env['pubdocs_venv']):
        run("virtualenv '{pubdocs_venv}' "
            "--distribute --no-site-packages "
            "-p '{pubdocs_python_bin}'"
            .format(**env))

    put("requirements.txt", str(env['pubdocs_venv']))
    run("{pubdocs_venv}/bin/pip install "
        "-r {pubdocs_venv}/requirements.txt"
        .format(**env))


@task
def install_es():
    run("mkdir -p {pubdocs_es}".format(**env))
    with cd(env['pubdocs_es']):
        run("curl -L '{pubdocs_es_kit}' | tar xzf -".format(**env))


@task
def install_tika():
    with cd(env['pubdocs_venv']):
        run("curl -LO '{pubdocs_tika_url}'".format(**env))


@task
def deploy(app_name):
    with cd(env['sarge_home']):
        with tempfile.NamedTemporaryFile() as tmp_file:
            local('git archive HEAD | gzip > {tmp}'
                  .format(tmp=tmp_file.name))
            put(tmp_file.name, '_deploy.tgz'.format(**env))
        run("{sarge_home}/bin/sarge deploy <(zcat _deploy.tgz) {app_name}"
            .format(app_name=app_name, **env))
        run('rm _deploy.tgz')
