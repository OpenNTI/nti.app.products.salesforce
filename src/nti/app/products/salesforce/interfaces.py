#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,expression-not-assigned

from zope import interface

from zope.interface import Attribute

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from nti.schema.field import ValidTextLine as TextLine


class ISalesforceUser(interface.Interface):
    """
    Marker interface for a user created via Salesforce.
    """


class ISalesforceLogonSettings(interface.Interface):

    api_endpoint = TextLine(title=u"The Salesforce API url", required=True)

    api_key = TextLine(title=u"The Salesforce api key", required=True)

    app_title = TextLine(title=u"The salesforce app display title", required=False)


class ISalesforceUserCreatedEvent(IObjectEvent):
    """
    Fired after an Google user has been created
    """
    request = Attribute(u"Request")


@interface.implementer(ISalesforceUserCreatedEvent)
class SalesforceUserCreatedEvent(ObjectEvent):

    def __init__(self, obj, request=None):
        super(SalesforceUserCreatedEvent, self).__init__(obj)
        self.request = request


class ISalesforceUserLogonEvent(IObjectEvent):
    """
    Fired after an salesforce user has logged on
    """
    request = Attribute(u"Request")


@interface.implementer(ISalesforceUserLogonEvent)
class SalesforceUserLogonEvent(ObjectEvent):

    def __init__(self, obj, external_values=None, request=None):
        super(SalesforceUserLogonEvent, self).__init__(obj)
        self.request = request
        self.external_values = external_values or {}

