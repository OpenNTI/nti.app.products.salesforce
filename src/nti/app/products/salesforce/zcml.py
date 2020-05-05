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

from nti.common.cypher import get_plaintext

from nti.schema.field import HTTPURL

logger = __import__('logging').getLogger(__name__)


class IRegisterSalesforceLogonSettings(interface.Interface):

    client_id = TextLine(title=u'The OAuth2 client id',
                         required=True)

    client_secret = TextLine(title=u'The OAuth2 client secret',
                             required=True)

    app_title = TextLine(title=u"The salesforce app display title", required=False)

    login_url = HTTPURL(title=u'The url the client should be sent to in order to initiate the log in process',
                        required=True)

    token_url = HTTPURL(title=u'The token url',
                        required=True)

    user_info_url = HTTPURL(title=u'The url to fetch user information',
                        required=True)


def registerSalesforceLogonSettings(_context, client_id, client_secret, app_title,
                                    login_url,
                                    user_info_url,
                                    token_url):
    factory = functools.partial(SalesforceLogonSettings,
                                client_id=text_(client_id),
                                app_title=text_(app_title),
                                client_secret=get_plaintext(client_secret),
                                login_url=login_url,
                                user_info_url=user_info_url,
                                token_url=token_url)
    utility(_context, provides=ISalesforceLogonSettings, factory=factory)
