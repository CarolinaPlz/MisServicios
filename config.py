import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'clave_secreta_mis_servicios'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database', 'mis_servicios.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
