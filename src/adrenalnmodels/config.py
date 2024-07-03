# Enable debug mode.
DEBUG = True
SECRET_KEY = 'my precious'
POSTGRES_USER = 'postgres'
POSTGRES_PASS = 'VBK0471208'
POSTGRES_DB = 'dumpimport'
POSTGRES_HOST = 'localhost'
POSTGRES_PORT = '5432'

# Connect to the database
SQLALCHEMY_DATABASE_URI = 'postgresql://' + POSTGRES_USER + ':' + POSTGRES_PASS + '@' + POSTGRES_HOST + ':' + POSTGRES_PORT + '/' + POSTGRES_DB