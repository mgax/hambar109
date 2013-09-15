#!/usr/bin/env python

LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s %(message)s"


def main():
    import logging
    logging.basicConfig(format=LOG_FORMAT)
    logging.getLogger('werkzeug').setLevel(logging.INFO)

    from hambar.app import create_app, create_manager
    app = create_app()

    SENTRY_DSN = app.config.get('SENTRY_DSN')
    if SENTRY_DSN:
        from raven.conf import setup_logging
        from raven.handlers.logging import SentryHandler
        setup_logging(SentryHandler(SENTRY_DSN, level=logging.WARN))

    manager = create_manager(app)
    manager.run()


if __name__ == '__main__':
    main()
