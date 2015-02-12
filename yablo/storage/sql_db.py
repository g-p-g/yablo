from datetime import datetime

from sqlalchemy import create_engine, Column, ForeignKey
from sqlalchemy import String, Integer, DateTime, Boolean, Enum, BLOB
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base

from ..config import app_config


def setup_engine(conn_string=None, **kwargs):
    return create_engine(conn_string or app_config['conn_string'], **kwargs)


def setup_storage(conn_string=None, engine=None, **kwargs):
    if engine is None:
        engine = setup_engine(conn_string, **kwargs)
    return sessionmaker(bind=engine)


def get_or_create(session, model, **kwargs):
    """
    Return one row from the database or create a new one
    if it doesn't exist based on the query parameters.

    This assumes the query must match no more than one single row.
    """
    try:
        return session.query(model).filter_by(**kwargs).one()
    except NoResultFound:
        instance = model(**kwargs)
        try:
            session.add(instance)
            session.flush()
            return instance
        except IntegrityError:
            # Some other place pushed new data between the initial
            # query and this new one.
            session.rollback()
            return session.query(model).filter_by(**kwargs).one()


def create_if_not_present(session, model, **kwargs):
    """
    Create a new record if it does not exist. If it does, None
    is returned.
    """
    try:
        session.query(model).filter_by(**kwargs).one()
        return None
    except NoResultFound:
        return model(**kwargs)


Base = declarative_base()


class Subscriber(Base):
    __tablename__ = "subscriber"
    subs_id = Column('id', Integer, primary_key=True)
    public_id = Column(String(36), unique=True, nullable=False)


class WebhookSubscriber(Base):
    """
    Table containing all the webhook subscribers.
    """
    __tablename__ = "webhook_subscriber"

    subs_id = Column('subscriber_id', Integer, ForeignKey('subscriber.id'),
                     primary_key=True)
    hook = Column(String(1024), nullable=False, unique=True)
    active = Column(Boolean, nullable=False)
    auth_path = Column(String(1024), nullable=False)
    authorized = Column(DateTime)

    subscriber = relationship(Subscriber, uselist=False)

    def __repr__(self):
        return "<WebhookSubscriber(subs_id=%s, hook='%s')>" % (
            self.subs_id, self.hook)


class WatchAddress(Base):
    """
    Table containing all addresses that are being watched by one or
    more subscribers.
    """
    __tablename__ = "watchaddy"

    addr_id = Column('id', Integer, primary_key=True)
    address = Column(String(35), unique=True, index=True)

    def __repr__(self):
        return "<WatchAddress(address='%s')>" % self.address


class SubscriberNewBlock(Base):
    """
    Subscribers interested in new blocks.
    """
    __tablename__ = "subscriber_newblock"

    subs_id = Column('subscriber_id', Integer, ForeignKey('subscriber.id'),
                     primary_key=True)

    subscriber = relationship(Subscriber, uselist=False)

    def __repr__(self):
        return "<SubscriberNewBlock(subs_id=%s)>" % self.subs_id


class SubscriberWatchAddress(Base):
    """
    Subscribers interested in watching specific addresses.
    """
    __tablename__ = "subscriber_watchaddy"

    # Composite primary key.
    subs_id = Column('subscriber_id', Integer, ForeignKey('subscriber.id'),
                     primary_key=True)
    addr_id = Column(Integer, ForeignKey('watchaddy.id'), nullable=False,
                     primary_key=True)

    subscriber = relationship(Subscriber)
    address = relationship(WatchAddress)

    def __repr__(self):
        return "<SubscriberWatchAddress(subs_id=%s, addr_id=%s)>" % (
            self.subs_id, self.addr_id)


class Event(Base):
    """
    Events that were sent or must be sent.
    """
    __tablename__ = "event"

    evt_id = Column('id', Integer, primary_key=True)
    subs_id = Column('subscriber_id', Integer, ForeignKey('subscriber.id'),
                     nullable=False)
    data = Column(BLOB, nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    num_attempt = Column(Integer, nullable=False)
    last_attempt = Column(DateTime)
    status = Column(Enum('sent', 'retrying', 'gaveup'))

    subscriber = relationship(Subscriber)

    def __repr__(self):
        return "<Event(evt_id=%s, subs_id=%s, num_attempt=%d, status=%s)>" % (
            self.evt_id, self.subs_id, self.num_attempt, self.status)
