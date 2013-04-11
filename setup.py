from distutils.core import setup

setup(
    name = 'tripel',
    version = '0.1',
    description = 'graph-based discussion and information sharing for small groups',
    long_description = 'tripel allows users to share and categorize write-ups, to '
                        'have discussions, and to receive notifications on write-ups '
                        'or discussion threads which they may be directly or indirectly '
                        'interested in.  tripel is backed by a graph database (neo4j), and '
                        'allows users to create and traverse arbitrary connections between '
                        'write-ups and comments.',
    author = 'nodesetc <nodesetc@gmail.com>',
    author_email = 'nodesetc@gmail.com',
    url = 'https://github.com/nodesetc/tripel/',
    package_dir = {'tripel': 'tripel'},
    packages = ['tripel', 'tripel.config_defaults'],
    requires = ['cryptacular', 'DBUtils', 'py2neo', 'pytz', 'web']
)