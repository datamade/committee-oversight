import sqlalchemy as sa

from sqlalchemy.engine.url import URL

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection

class Command(BaseCommand):
    help = "Import data from manually entered Lugar spreadsheets"

    def handle(self, *args, **options):

        django_conn = connection.get_connection_params()

        conn_kwargs = {
            'username': django_conn.get('user', ''),
            'password': django_conn.get('password', ''),
            'host': django_conn.get('host', ''),
            'port': django_conn.get('port', ''),
            'database': django_conn.get('database', ''),
        }

        self.DB_CONN = URL('postgresql', **conn_kwargs)
        self.engine = sa.create_engine(self.DB_CONN)

        self.stdout.write('Connected to database')
        self.import_csv('data_dir', file, recreate=options['recreate'])

    def import_csv(self, file_path, tablename, recreate=False, primary_key=True):

        if recreate is True:
            self.executeTransaction('''DROP TABLE IF EXISTS {}'''.format(tablename))

        with open(file_path, 'r') as fobj:
            reader = csv.reader(fobj)
            header = next(reader)

        primary_key = header[0]
        fields = ', '.join(['"{}" VARCHAR'.format(head.lower()) for head in header])

        create_table = '''
            CREATE TABLE {0} (
                {1}
            )
        '''.format(tablename, fields)

        self.executeTransaction('DROP TABLE IF EXISTS {}'.format(tablename))
        self.executeTransaction(create_table)

        copy_st = '''
            COPY {} FROM STDIN WITH CSV HEADER
        '''.format(tablename)

        with open(file_path, 'r') as fobj:
            with connection.cursor() as curs:
                curs.copy_expert(copy_st, fobj)

        if primary_key is True:
            self.executeTransaction('''
                ALTER TABLE {0} ADD PRIMARY KEY ("{1}")
            '''.format(tablename, primary_key), raise_exc=False)

        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) AS count FROM {}'.format(tablename))
            result = cursor.fetchone()

        return result[0]

    def executeTransaction(self, query):
        with self.engine.begin() as conn:
            conn.execute("SET local timezone to 'America/Chicago'")
            conn.execute(query)
