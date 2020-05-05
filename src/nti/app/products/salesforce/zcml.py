#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id: zcml.py 124707 2017-12-08 21:48:18Z carlos.sanchez $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

import functools

from zope import interface

from zope.component.zcml import utility

from zope.schema import TextLine

from nti.app.products.salesforce.interfaces import ISalesforceLogonSettings

from nti.app.products.salesforce.model import SalesforceLogonSettings

from nti.common._compat import text_

logger = __import__('logging').getLogger(__name__)


class IRegisterSalesforceLogonSettings(interface.Interface):

    api_endpoint = TextLine(title=u"The salesforce API url", required=True)

    api_key = TextLine(title=u"The salesforce api key", required=True)

    app_title = TextLine(title=u"The salesforce app display title", required=False)


def registerSalesforceLogonSettings(_context, api_endpoint, api_key, app_title):
    factory = functools.partial(SalesforceLogonSettings,
                                api_endpoint=text_(api_endpoint),
                                app_title=text_(app_title),
                                api_key=text_(api_key))
    utility(_context, provides=ISalesforceLogonSettings, factory=factory)
