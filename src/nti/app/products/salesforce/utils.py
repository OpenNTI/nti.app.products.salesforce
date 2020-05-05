#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: identity.py 110862 2017-04-18 00:30:43Z carlos.sanchez $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.event import notify

from nti.app.products.salesforce import MessageFactory as _
from nti.app.products.salesforce import raise_http_error

from nti.app.products.salesforce.interfaces import ISalesforceUser

from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.identifiers.utils import get_user_for_external_id

logger = __import__('logging').getLogger(__name__)

PROVIDER_ID = "salesforce"


def set_user_salesforce_id(user, salesforce_id, request):
    """
    Set the given salesforce identity for a user.
    """
    if not salesforce_id:
        raise_http_error(request,
                         _(u"Must provide salesforce_id."),
                         u'NoSalesforceIdsGiven')
    interface.alsoProvides(user, ISalesforceUser)

    identity_container = IUserExternalIdentityContainer(user)
    identity_container.add_external_mapping(PROVIDER_ID, salesforce_id)
    logger.info("Setting Salesforce ID for user (%s) (%s/%s)",
                user.username, PROVIDER_ID, salesforce_id)
    notify(ObjectModifiedFromExternalEvent(user))


def get_user_for_salesforce_id(salesforce_id):
    """
    Find any user associated with the given Salesforce id.
    """
    return get_user_for_external_id(PROVIDER_ID, salesforce_id)
