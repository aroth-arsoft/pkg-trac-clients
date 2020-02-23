# -*- coding: utf-8 -*-

from trac.core import *


class CustomReportManager:
    """A Class to manage custom reports"""
    version = 1
    name = "custom_report_manager_version"
    env = None
    log = None

    def __init__(self, env, log):
        self.env = env
        self.log = log
        self.upgrade()

    def upgrade(self):
        version = 0
        for value, in self.env.db_query("""
                SELECT value FROM system WHERE name=%s
                """, (self.name,)):
            version = int(value)
            break
        else:
            self.env.db_transaction("""
                INSERT INTO system (name,value) VALUES(%s,%s)
                """, (self.name, version))

        if version > self.version:
            raise TracError(
                "Fatal Error: You appear to be running two plugins with "
                "conflicting versions of the CustomReportManager class. "
                "Please ensure that '%s' is updated to version %s of the "
                "file reportmanager.py (currently using version %s)."
                % (__name__, str(version), str(self.version)))

        # Do the staged updates
        if version < self.version:
            with self.env.db_transaction as db:
                if version < 1:
                    db("""
                        CREATE TABLE custom_report (
                          id INTEGER,
                          uuid VARCHAR(64),
                          maingroup VARCHAR(255),
                          subgroup VARCHAR(255),
                          version INTEGER,
                          ordering INTEGER)
                        """)
                db("""
                    UPDATE system SET value=%s WHERE name=%s
                    """, (self.version, self.name))

    def add_report(self, title, author, description, query, uuid, version,
                   maingroup, subgroup=""):
        # First check to see if we can load an existing version of this report
        rv = False

        id = None
        currentversion = 0
        for id, currentversion in self.env.db_query("""
                SELECT id, version FROM custom_report WHERE uuid=%s
                """, (uuid,)):
            break

        if not id or currentversion < version:
            with self.env.db_transaction as db:
                if not id:
                    next_id = 0
                    for next_id, in self.env.db_query("""
                            SELECT MAX(id) FROM report
                            """):
                        if next_id is None:
                            next_id = 0
                        else:
                            next_id = int(next_id) + 1
                    self.log.debug("Inserting new report with uuid '%s'",
                                   uuid)

                    # Get the ordering of any current reports in this
                    # group/subgroup.
                    for ordering, in db("""
                            SELECT MAX(ordering) FROM custom_report
                            WHERE maingroup=%s AND subgroup=%s
                            """, (maingroup, subgroup)):
                        if ordering is None:
                            ordering = 0
                        else:
                            ordering = int(ordering) + 1
                        break
                    else:
                        ordering = 0

                    db("""
                        INSERT INTO report
                         (id, title, author, description, query)
                        VALUES (%s, %s, %s, %s, %s)
                        """, (next_id, title, author, description, query))
                    db("""
                        INSERT INTO custom_report
                          (id,uuid,maingroup,subgroup,version,ordering)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """, (next_id, uuid, maingroup, subgroup, version,
                              ordering))
                    rv = True
                else:
                    self.log.debug("Updating report with uuid '%s' to "
                                   "version %s", uuid, version)
                    db("""
                        UPDATE report
                        SET title=%s, author=%s, description=%s, QUERY=%s
                        WHERE id=%s
                        """, (title, author, description, query, id))
                    db("""
                        UPDATE custom_report
                        SET version=%s, maingroup=%s, subgroup=%s
                        WHERE id=%s
                        """, (version, maingroup, subgroup, id))
                    rv = True

        return rv

    def get_report_by_uuid(self, uuid):
        for row in self.env.db_query("""
                SELECT report.id,report.title FROM custom_report
                LEFT JOIN report ON custom_report.id=report.id
                WHERE custom_report.uuid=%s
                """, (uuid,)):
            return row

    def get_reports_by_group(self, group):
        rv = {}
        for subgroup, id_, title in self.env.db_query("""
                SELECT custom_report.subgroup,report.id,report.title
                FROM custom_report
                LEFT JOIN report ON custom_report.id=report.id
                WHERE custom_report.maingroup=%s
                ORDER BY custom_report.subgroup,custom_report.ordering
                """, (group,)):
            if subgroup not in rv:
                rv[subgroup] = {
                    'title': subgroup,
                    'reports': []
                }
            rv[subgroup]['reports'].append({
                'id': int(id_),
                'title': title
            })

        return rv
