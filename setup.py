#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(name='TracClients',
      description="Plugin to allow management of which ticket belong to "
                  "which client",
      keywords='trac plugin ticket client',
      version='0.5',
      url='https://www.trac-hacks.org/wiki/ClientsPlugin',
      license='http://www.opensource.org/licenses/mit-license.php',
      author='Colin Guthrie',
      author_email='trac@colin.guthr.ie',
      packages=find_packages(exclude=['*.tests']),
      package_data={'clients': ['templates/*.html', 'htdocs/*.css']},
      entry_points={
          'trac.plugins': [
              'clients.api = clients.api',
              'clients.client = clients.client',
              'clients.model = clients.model',
              'clients.admin = clients.admin',
              'clients.events = clients.events',
              'clients.eventsadmin = clients.eventsadmin',
              'clients.processor = clients.processor',
              'clients.summary = clients.summary',
              'clients.summary_milestone = clients.summary_milestone',
              'clients.summary_ticketchanges = clients.summary_ticketchanges',
              'clients.summary_monthlyhours = clients.summary_monthlyhours',
              'clients.action = clients.action',
              'clients.action_email = clients.action_email',
              'clients.action_zendesk_forum = clients.action_zendesk_forum',
          ]
      },
      install_requires=['Trac', 'lxml'],
      test_suite='clients.tests.test_suite',
      tests_require=[]
      )
