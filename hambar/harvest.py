from flask.ext.script import Manager
from hambar import model

harvest_manager = Manager()


@harvest_manager.option('number', type=int)
@harvest_manager.option('part', type=int)
def new_editions(part, number):
    year = 2013
    latest_known = (model.Mof.query
                             .filter_by(year=year, part=part)
                             .order_by('-number')
                             .first())
    next_number = 1 if latest_known is None else latest_known.number + 1
    print next_number, number
    for number in range(next_number, number + 1):
        model.db.session.add(model.Mof(year=year, part=part, number=number))
    model.db.session.commit()
