import unittest
from pc_ble_driver_py import config

config.__conn_ic_id__ = 'NRF52'
from pc_ble_driver_py.ble_driver import Flasher

class FlasherParserTestCase(unittest.TestCase):

    def test_invalid_parse(self):
        fw_struct = Flasher.parse_fw_struct([
            '17', 'A5', 'D8', '46',  # magic number
            '02',  # struct version
            'FF', 'FF', 'FF',  # (reserved for future use)
            '00', '00', '00', '00',  # revision hash
            '04', '01', '01',  # major, minor, patch
            'FF',  # (reserved for future use)
            '05',  # softdevice ble api number
            '01',  # transport type
            'FF', 'FF',  # (reserved for future use)
            '40', '42', '0F', '00'  # baud rate
        ])
        self.assertNotEqual(
            fw_struct,
            {
                'len': 25,
                'magic_number': ['17', 'A5', 'D8', '45'],
                'version': '4.0.1',
                'baud_rate': 1000001,
                'api_version': 3
            }
        )

    def test_valid_parse(self):
        fw_struct = Flasher.parse_fw_struct([
            '17', 'A5', 'D8', '46',  # magic number
            '02',  # struct version
            'FF', 'FF', 'FF',  # (reserved for future use)
            '00', '00', '00', '00',  # revision hash
            '04', '01', '01',  # major, minor, patch
            'FF',  # (reserved for future use)
            '05',  # softdevice ble api number
            '01',  # transport type
            'FF', 'FF',  # (reserved for future use)
            '40', '42', '0F', '00'  # baud rate
        ])
        self.assertEqual(
            fw_struct,
            {
                'len': 24,
                'magic_number': ['17', 'A5', 'D8', '46'],
                'version': '4.1.1',
                'baud_rate': 1000000,
                'api_version': 5
            }
        )


class FlasherMagicNumberTestCase(unittest.TestCase):

    def test_invalid_number(self):
        self.assertFalse(Flasher.is_valid_magic_number(['17', 'A5', 'D8', '45']))

    def test_valid_number(self):
        self.assertTrue(Flasher.is_valid_magic_number(['17', 'A5', 'D8', '46']))


class FlasherVersionTestCase(unittest.TestCase):

    def test_invalid_version(self):
        self.assertFalse(Flasher.is_valid_version('4.0.0'))

    def test_valid_version(self):
        self.assertTrue(Flasher.is_valid_version('4.1.1'))


class FlasherBaudRateTestCase(unittest.TestCase):

    def test_invalid_baud_rate(self):
        self.assertFalse(Flasher.is_valid_baud_rate(115200))

    def test_valid_baud_rate(self):
        self.assertTrue(Flasher.is_valid_baud_rate(1000000))


if __name__ == '__main__':
    unittest.main()
