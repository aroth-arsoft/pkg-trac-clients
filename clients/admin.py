# -*- coding: utf-8 -*-

from trac.core import *
from trac.ticket.admin import TicketAdminPanel
from trac.web.chrome import add_script

from clients.model import Client
from clients.events import ClientEvent


class ClientAdminPanel(TicketAdminPanel):
    _type = 'clients'
    _label = ('Client', 'Clients')

    # TicketAdminPanel methods

    def get_admin_commands(self):
        return None

    def _render_admin_panel(self, req, cat, page, client):
        # Detail view?
        if client:
            clnt = Client(self.env, client)
            events = ClientEvent.select(self.env, client)
            if req.method == 'POST':
                if 'save' in req.args:
                    clnt.name = req.args.get('name')
                    clnt.description = req.args.get('description')
                    clnt.changes_list = req.args.get('changes_list')
                    clnt.changes_period = req.args.get('changes_period')
                    clnt.summary_list = req.args.get('summary_list')
                    clnt.summary_period = req.args.get('summary_period')
                    clnt.default_rate = req.args.get('default_rate')
                    clnt.currency = req.args.get('currency')
                    clnt.update()

                    for clev in events:
                        for option in clev.summary_client_options:
                            arg = 'summary-option-%s-%s' \
                                  % (clev.md5,
                                     clev.summary_client_options[option]['md5'])
                            clev.summary_client_options[option]['value'] = \
                                req.args.get(arg)
                        for option in clev.action_client_options:
                            arg = 'action-option-%s-%s' \
                                  % (clev.md5,
                                     clev.action_client_options[option]['md5'])
                            clev.action_client_options[option]['value'] = \
                                req.args.get(arg)
                        clev.update_options(client)

                    req.redirect(req.href.admin(cat, page))
                elif 'cancel' in req.args:
                    req.redirect(req.href.admin(cat, page))

            add_script(req, 'common/js/wikitoolbar.js')
            data = {'view': 'detail', 'client': clnt, 'events': events}

        else:
            if req.method == 'POST':
                # Add Client
                if 'add' in req.args and 'name' in req.args:
                    clnt = Client(self.env)
                    clnt.name = req.args.get('name')
                    clnt.insert()
                    req.redirect(req.href.admin(cat, page))

                # Remove clients
                elif 'remove' in req.args and 'sel' in req.args:
                    sel = req.args.getlist('sel')
                    if not sel:
                        raise TracError('No client selected')

                    with self.env.db_transaction:
                        for name in sel:
                            Client(self.env, name).delete()

                    req.redirect(req.href.admin(cat, page))

                # Set default client
                elif 'apply' in req.args and 'default' in req.args:
                    name = req.args.get('default')
                    self.log.info('Setting default client to %s', name)
                    self.config.set('ticket', 'default_client', name)
                    self.config.save()
                    req.redirect(req.href.admin(cat, page))

            default = self.config.get('ticket', 'default_client')
            data = {'view': 'list',
                    'clients': Client.select(self.env),
                    'default': default}

        return 'admin_clients.html', data
