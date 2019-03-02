# -*- coding: utf-8 -*-

import hashlib
import time

from trac.core import Component, ExtensionPoint, TracError

from clients.summary import IClientSummaryProvider
from clients.action import IClientActionProvider


def simplify_whitespace(name):
    """Strip spaces and remove duplicate spaces within names"""
    return ' '.join(name.split())


class ClientEventsSystem(Component):
    summaries = ExtensionPoint(IClientSummaryProvider)
    actions = ExtensionPoint(IClientActionProvider)

    def get_summaries(self):
        for summary in self.summaries:
            yield summary.get_name()

    def get_summary(self, name):
        for summary in self.summaries:
            if name == summary.get_name():
                return summary
        return None

    def get_actions(self):
        for action in self.actions:
            yield action.get_name()

    def get_action(self, name):
        for action in self.actions:
            if name == action.get_name():
                return action
        return None


class ClientEvent(object):
    def __init__(self, env, name=None, client=None):
        self.env = env
        self.log = env.log
        if name:
            name = simplify_whitespace(name)
        if name:
            for row in self.env.db_query("""
                    SELECT summary, action, lastrun
                    FROM client_events WHERE name=%s
                    """, (name,)):
                self.md5 = hashlib.md5(name).hexdigest()
                self.name = self._old_name = name
                self.summary = row[0] or ''
                self.action = row[1] or ''
                self.lastrun = row[2] or 0
                self._load_options(client)
                break
            else:
                raise TracError('Client Event %s does not exist.' % name)
        else:
            self.name = self._old_name = None
            self.summary = ''
            self.action = ''
            self.lastrun = 0

    exists = property(fget=lambda self: self._old_name is not None)

    def delete(self):
        assert self.exists, 'Cannot deleting non-existent client event'
        self.log.info("Deleting client event %s", self.name)
        self.env.db_transaction("""
            DELETE FROM client_events WHERE name=%s
            """, (self.name,))
        self.name = self._old_name = None

    def insert(self):
        assert not self.exists, 'Cannot insert existing client event'
        system = ClientEventsSystem(self.env)
        assert system.get_summary(self.summary) is not None, 'Invalid summary'
        assert system.get_action(self.action) is not None, 'Invalid action'
        self.name = simplify_whitespace(self.name)
        assert self.name, 'Cannot create client event with no name'
        self.log.debug("Creating new client event '%s'", self.name)
        self.env.db_transaction("""
            INSERT INTO client_events (name,summary,action,lastrun)
            VALUES (%s,%s,%s,%s)
            """, (self.name, self.summary, self.action, int(time.time())))

    def _load_client_options(self, client, opttype):
        assert self.exists, 'Cannot update non-existent client event'
        assert opttype in ('summary', 'action'), 'Invalid options type'
        system = ClientEventsSystem(self.env)
        if 'summary' == opttype:
            thing = system.get_summary(self.summary)
            assert thing is not None, 'Invalid summary'
            self.summary_description = thing.get_description()
        else:
            thing = system.get_action(self.action)
            assert thing is not None, 'Invalid action'
            self.action_description = thing.get_description()

        options = {}
        table = 'client_event_' + opttype + '_options'
        for name, value in self.env.db_query("""
                SELECT name, value FROM %s
                WHERE client_event=%%s AND client=%%s
                """ % table, (self._old_name, client or '')):
            options[name] = value
        rv = {}
        for option in thing.options(client):
            option['md5'] = hashlib.md5(option['name']).hexdigest()
            if option['name'] in options:
                option['value'] = options[option['name']]
            else:
                option['value'] = ''
            rv[option['name']] = option
        return rv

    def _load_options(self, client):
        self.summary_options = self._load_client_options(None, 'summary')
        self.action_options = self._load_client_options(None, 'action')
        if client:
            self.summary_client_options = \
                self._load_client_options(client, 'summary')
            self.action_client_options = \
                self._load_client_options(client, 'action')

    def _update_client_options(self, client, opttype, options):
        assert self.exists, 'Cannot update non-existent client event'
        assert opttype in ('summary', 'action'), 'Invalid options type'
        system = ClientEventsSystem(self.env)
        if 'summary' == opttype:
            thing = system.get_summary(self.summary)
            assert thing is not None, 'Invalid summary'
        else:
            thing = system.get_action(self.action)
            assert thing is not None, 'Invalid action'

        table = 'client_event_' + opttype + '_options'
        self.log.info('Updating client event "%s"', self._old_name)
        with self.env.db_transaction as db:
            db("""
                DELETE FROM %s WHERE client_event=%%s AND client=%%s
                """ % table, (self._old_name, client or ''))

            valid_options = []
            for option in thing.options(client):
                valid_options.append(option['name'])
            for option in options.values():
                if option['name'] in valid_options:
                    db("""
                        INSERT INTO %s (client_event, client, name, value)
                        VALUES (%%s, %%s, %%s, %%s)
                        """ % table, (self._old_name, client or '',
                                      option['name'], option['value']))

    def update_options(self, client=None):
        assert self.exists, 'Cannot update non-existent client event'

        if client:
            self._update_client_options(client, 'summary',
                                        self.summary_client_options)
            self._update_client_options(client, 'action',
                                        self.action_client_options)
        else:
            self._update_client_options(None, 'summary', self.summary_options)
            self._update_client_options(None, 'action', self.action_options)

    def update(self):
        assert self.exists, 'Cannot update non-existent client event'
        self.name = simplify_whitespace(self.name)
        assert self.name, 'Cannot update client event with no name'

        self.log.info('Updating client event "%s"', self._old_name)
        self.env.db_transction("""
            UPDATE client_events SET lastrun=%s WHERE name=%s
            """, (int(self.lastrun), self._old_name))

    def trigger(self, req, client, fromdate, todate):
        assert self.exists, "Cannot trigger client event that does not exist"
        system = ClientEventsSystem(self.env)
        summary = system.get_summary(self.summary)
        assert summary is not None, 'Invalid summary'
        action = system.get_action(self.action)
        assert action is not None, 'Invalid action'

        if not summary.init(self, client):
            self.log.info("Could not init summary")
            return False
        if not action.init(self, client):
            self.log.info("Could not init action")
            return False

        self.log.debug("Performing action")
        return action.perform(req, summary.get_summary(req, fromdate, todate))

    @classmethod
    def select(cls, env, client=None):
        for name, summary, action, lastrun in env.db_query("""
                SELECT name,summary,action,lastrun
                FROM client_events ORDER BY name
                """):
            clev = cls(env)
            clev.md5 = hashlib.md5(name).hexdigest()
            clev.name = clev._old_name = name
            clev.summary = summary or ''
            clev.action = action or ''
            clev.lastrun = lastrun or 0
            clev._load_options(client)
            yield clev

    @classmethod
    def triggerall(cls, env, req, event):
        with env.db_transaction as db:
            try:
                ev = cls(env, event, None)
            except:
                env.log.error("Could not run the event %s", event)
                return
            # ev.lastrun = 1
            now = int(time.time())

            for client, in db("""
                    SELECT name FROM client ORDER BY name
                    """):
                env.log.info("Running event for client: %s", client)
                clev = cls(env, event, client)
                clev.trigger(req, client, ev.lastrun, now)
            ev.lastrun = now
            ev.update()
