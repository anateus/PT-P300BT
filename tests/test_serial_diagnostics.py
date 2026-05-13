import io
import unittest
from unittest import mock
from types import SimpleNamespace

import labelmaker
import printlabel


READY_STATUS = bytes.fromhex(
    '80 20 42 30 72 30 00 00 00 00 0c 01 00 00 00 00 '
    '00 00 00 00 00 00 00 00 01 08 00 00 00 00 00 00'
)
COMMUNICATION_ERROR_STATUS = bytes.fromhex(
    '80 20 42 30 72 30 00 00 00 04 0c 01 00 00 00 00 '
    '00 00 02 00 00 00 00 00 01 08 00 00 00 00 00 00'
)
PRINTING_STATUS = bytes.fromhex(
    '80 20 42 30 72 30 00 00 00 00 0c 01 00 00 00 00 '
    '00 00 06 01 00 00 00 00 01 08 00 00 00 00 00 00'
)
PRINT_COMPLETE_STATUS = bytes.fromhex(
    '80 20 42 30 72 30 00 00 00 00 0c 01 00 00 00 00 '
    '00 00 01 00 00 00 00 00 01 08 00 00 00 00 00 00'
)


class FakeSerial:
    def __init__(self, reads=None):
        self.reads = list(reads or [])
        self.writes = []

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def read(self, size=1):
        if self.reads:
            return self.reads.pop(0)
        return b''


class SerialDiagnosticsTests(unittest.TestCase):
    def test_diagnostic_serial_logs_read_and_write_activity(self):
        stream = io.StringIO()
        ser = labelmaker.DiagnosticSerial(
            FakeSerial(reads=[b'\x80 B0']),
            enabled=True,
            stream=stream,
        )

        ser.write(b'\x1b\x69\x53')
        ser.read(32)

        output = stream.getvalue()
        self.assertIn('write 3 bytes: 1b 69 53', output)
        self.assertIn('read requested 32 bytes', output)
        self.assertIn('read returned 4 bytes', output)
        self.assertIn('80 20 42 30', output)

    def test_read_exact_reports_timeout_with_partial_response(self):
        ser = FakeSerial(reads=[b'\x80 '])

        with self.assertRaises(labelmaker.PrinterCommunicationError) as ctx:
            labelmaker.read_exact(ser, 32, 'initial printer status')

        message = str(ctx.exception)
        self.assertIn('initial printer status', message)
        self.assertIn('expected 32 bytes, got 2', message)
        self.assertIn('80 20', message)

    def test_print_job_retries_stale_initial_communication_error_once(self):
        ser = FakeSerial(reads=[COMMUNICATION_ERROR_STATUS, READY_STATUS])
        args = SimpleNamespace(verbose=False, status_only=True)
        stream = io.StringIO()

        with mock.patch('sys.stdout', stream):
            labelmaker.do_print_job(ser, args, b'')

        get_status_command = b'\x1b\x69\x53'
        self.assertEqual(ser.writes.count(get_status_command), 2)
        self.assertIn('Retrying printer status query once', stream.getvalue())

    def test_print_job_waits_past_printing_phase_before_cleanup(self):
        ser = FakeSerial(reads=[READY_STATUS, PRINTING_STATUS, PRINT_COMPLETE_STATUS])
        args = SimpleNamespace(
            verbose=False,
            status_only=False,
            no_feed=False,
            auto_cut=False,
            end_margin=0,
            nocomp=True,
            no_print=False,
        )
        stream = io.StringIO()

        with mock.patch('sys.stdout', stream):
            labelmaker.do_print_job(ser, args, b'\x00' * 16)

        self.assertEqual(ser.writes.count(b'\x1a'), 1)
        self.assertIn('Waiting for print completion', stream.getvalue())
        self.assertIn('All done', stream.getvalue())

    def test_printlabel_accepts_verbose_and_serial_timeout_options(self):
        parser = printlabel.set_args()

        args = parser.parse_args([
            '--verbose',
            '--serial-timeout',
            '3.5',
            '/dev/cu.PT-P300BT2347',
            'font.otf',
            'Test',
        ])

        self.assertTrue(args.verbose)
        self.assertEqual(args.serial_timeout, 3.5)

    def test_extracts_macos_bluetooth_device_name_from_serial_path(self):
        self.assertEqual(
            labelmaker.macos_bluetooth_device_name('/dev/cu.PT-P300BT2347'),
            'PT-P300BT2347',
        )
        self.assertEqual(
            labelmaker.macos_bluetooth_device_name('/dev/tty.PT-P300BT2347'),
            'PT-P300BT2347',
        )
        self.assertIsNone(
            labelmaker.macos_bluetooth_device_name('/dev/cu.Bluetooth-Incoming-Port')
        )
        self.assertIsNone(labelmaker.macos_bluetooth_device_name('/dev/tty.usbserial'))

    def test_printlabel_accepts_status_only(self):
        parser = printlabel.set_args()

        args = parser.parse_args([
            '--status-only',
            '/dev/cu.PT-P300BT2347',
        ])

        self.assertTrue(args.status_only)

    def test_printlabel_cleanup_reset_is_opt_in(self):
        parser = printlabel.set_args()

        default_args = parser.parse_args([
            '/dev/cu.PT-P300BT2347',
            'font.otf',
            'Test',
        ])
        cleanup_args = parser.parse_args([
            '--cleanup-reset',
            '/dev/cu.PT-P300BT2347',
            'font.otf',
            'Test',
        ])

        self.assertFalse(default_args.cleanup_reset)
        self.assertTrue(cleanup_args.cleanup_reset)

    def test_printlabel_accepts_macos_rfcomm_transport(self):
        parser = printlabel.set_args()

        args = parser.parse_args([
            '--macos-rfcomm',
            '--rfcomm-channel',
            '1',
            '/dev/cu.PT-P300BT2347',
            'font.otf',
            'Test',
        ])

        self.assertTrue(args.macos_rfcomm)
        self.assertEqual(args.rfcomm_channel, 1)

    def test_printlabel_rejects_removed_bluetooth_workaround_flags(self):
        parser = printlabel.set_args()

        removed_flags = (
            '--no-macos-bluetooth-reconnect',
            '--restart-bluetoothd-before-connect',
            '--restart-bluetoothd-on-timeout',
            '--bluetoothd-restart-delay',
            '--experimental-destroy-bt-connection',
            '--experimental-rematch-bt-serial-driver',
            '--bt-serial-rematch-delay',
        )
        for flag in removed_flags:
            args = [flag]
            if flag in ('--bluetoothd-restart-delay', '--bt-serial-rematch-delay'):
                args.append('1')
            args.extend(['/dev/cu.PT-P300BT2347', 'font.otf', 'Test'])
            with self.subTest(flag=flag):
                with mock.patch('sys.stderr', io.StringIO()):
                    with self.assertRaises(SystemExit):
                        parser.parse_args(args)


if __name__ == '__main__':
    unittest.main()
