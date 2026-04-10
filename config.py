import os
from datetime import timedelta

def _db_uri():
    uri = os.environ.get('DATABASE_URL', 'sqlite:///ucl2526.db')
    # Railway gera URLs com prefixo "postgres://" mas SQLAlchemy exige "postgresql://"
    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    return uri

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ucl2526-chave-secreta-troque-em-producao')
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
