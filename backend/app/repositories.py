from sqlalchemy import select

def rows(db, model, order=None):
    query = select(model)
    if order is not None: query = query.order_by(order)
    return db.scalars(query).all()

def serialize(row):
    return {c.name:getattr(row,c.name) for c in row.__table__.columns}
