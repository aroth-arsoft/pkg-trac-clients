# -*- coding: utf-8 -*-

from trac.core import TracError


def simplify_whitespace(name):
    """Strip spaces and remove duplicate spaces within names"""
    return ' '.join(name.split())


class Client(object):
    def __init__(self, env, name=None):
        self.env = env
        self.log = env.log
        if name:
            name = simplify_whitespace(name)
        if name:
            for row in self.env.db_query("""
                    SELECT description, default_rate, currency
                    FROM client WHERE name=%s
                    """, (name,)):
                self.name = self._old_name = name
                self.description = row[0] or ''
                self.default_rate = row[1] or ''
                self.currency = row[2] or ''
                break
            else:
                raise TracError('Client %s does not exist.' % name)
        else:
            self.name = self._old_name = None
            self.description = None
            self.default_rate = ''
            self.currency = ''

    exists = property(fget=lambda self: self._old_name is not None)

    def delete(self):
        assert self.exists, 'Cannot deleting non-existent client'
        self.log.info("Deleting client %s", self.name)
        self.env.db_transaction("""
            DELETE FROM client WHERE name=%s
            """, (self.name,))
        self.name = self._old_name = None

    def insert(self):
        assert not self.exists, "Cannot insert existing client"
        self.name = simplify_whitespace(self.name)
        assert self.name, 'Cannot create client with no name'
        self.log.debug("Creating new client '%s'", self.name)
        self.env.db_transaction("""
            INSERT INTO client (name, description,default_rate, currency)
            VALUES (%s,%s, %s,%s)
            """, (self.name, self.description,
                  (self.default_rate or None), self.currency))

    def update(self):
        assert self.exists, "Cannot update non-existent client"
        self.name = simplify_whitespace(self.name)
        assert self.name, "Cannot update client with no name"

        with self.env.db_transaction as db:
            self.log.info('Updating client "%s"', self.name)
            db("""
                UPDATE client
                SET name=%s,description=%s, default_rate=%s, currency=%s
                WHERE name=%s
                """, (self.name, self.description,
                      (self.default_rate or None),
                      self.currency, self._old_name))
            if self.name != self._old_name:
                # Update tickets
                db("""
                    UPDATE ticket_custom SET value=%s
                    WHERE name=%s AND value=%s
                    """, (self.name, 'client', self._old_name))
                # Update event options
                db("""
                    UPDATE client_event_summary_options SET client=%s
                    WHERE client=%s
                    """, (self.name, self._old_name))
                db("""
                    UPDATE client_event_action_options SET client=%s
                    WHERE client=%s
                    """, (self.name, self._old_name))
                self._old_name = self.name

    @classmethod
    def select(cls, env):
        for name, description, default_rate, currency in env.db_query("""
                SELECT name, description, default_rate, currency
                FROM client ORDER BY name
                """):
            client = cls(env)
            client.name = client._old_name = name
            client.description = description or ''
            client.default_rate = default_rate or ''
            client.currency = currency or ''
            yield client
