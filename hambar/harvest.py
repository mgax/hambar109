from flask.ext.script import Manager
from hambar import model

harvest_manager = Manager()


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
