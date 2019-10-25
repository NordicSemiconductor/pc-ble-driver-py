import unittest
from pc_ble_driver_py import config

config.__conn_ic_id__ = 'NRF52'
from pc_ble_driver_py.ble_driver import Flasher

class FlasherParserTestCase(unittest.TestCase):
 
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
        self.assertTrue(
            fw_struct['len'] == 24 and
            fw_struct['magic_number'] == ['17', 'A5', 'D8', '46'] and
            fw_struct['version'] == '4.1.1' and
            fw_struct['baud_rate'] == 1000000 and
            fw_struct['api_version'] == 5
        )


class FlasherMagicNumberTestCase(unittest.TestCase):

    def test_invalid_number(self):
        self.assertEqual(Flasher.is_valid_magic_number(['17', 'A5', 'D8', '45']), False)

    def test_valid_number(self):
        self.assertEqual(Flasher.is_valid_magic_number(['17', 'A5', 'D8', '46']), True)


class FlasherVersionTestCase(unittest.TestCase):

    def test_invalid_version(self):
        self.assertEqual(Flasher.is_valid_version('4.0.0'), False)

    def test_valid_version(self):
        self.assertEqual(Flasher.is_valid_version('4.1.1'), True)


class FlasherBaudRateTestCase(unittest.TestCase):

    def test_invalid_baud_rate(self):
        self.assertEqual(Flasher.is_valid_baud_rate(115200), False)

    def test_valid_baud_rate(self):
        self.assertEqual(Flasher.is_valid_baud_rate(1000000), True)


if __name__ == '__main__':
    unittest.main()
