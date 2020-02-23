# -*- coding: utf-8 -*-

from lxml import etree

from trac.core import Component, implements
from trac.util.datefmt import format_date
from trac.wiki import format_to_oneliner

from clients.summary import IClientSummaryProvider
from clients.processor import extract_client_text


class ClientMonthlyHoursSummary(Component):
    implements(IClientSummaryProvider)

    client = None
    debug = False

    def get_name(self):
        return "Monthly Hours Summary"

    def get_description(self):
        return "Details the total hours spent on tickets for the last " \
               "three months."

    def options(self, client=None):
        return []

    def init(self, event, client):
        self.client = client
        return True

    def get_summary(self, req, fromdate=None, todate=None):
        def myformat_date(dte):
            if dte:
                return format_date(dte, '%e %b %Y')
            return "No date set"

        def myformat_hours(hrs, fallback='No estimate available'):
            from math import floor
            if hrs:
                hrs = float(hrs)
                if 0 != hrs:
                    neg = False
                    if hrs < 0:
                        neg = True
                        hrs *= -1
                    mins = floor((hrs - floor(hrs)) * 60)
                    s = ''
                    if neg:
                        s = '-'
                    if hrs:
                        s = "%s%sh" % (s, int(floor(hrs)))
                    if mins:
                        s = "%s %sm" % (s, int(mins))
                    return s
            return fallback

        client = self.client
        xml = etree.Element('clientsplugin')

        # Place basic client info here
        xclient = etree.SubElement(xml, 'client')
        etree.SubElement(xclient, 'name').text = client
        if fromdate:
            etree.SubElement(xclient, 'lastupdate').text = \
                myformat_date(fromdate)

        # Information about milestones
        months = {}
        xmonths = etree.SubElement(xml, 'months')

        have_data = False
        # Load in a summary of the client's tickets
        sql = ("""\
          SELECT t.id, t.summary, t.description, t.status,
            SUM(tchng.newvalue) AS totalhours,
            CONCAT(MONTHNAME(FROM_UNIXTIME(tchng.time/1000000)),
            " ",
            YEAR(FROM_UNIXTIME(tchng.time/1000000))) AS month
          FROM ticket_custom AS tcust
          INNER JOIN ticket AS t ON tcust.ticket=t.id
          INNER JOIN ticket_change AS tchng
            ON t.id=tchng.ticket
              AND tchng.field='hours'
              AND tchng.oldvalue=0
          WHERE tcust.name = 'client'
            AND tcust.value = %s
            AND tchng.time >= (UNIX_TIMESTAMP(PERIOD_ADD(EXTRACT(YEAR_MONTH FROM NOW()), -3)*100+1)*1000000)
          GROUP BY t.id, MONTH(FROM_UNIXTIME(tchng.time/1000000))
          ORDER BY tchng.time DESC;
          """)
        xsummary = etree.SubElement(xml, 'summary')
        for tid, summary, description, status, totalhours, month \
                in self.env.db_query(sql, (client,)):
            have_data = True

            if month not in months:
                xmonth = etree.SubElement(xmonths, 'month')
                etree.SubElement(xmonth, 'name').text = month
                months[month] = {'totalhours': 0, 'xml': xmonth}

            # Add hours to create a total.
            months[month]['totalhours'] += float(totalhours)

            self.log.debug("  Summarising ticket #%s in %s", tid, month)
            ticket = etree.SubElement(xsummary, 'ticket')
            etree.SubElement(ticket, 'id').text = str(tid)
            etree.SubElement(ticket, 'summary').text = summary
            ticket.append(etree.XML(
                '<description>%s</description>' % format_to_oneliner(
                    extract_client_text(description), self.env, req)))
            etree.SubElement(ticket, 'status').text = status
            etree.SubElement(ticket, 'month').text = month

            etree.SubElement(ticket, 'totalhours').text = myformat_hours(
                totalhours, 'None')

        # Put the total hours into the month info
        for month in months:
            etree.SubElement(months[month]['xml'], 'totalhours').\
                text = myformat_hours(months[month]['totalhours'])

        if self.debug:
            with open('/tmp/send-client-email.xml', 'w') as file_:
                file_.write(etree.tostring(xml, pretty_print=True))
            self.log.debug(" Wrote XML to /tmp/send-client-email.xml")

        if not have_data:
            return None

        return xml
