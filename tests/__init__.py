import unittest
import logging

from driver_setup import Settings

import test_driver_open_close


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(test_driver_open_close.test_suite())
    return suite


if __name__ == '__main__':
    logging.basicConfig(level=Settings.current().log_level)
    unittest.main(defaultTest='test_suite', argv=Settings.clean_args())
