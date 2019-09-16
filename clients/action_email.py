# -*- coding: utf-8 -*-

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.charset import add_charset, SHORTEST
from lxml import etree

from trac import __version__
from trac.core import Component, implements

from clients.action import IClientActionProvider


class ClientActionEmail(Component):
    implements(IClientActionProvider)

    client = None
    debug = False

    def __init__(self):
        self.emails = None
        self.subject = None
        self.transform = None

    def get_name(self):
        return "Send Email"

    def get_description(self):
        return "Send an email to a certain list of addresses"

    def options(self, client=None):
        if client is None:
            yield {
                'name': 'XSLT',
                'description': "Formatting XSLT to convert the summary to "
                               "an email",
                'type': 'large'
            }
            yield {
                'name': 'Subject',
                'description': "Email subject (use %s to replace the active "
                               "client name)",
                'type': 'medium'
            }
        else:
            yield {
                'name': 'Email Addresses',
                'description': 'Comma separated list of email addresses',
                'type': 'medium'
            }

    def init(self, event, client):
        self.client = client
        if 'XSLT' not in event.action_options or \
                not event.action_options['XSLT']['value']:
            return False
        try:
            self.transform = etree.XSLT(
                etree.fromstring(str(event.action_options['XSLT']['value'])))
        except:
            self.log.error("Error: Cannot load/parse stylesheet")
            return False

        if 'Email Addresses' not in event.action_client_options or \
                not event.action_client_options['Email Addresses']['value']:
            return False

        self.emails = []
        addresses = event.action_client_options['Email Addresses']['value']
        for email in addresses.replace(',', ' ').split(' '):
            if '' != email.strip():
                self.emails.append(email.strip())

        if not self.emails:
            return False

        if 'Subject' not in event.action_options or not \
                event.action_options['Subject']['value']:
            self.subject = 'Ticket Summary for %s'
        else:
            self.subject = event.action_options['Subject']['value']

        if self.subject.find('%s') >= 0:
            self.subject = self.subject % (client,)

        return True

    def perform(self, req, summary):
        if summary is None:
            return False
        config = self.env.config
        encoding = 'utf-8'
        subject = self.subject

        if not config.getbool('notification', 'smtp_enabled'):
            return False
        from_email = config['notification'].get('smtp_from')
        from_name = config['notification'].get('smtp_from_name')
        replyto_email = config['notification'].get('smtp_replyto')
        from_email = from_email or replyto_email
        if not from_email:
            return False

        # Authentication info (optional)
        user_name = config['notification'].get('smtp_user')
        password = config['notification'].get('smtp_password')

        # Thanks to the author of this recipe:
        # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473810

        add_charset('utf-8', SHORTEST, None, None)

        projname = config.get('project', 'name')

        # Create the root message and fill in from, to, and subject headers
        msg_root = MIMEMultipart('alternative')
        msg_root['To'] = str(', ').join(self.emails)

        msg_root['X-Mailer'] = 'ClientsPlugin for Trac'
        msg_root['X-Trac-Version'] = __version__
        msg_root['X-Trac-Project'] = projname
        msg_root['Precedence'] = 'bulk'
        msg_root['Auto-Submitted'] = 'auto-generated'
        msg_root['Subject'] = subject
        msg_root['From'] = '%s <%s>' % (from_name or projname, from_email)
        msg_root['Reply-To'] = replyto_email
        msg_root.preamble = 'This is a multi-part message in MIME format.'

        view = 'plain'
        arg = "'%s'" % view
        result = self.transform(summary, view=arg)
        msg_text = MIMEText(str(result), view, encoding)
        msg_root.attach(msg_text)

        msg_related = MIMEMultipart('related')
        msg_root.attach(msg_related)

        view = 'html'
        arg = "'%s'" % view
        result = self.transform(summary, view=arg)
        # file = open('/tmp/send-client-email.html', 'w')
        # file.write(str(result))
        # file.close()

        msg_text = MIMEText(str(result), view, encoding)
        msg_related.attach(msg_text)

        # Handle image embedding...
        view = 'images'
        arg = "'%s'" % view
        result = self.transform(summary, view=arg)
        if result:
            images = result.getroot()
            if images is not None:
                for img in images:
                    if 'img' != img.tag:
                        continue
                    if not img.get('id') or not img.get('src'):
                        continue

                    with open(img.get('src'), 'rb') as fp:
                        if not fp:
                            continue
                        msg_img = MIMEImage(fp.read())
                    msg_img.add_header('Content-ID', '<%s>' % img.get('id'))
                    msg_related.attach(msg_img)

        # Send the email
        import smtplib
        smtp = smtplib.SMTP()  # smtp_server, smtp_port)
        if False and user_name:
            smtp.login(user_name, password)
        smtp.connect()
        smtp.sendmail(from_email, self.emails, msg_root.as_string())
        smtp.quit()
        return True
