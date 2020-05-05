#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,no-member

from hamcrest import is_
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_property

from zope import component

from nti.app.products.salesforce.interfaces import ISalesforceLogonSettings

import nti.testing.base

ZCML_STRING = """
<configure  xmlns="http://namespaces.zope.org/zope"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            xmlns:zcml="http://namespaces.zope.org/zcml"
            xmlns:your="http://nextthought.com/ntp/salesforce">

    <include package="zope.component" file="meta.zcml" />
    <include package="zope.security" file="meta.zcml" />
    <include package="zope.component" />
    <include package="." file="meta.zcml" />

    <configure>
        <your:registerSalesforceLogonSettings api_endpoint="http://salesforce.api"
                                              api_key="1111111111111"
                                              app_title="salesforce app" />
    </configure>
</configure>
"""


class TestZcml(nti.testing.base.ConfiguringTestBase):

    def test_registration(self):
        self.configure_string(ZCML_STRING)
        logon_settings = component.queryUtility(ISalesforceLogonSettings)
        assert_that(logon_settings, not_none())
        assert_that(logon_settings,
                    has_property('api_endpoint', is_("http://salesforce.api")))
        assert_that(logon_settings,
                    has_property('api_key', is_("1111111111111")))
        assert_that(logon_settings,
                    has_property('app_title', is_("salesforce app")))
