import unittest
from pc_ble_driver_py import config

config.__conn_ic_id__ = 'NRF52'
from pc_ble_driver_py.ble_driver import Flasher


class FlasherMagicNumberTestCase(unittest.TestCase):

    def test_invalid_number(self):
        self.assertEqual(Flasher.is_valid_magic_number(
            ['17', 'A5', 'D8', '45']
        ), False)

    def test_valid_number(self):
        self.assertEqual(Flasher.is_valid_magic_number(
            ['17', 'A5', 'D8', '46']
        ), True)


class FlasherVersionTestCase(unittest.TestCase):

    def test_invalid_version(self):
        self.assertEqual(Flasher.is_valid_version(
            ['17', 'A5', 'D8', '46',  # magic number
             '02',  # struct version
             'FF', 'FF', 'FF',  # (reserved for future use)
             '00', '00', '00', '00',  # revision hash
             '04', '00', '00'  # major, minor, patch
             ]), False)

    def test_valid_version(self):
        self.assertEqual(Flasher.is_valid_version(
            ['17', 'A5', 'D8', '46',  # magic number
             '02',  # struct version
             'FF', 'FF', 'FF',  # (reserved for future use)
             '00', '00', '00', '00',  # revision hash
             '04', '00', '03'  # major, minor, patch
             ]), True)


class FlasherBaudRateTestCase(unittest.TestCase):

    def test_invalid_baud_rate(self):
        self.assertEqual(Flasher.is_valid_baud_rate(
            ['17', 'A5', 'D8', '46',  # magic number
             '02',  # struct version
             'FF', 'FF', 'FF',  # (reserved for future use)
             '00', '00', '00', '00',  # revision hash
             '04', '00', '00',  # major, minor, patch
             'FF',  # (reserved for future use)
             '05',  # softdevice ble api number
             '01',  # transport type
             'FF', 'FF',  # (reserved for future use)
             '00', 'C2', '02', '00'  # baud rate
             ]), False)

    def test_valid_baud_rate(self):
        self.assertEqual(Flasher.is_valid_baud_rate(
            ['17', 'A5', 'D8', '46',  # magic number
             '02',  # struct version
             'FF', 'FF', 'FF',  # (reserved for future use)
             '00', '00', '00', '00',  # revision hash
             '04', '00', '00',  # major, minor, patch
             'FF',  # (reserved for future use)
             '05',  # softdevice ble api number
             '01',  # transport type
             'FF', 'FF',  # (reserved for future use)
             '00', 'C2', '01', '00'  # baud rate
             ]), True)


if __name__ == '__main__':
    unittest.main()
