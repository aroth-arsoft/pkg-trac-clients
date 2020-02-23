# -*- coding: utf-8 -*-

import StringIO

from trac.core import Component, implements
from trac.wiki.api import IWikiMacroProvider
from trac.wiki.formatter import format_to_oneliner
from trac.wiki.parser import WikiParser


class ClientWikiProcessor(Component):

    implements(IWikiMacroProvider)

    def get_macros(self):
        return ['client']

    def get_macro_description(self, name):
        return "No real formatting but allows for easy extraction of " \
               "specific text blocks designed to be displayed to the client"

    def expand_macro(self, formatter, name, content):
        return '<fieldset class="client"><legend>' \
               'Comments to Client</legend>%s</fieldset>' \
               % format_to_oneliner(content, self.env, formatter.req)


def extract_client_text(text, sep="----\n"):
    buf = StringIO.StringIO()
    stack = 0
    gotblock = False
    realsep = ''
    for line in text.splitlines():
        if stack:
            realsep = sep
            if line.strip() == WikiParser.ENDBLOCK:
                stack = stack - 1
            if stack:
                buf.write(line + "\n")
                realsep = ''
        if gotblock:
            if line.strip() == '#!client':
                stack = stack + 1
                if stack == 1:
                    buf.write(realsep)
            else:
                gotblock = False
        elif line.strip() == WikiParser.STARTBLOCK:
            gotblock = True
    return buf.getvalue()


class TestProcessor(Component):

    implements(IWikiMacroProvider)

    def get_macros(self):
        return ['clientx']

    def get_macro_description(self, name):
        return 'Just a test'

    def expand_macro(self, formatter, name, content):
        for raw_text, in self.env.db_query("""
                SELECT text FROM wiki
                WHERE name=%s
                ORDER BY version DESC LIMIT 1
                """, ("WikiStart",)):
            text = extract_client_text(raw_text)
            return format_to_oneliner(text, self.env, formatter.req)
