import sys
import pytest


driver_in_sys_args = any('--driver' in arg.lower() for arg in sys.argv)
pytestmark = pytest.mark.skipif(not driver_in_sys_args,
                                reason="Skipped as --driver was not provided in the cli arguments")


def test_billing_portal(billing_portal_data, selenium_go_to_billing_portal):
    session = billing_portal_data['session']
    assert selenium_go_to_billing_portal.current_url == session["url"]
