SERVER_HOSTNAME = 'https://my-server.com'
APP_DEPLOYMENT_PATH = '/tripel'

NUM_BCRYPT_ROUNDS = 13

SESSION_ID_COOKIE_NAME = 'metaspace_session_id'

TEMPLATE_DIR = 'templates'

PG_PASS_FILENAME = 'config/pgpass'
PG_HOST_ADDR = '127.0.0.1'
PG_DBNAME = 'tripel'
PG_USERNAME = 'tripel'

PG_HOST_ADDR_TEST = PG_HOST_ADDR
PG_DBNAME_TEST = 'tripel_test'
PG_USERNAME_TEST = 'tripel_test'

NEO_DB_URI = 'http://localhost:7474/db/data/'
NEO_DB_URI_TEST = 'http://localhost:6474/test_db/data/'

GREMLIN_LIB_FILES = ['groovy_scripts/GremlinUtils.groovy']

SMTP_SERVER = 'mail.my-server.com'
SMTP_PORT = 587
SMTP_USERNAME = 'tripel.email.user@my-server.com'
SMTP_PASS_FILENAME = 'config/smtppass'
DEFAULT_FROM_ADDRESS = 'tripel.email.user@my-server.com'

PASSWORD_CHECK_MAX_FAILURES = 5
PASSWORD_CHECK_WINDOW_IN_MIN = 10
