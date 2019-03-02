# -*- coding: utf-8 -*-

from trac.core import Component, implements
from trac.env import IEnvironmentSetupParticipant
from reportmanager import CustomReportManager


class ClientsSetupParticipant(Component):

    implements(IEnvironmentSetupParticipant)

    def __init__(self):
        self.db_version_key = 'clients_plugin_version'
        self.db_version = 6
        self.db_installed_version = None

        # Initialise database schema version tracking.
        for value, in self.env.db_query("""
                SELECT value FROM system WHERE name=%s
                """, (self.db_version_key,)):
            self.db_installed_version = int(value)
            break
        else:
            self.db_installed_version = 0
            self.env.db_transaction("""
                INSERT INTO system (name,value) VALUES(%s,%s)
                """, (self.db_version_key, self.db_installed_version))

    def system_needs_upgrade(self):
        return self.db_installed_version < self.db_version

    def do_db_upgrade(self):

        # Do the staged updates
        with self.env.db_transaction as db:
            if self.db_installed_version < 2:
                print 'Creating client table'
                db("""
                    CREATE TABLE client (
                      name TEXT,
                      description TEXT,
                      changes_list TEXT,
                      changes_period TEXT,
                      changes_lastupdate INTEGER,
                      summary_list TEXT,
                      summary_period TEXT,
                      summary_lastupdate INTEGER)
                    """)
                # Import old Enums
                db("""
                    INSERT INTO client (name)
                    SELECT name FROM enum WHERE type='client'
                    """)
                # Clean them out
                db("DELETE FROM enum WHERE type='client'")

            if self.db_installed_version < 3:
                print 'Updating clients table (v3)'
                db("""
                    ALTER TABLE client ADD COLUMN default_rate INTEGER
                    """)
                db("""
                    ALTER TABLE client ADD COLUMN currency TEXT
                    """)

            if self.db_installed_version < 4:
                print 'Updating clients table (v4)'
                db("""
                    CREATE TABLE client_events (
                      name TEXT,
                      summary TEXT,
                      action TEXT,
                      lastrun INTEGER)
                    """)
                db("""
                    CREATE TABLE client_event_summary_options (
                      client_event TEXT,
                      client TEXT,
                      name TEXT,
                      value TEXT)
                    """)
                db("""
                    CREATE TABLE client_event_action_options (
                      client_event TEXT,
                      client TEXT,
                      name TEXT,
                      value TEXT)
                    """)

            if self.db_installed_version < 5:
                print 'Updating clients table (v5)'
                # NB: Use single quotes for literals for better compat
                db("""
                    INSERT INTO client_events
                    SELECT 'Weekly Summary', 'Milestone Summary',
                           'Send Email', MAX(summary_lastupdate)
                    FROM client
                    """)
                db("""
                    INSERT INTO client_event_action_options
                    SELECT 'Weekly Summary', name,
                           'Email Addresses', summary_list
                    FROM client WHERE summary_list != ''
                    """)
                db("""
                    INSERT INTO client_events
                    SELECT 'Ticket Changes', 'Ticket Change Summary',
                           'Send Email', MAX(changes_lastupdate)
                    FROM client
                    """)
                db("""
                    INSERT INTO client_event_action_options
                    SELECT 'Ticket Changes', name,
                           'Email Addresses', changes_list
                    FROM client WHERE changes_list != ''
                    """)
                db("""
                    CREATE TEMPORARY TABLE client_tmp (
                      name TEXT,
                      description TEXT,
                      default_rate INTEGER,
                      currency TEXT)
                    """)
                db("""
                    INSERT INTO client_tmp
                    SELECT name, description, default_rate, currency
                    FROM client
                    """)
                db("DROP TABLE client")
                db("""
                    CREATE TABLE client (
                      name TEXT,
                      description TEXT,
                      default_rate INTEGER,
                      currency TEXT)
                    """)
                db("""
                    INSERT INTO client
                    SELECT name, description, default_rate, currency
                    FROM client_tmp
                    """)
                db("DROP TABLE client_tmp")

            if self.db_installed_version < 6:
                print 'Updating clients table (v6)'
                db("""
                    CREATE TEMPORARY TABLE client_tmp (
                      name TEXT,
                      description TEXT,
                      default_rate DECIMAL(10,2),
                      currency TEXT)
                    """)
                db("""
                    INSERT INTO client_tmp
                    SELECT name, description, default_rate, currency
                    FROM client
                    """)
                db("DROP TABLE client")
                db("""
                    CREATE TABLE client
                      (name TEXT,description TEXT,
                       default_rate DECIMAL(10,2),currency TEXT)
                    """)
                db("""
                    INSERT INTO client
                    SELECT name, description, default_rate, currency
                    FROM client_tmp
                    """)
                db("DROP TABLE client_tmp")

            # Updates complete, set the version'
            db("""
                UPDATE system SET value=%s WHERE name=%s
                """, (self.db_version, self.db_version_key))

    def do_reports_upgrade(self):
        mgr = CustomReportManager(self.env, self.log)
        r = __import__('reports', globals(), locals(), ['reports'])

        for report_group in r.reports:
            rlist = report_group['reports']
            group_title = report_group['title']
            for report in rlist:
                title = report['title']
                new_version = report['version']
                mgr.add_report(report["title"], 'Clients Plugin',
                               report['description'], report['sql'],
                               report['uuid'], report['version'],
                               'Timing and Estimation Plugin',
                               group_title)

    def ticket_fields_need_upgrade(self):
        section = 'ticket-custom'
        return ('text' != self.config.get(section, 'client') or
                'text' != self.config.get(section, 'clientrate'))

    def do_ticket_field_upgrade(self):
        section = 'ticket-custom'

        self.config.set(section, 'client', 'text')
        self.config.set(section, 'client.label', 'Client')

        self.config.set(section, 'clientrate', 'text')
        self.config.set(section, 'clientrate.label', 'Client Charge Rate')

        self.config.save()

    # IEnvironmentSetupParticipant methods

    def environment_created(self):
        """Called when a new Trac environment is created."""
        if self.environment_needs_upgrade():
            self.upgrade_environment()

    def environment_needs_upgrade(self, db=None):
        """Called when Trac checks whether the environment needs to be upgraded.

        Should return `True` if this participant needs an upgrade to be
        performed, `False` otherwise.

        """
        return self.system_needs_upgrade() or self.ticket_fields_need_upgrade()

    def upgrade_environment(self, db=None):
        """Actually perform an environment upgrade.

        Implementations of this method should not commit any database
        transactions. This is done implicitly after all participants have
        performed the upgrades they need without an error being raised.
        """
        print 'ClientsPlugin needs an upgrade'
        print ' * Upgrading db'

        with self.env.db_transaction:
            self.do_db_upgrade()

            print ' * Upgrading reports'
            self.do_reports_upgrade()

            if self.ticket_fields_need_upgrade():
                print ' * Upgrading fields'
                self.do_ticket_field_upgrade()

            print 'Done Upgrading'
