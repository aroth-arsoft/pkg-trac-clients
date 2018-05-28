# -*- coding: utf-8 -*-

from trac.core import TracError


def simplify_whitespace(name):
    """Strip spaces and remove duplicate spaces within names"""
    return ' '.join(name.split())


class Client(object):
    def __init__(self, env, name=None, db=None):
        self.env = env
        if name:
            name = simplify_whitespace(name)
        if name:
            if not db:
                db = self.env.get_read_db()
            cursor = db.cursor()
            cursor.execute("""
                SELECT description, default_rate, currency
                FROM client WHERE name=%s
                """, (name,))
            row = cursor.fetchone()
            if not row:
                raise TracError('Client %s does not exist.' % name)
            self.name = self._old_name = name
            self.description = row[0] or ''
            self.default_rate = row[1] or ''
            self.currency = row[2] or ''
        else:
            self.name = self._old_name = None
            self.description = None
            self.default_rate = ''
            self.currency = ''

    exists = property(fget=lambda self: self._old_name is not None)

    def delete(self, db=None):
        assert self.exists, 'Cannot deleting non-existent client'

        @self.env.with_transaction()
        def do_delete(db):
            cursor = db.cursor()
            self.log.info("Deleting client %s", self.name)
            cursor.execute("DELETE FROM client WHERE name=%s", (self.name,))

            self.name = self._old_name = None

    def insert(self, db=None):
        assert not self.exists, "Cannot insert existing client"
        self.name = simplify_whitespace(self.name)
        assert self.name, 'Cannot create client with no name'

        @self.env.with_transaction()
        def do_insert(db):
            cursor = db.cursor()
            self.log.debug("Creating new client '%s'", self.name)
            cursor.execute("""
                INSERT INTO client (name, description,default_rate, currency)
                VALUES (%s,%s, %s,%s)
                """, (self.name, self.description,
                      (self.default_rate or None), self.currency))

    def update(self, db=None):
        assert self.exists, "Cannot update non-existent client"
        self.name = simplify_whitespace(self.name)
        assert self.name, "Cannot update client with no name"

        @self.env.with_transaction()
        def do_update(db):
            cursor = db.cursor()
            self.log.info('Updating client "%s"', self.name)
            cursor.execute("""
                UPDATE client
                SET name=%s,description=%s, default_rate=%s, currency=%s
                WHERE name=%s
                """, (self.name, self.description,
                      (self.default_rate or None),
                      self.currency, self._old_name))
            if self.name != self._old_name:
                # Update tickets
                cursor.execute("""
                    UPDATE ticket_custom SET value=%s
                    WHERE name=%s AND value=%s
                    """, (self.name, 'client', self._old_name))
                # Update event options
                cursor.execute("""
                    UPDATE client_event_summary_options SET client=%s
                    WHERE client=%s
                    """, (self.name, self._old_name))
                cursor.execute("""
                    UPDATE client_event_action_options SET client=%s
                    WHERE client=%s
                    """, (self.name, self._old_name))
                self._old_name = self.name

    @classmethod
    def select(cls, env, db=None):
        if not db:
            db = env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT name, description, default_rate, currency
            FROM client ORDER BY name
            """)
        for name, description, default_rate, currency in cursor:
            client = cls(env)
            client.name = client._old_name = name
            client.description = description or ''
            client.default_rate = default_rate or ''
            client.currency = currency or ''
            yield client
