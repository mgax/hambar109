PubDocs
=======


Development
-----------
To work on the PubDocs code, you need a local repository checkout, and
make sure you have Java 6 and redis (2.6 or newer) on your ``$PATH``.
Here's a quick howto::

1. Clone the code::

    $ git clone https://github.com/mgax/pubdocs.git
    $ cd pubdocs

2. Create a virtualenv and install dependencies::

    $ virtualenv sandbox --no-site-packages -p python2.7
    $ echo '*' > sandbox/.gitignore
    $ sandbox/bin/pip install -r requirements-dev.txt

3. Install elasticsearch and the `attachment` plugin::

    $ cd sandbox
    $ curl -L 'https://github.com/downloads/elasticsearch/elasticsearch/elasticsearch-0.19.9.tar.gz' | tar xzf -
    $ elasticsearch-0.19.9/bin/plugin -install 'elasticsearch/elasticsearch-mapper-attachments/1.6.0'
    $ cd ..

4. Create an ``.env`` file for `honcho`/`foreman` with the following
contents::

    PUBDOCS_VENV=sandbox
    REDIS_VAR=sandbox/var/redis
    PUBDOCS_REDIS_PORT=5200
    PUBDOCS_ES_URL=http://localhost:5300
    PUBDOCS_ES_BIN=sandbox/elasticsearch-0.19.9/bin

5. Activate the virtualenv. This needs to be done in each shell session
before you run the app. It just configures your ``$PATH`` so that it
begins with ``sandbox/bin``::

    $ source sandbox/bin/activate

6. Run the services locally::

    $ honcho start
