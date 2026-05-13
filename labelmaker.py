#!/usr/bin/env python

from labelmaker_encode import encode_raster_transfer, read_png

import argparse
import sys
import contextlib
import os
import platform
import time
import threading
import ptcbp
import ptstatus
import serial

BARS = '123456789'
DEFAULT_SERIAL_TIMEOUT = 10.0
DEFAULT_PRINT_STATUS_FRAMES = 20
DEFAULT_RFCOMM_CHANNEL = 1


class PrinterCommunicationError(RuntimeError):
    pass


def _format_bytes(data, limit=64):
    if not data:
        return '<none>'
    hex_data = bytes(data[:limit]).hex(' ')
    if len(data) > limit:
        hex_data += f' ... (+{len(data) - limit} bytes)'
    return hex_data


class DiagnosticSerial:
    def __init__(self, ser, enabled=False, stream=None):
        self._ser = ser
        self.enabled = enabled
        self.stream = stream or sys.stderr
        self._started_at = time.monotonic()

    def _log(self, message):
        if self.enabled:
            elapsed = time.monotonic() - self._started_at
            print(f'[serial +{elapsed:0.3f}s] {message}', file=self.stream)

    def write(self, data):
        self._log(f'write {len(data)} bytes: {_format_bytes(data)}')
        start = time.monotonic()
        written = self._ser.write(data)
        self._log(f'write returned {written} in {time.monotonic() - start:0.3f}s')
        return written

    def read(self, size=1):
        self._log(f'read requested {size} bytes')
        start = time.monotonic()
        data = self._ser.read(size)
        self._log(
            f'read returned {len(data)} bytes in {time.monotonic() - start:0.3f}s: '
            f'{_format_bytes(data)}'
        )
        return data

    def __getattr__(self, name):
        return getattr(self._ser, name)


class MacOSRFCOMMSerial:
    def __init__(self, device_name, channel, timeout=DEFAULT_SERIAL_TIMEOUT):
        if platform.system() != 'Darwin':
            raise PrinterCommunicationError('RFCOMM transport is only supported on macOS')
        try:
            import objc
            from Foundation import NSDate, NSObject, NSRunLoop
            from IOBluetooth import IOBluetoothDevice
        except ImportError as e:
            raise PrinterCommunicationError(
                'PyObjC IOBluetooth is not installed. Run uv sync or install pyobjc-framework-IOBluetooth.'
            ) from e

        self._NSDate = NSDate
        self._NSRunLoop = NSRunLoop
        self.timeout = serial_timeout_value(timeout)
        self.device_name = device_name
        self.channel_id = channel
        self._buffer = bytearray()
        self._condition = threading.Condition()
        self._closed = False

        owner = self

        class RFCOMMDelegate(NSObject):
            def init(self):
                self = objc.super(RFCOMMDelegate, self).init()
                return self

            def rfcommChannelData_data_length_(self, _rfcomm_channel, data, length):
                if isinstance(data, bytes):
                    chunk = data[:length]
                else:
                    chunk = bytes(data[:length])
                with owner._condition:
                    owner._buffer.extend(chunk)
                    owner._condition.notify_all()

            def rfcommChannelClosed_(self, _rfcomm_channel):
                with owner._condition:
                    owner._closed = True
                    owner._condition.notify_all()

        self._delegate = RFCOMMDelegate.alloc().init()
        device = None
        for candidate in IOBluetoothDevice.pairedDevices() or []:
            identifiers = {
                _objc_value(candidate, 'name'),
                _objc_value(candidate, 'nameOrAddress'),
                _objc_value(candidate, 'addressString'),
            }
            if device_name in identifiers:
                device = candidate
                break
        if device is None:
            raise PrinterCommunicationError(f'Bluetooth device "{device_name}" is not paired or visible')

        result, rfcomm_channel = device.openRFCOMMChannelSync_withChannelID_delegate_(
            None,
            channel,
            self._delegate,
        )
        if int(result) != 0:
            raise PrinterCommunicationError(
                f'Could not open RFCOMM channel {channel} for "{device_name}": IOReturn 0x{int(result):08x}'
            )
        self._device = device
        self._channel = rfcomm_channel

    def _pump_run_loop(self, seconds):
        self._NSRunLoop.currentRunLoop().runUntilDate_(
            self._NSDate.dateWithTimeIntervalSinceNow_(seconds)
        )

    def write(self, data):
        offset = 0
        while offset < len(data):
            chunk = data[offset:offset + 320]
            result = self._channel.writeSync_length_(chunk, len(chunk))
            if int(result) != 0:
                raise PrinterCommunicationError(
                    f'RFCOMM write failed on channel {self.channel_id}: IOReturn 0x{int(result):08x}'
                )
            offset += len(chunk)
        return len(data)

    def read(self, size=1):
        deadline = None if self.timeout is None else time.monotonic() + self.timeout
        while True:
            with self._condition:
                if len(self._buffer) >= size:
                    chunk = bytes(self._buffer[:size])
                    del self._buffer[:size]
                    return chunk
                if self._closed:
                    chunk = bytes(self._buffer)
                    self._buffer.clear()
                    return chunk
                if deadline is not None and time.monotonic() >= deadline:
                    chunk = bytes(self._buffer)
                    self._buffer.clear()
                    return chunk
            self._pump_run_loop(0.05)

    def close(self):
        if self._closed:
            return
        result = self._channel.closeChannel()
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        if int(result) != 0:
            raise PrinterCommunicationError(
                f'RFCOMM close failed on channel {self.channel_id}: IOReturn 0x{int(result):08x}'
            )

    def get_settings(self):
        return {
            'transport': 'macos-rfcomm',
            'device_name': self.device_name,
            'channel': self.channel_id,
            'timeout': self.timeout,
        }


def serial_timeout_value(timeout):
    if timeout == 0:
        return None
    return timeout


def _objc_value(obj, *names):
    for name in names:
        value = getattr(obj, name, None)
        if callable(value):
            value = value()
        if value is not None:
            return str(value)
    return None


def macos_bluetooth_device_name(comport):
    basename = os.path.basename(comport)
    for prefix in ('cu.', 'tty.'):
        if not basename.startswith(prefix):
            continue
        device_name = basename[len(prefix):]
        if device_name == 'Bluetooth-Incoming-Port':
            return None
        if device_name.startswith('usb') or 'usbserial' in device_name:
            return None
        return device_name
    return None


def open_printer_port(
    comport,
    timeout=DEFAULT_SERIAL_TIMEOUT,
    write_timeout=DEFAULT_SERIAL_TIMEOUT,
    verbose=False,
    macos_rfcomm=False,
    rfcomm_channel=DEFAULT_RFCOMM_CHANNEL,
):
    if macos_rfcomm:
        device_name = macos_bluetooth_device_name(comport) or comport
        ser = MacOSRFCOMMSerial(device_name, rfcomm_channel, timeout=timeout)
    else:
        ser = serial.Serial(
            comport,
            timeout=serial_timeout_value(timeout),
            write_timeout=serial_timeout_value(write_timeout),
        )
    wrapped = DiagnosticSerial(ser, enabled=verbose)
    if verbose:
        wrapped._log(f'opened {comport}')
        with contextlib.suppress(Exception):
            wrapped._log(f'settings: {ser.get_settings()}')
    return wrapped


def open_printer_port_from_args(args):
    return open_printer_port(
        args.comport,
        timeout=args.serial_timeout,
        verbose=args.verbose,
        macos_rfcomm=args.macos_rfcomm,
        rfcomm_channel=args.rfcomm_channel,
    )


def read_exact(ser, size, context):
    data = ser.read(size)
    if len(data) != size:
        raise PrinterCommunicationError(
            f'Timed out waiting for {context}: expected {size} bytes, got {len(data)}. '
            f'Partial response: {_format_bytes(data)}'
        )
    return data


def is_ready(status):
    return status.err == 0x0000 and status.phase_type == 0x00 and status.phase == 0x0000


def is_recoverable_initial_communication_error(status):
    return (
        status.err == 0x0004
        and status.status_type == 0x02
        and status.phase_type == 0x00
        and status.phase == 0x0000
    )


def is_printing(status):
    return status.err == 0x0000 and status.phase_type == 0x01 and status.phase == 0x0000


def is_print_complete(status):
    return status.err == 0x0000 and (
        status.status_type == 0x01
        or (status.status_type == 0x06 and status.phase_type == 0x00 and status.phase == 0x0000)
    )


def query_printer_status(ser, context):
    reset_printer(ser)
    ser.write(ptcbp.serialize_control('get_status'))
    return ptstatus.unpack_status(read_exact(ser, 32, context))


def wait_for_print_completion(ser, args):
    print('=> Waiting for print completion...', flush=True)
    max_frames = getattr(args, 'print_status_frames', DEFAULT_PRINT_STATUS_FRAMES)
    last_status = None
    for frame_index in range(max_frames):
        status = ptstatus.unpack_status(
            read_exact(ser, 32, f'print status frame {frame_index + 1}')
        )
        last_status = status
        ptstatus.print_status(status, verbose=getattr(args, 'verbose', False))
        if is_print_complete(status):
            return status
        if status.err != 0x0000:
            raise PrinterCommunicationError('Printer reported an error while printing')
        if not is_printing(status):
            return status
    raise PrinterCommunicationError(
        f'Timed out waiting for print completion after {max_frames} status frames. '
        f'Last status type: 0x{last_status.status_type:02x}'
    )


def run_print_job(args, data):
    ser = None
    communication_failed = False
    try:
        ser = open_printer_port_from_args(args)
        do_print_job(ser, args, data)
    except PrinterCommunicationError:
        communication_failed = True
        raise
    finally:
        if ser is not None:
            if args.cleanup_reset and not communication_failed:
                with contextlib.suppress(Exception):
                    reset_printer(ser)
            with contextlib.suppress(Exception):
                ser.close()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('comport', help='Printer COM port.')
    p.add_argument('-i', '--image', help='Image file to print.')
    p.add_argument('--status-only', help='Only query and print printer status; do not send image data or print.', action='store_true')
    p.add_argument('-n', '--no-print', help='Only configure the printer and send the image but do not send print command.', action='store_true')
    p.add_argument('-F', '--no-feed', help='Disable feeding at the end of the print (chaining).')
    p.add_argument('-a', '--auto-cut', help='Enable auto-cutting (or print label boundary on e.g. PT-P300BT).')
    p.add_argument('-m', '--end-margin', help='End margin (in dots).', default=0, type=int)
    p.add_argument('-r', '--raw', help='Send the image to printer as-is without any pre-processing.', action='store_true')
    p.add_argument('-C', '--nocomp', help='Disable compression.', action='store_true')
    p.add_argument('-v', '--verbose', help='Print serial diagnostics and verbose printer status.', action='store_true')
    p.add_argument(
        '--print-status-frames',
        help='Maximum number of status frames to read after sending the print command. (default: 20)',
        default=DEFAULT_PRINT_STATUS_FRAMES,
        type=int,
    )
    p.add_argument(
        '--cleanup-reset',
        help='Send a printer reset during cleanup after a successful job. Disabled by default on macOS Bluetooth serial.',
        action='store_true',
    )
    p.add_argument(
        '--serial-timeout',
        help='Seconds to wait for printer responses. Use 0 to wait forever. (default: 10)',
        default=DEFAULT_SERIAL_TIMEOUT,
        type=float,
    )
    p.add_argument(
        '--macos-rfcomm',
        help='On macOS, bypass /dev/cu.* and talk directly to the printer RFCOMM channel.',
        action='store_true',
    )
    p.add_argument(
        '--rfcomm-channel',
        help='RFCOMM channel to use with --macos-rfcomm. PT-P300BT Serial Port Profile is usually channel 1.',
        default=DEFAULT_RFCOMM_CHANNEL,
        type=int,
    )
    return p, p.parse_args()

def reset_printer(ser):
    # Flush print buffer
    ser.write(b"\x00" * 64)

    # Initialize
    ser.write(ptcbp.serialize_control('reset'))

    # Enter raster graphics (PTCBP) mode
    ser.write(ptcbp.serialize_control('use_command_set', ptcbp.CommandSet.ptcbp))

def configure_printer(ser, raster_lines, tape_dim, compress=True, chaining=False, auto_cut=False, end_margin=0):
    reset_printer(ser)

    type_, width, length = tape_dim
    # Set media & quality
    ser.write(ptcbp.serialize_control_obj('set_print_parameters', ptcbp.PrintParameters(
        active_fields=(ptcbp.PrintParameterField.width |
                       ptcbp.PrintParameterField.quality |
                       ptcbp.PrintParameterField.recovery),
        media_type=type_,
        width_mm=width, # Tape width in mm
        length_mm=length, # Label height in mm (0 for continuous roll)
        length_px=raster_lines, # Number of raster lines in image data
        is_follow_up=0, # Unused
        sbz=0, # Unused
    )))

    pm, pm2 = 0, 0
    if not chaining:
        pm2 |= ptcbp.PageModeAdvanced.no_page_chaining
    if auto_cut:
        pm |= ptcbp.PageMode.auto_cut

    # Set print chaining off (0x8) or on (0x0)
    ser.write(ptcbp.serialize_control('set_page_mode_advanced', pm2))

    # Set no mirror, no auto tape cut
    ser.write(ptcbp.serialize_control('set_page_mode', pm))

    # Set margin amount (feed amount)
    ser.write(ptcbp.serialize_control('set_page_margin', end_margin))

    # Set compression mode: TIFF
    ser.write(ptcbp.serialize_control('compression', ptcbp.CompressionType.rle if compress else ptcbp.CompressionType.none))

def do_print_job(ser, args, data):
    print('=> Querying printer status...', flush=True)

    status = query_printer_status(ser, 'initial printer status')
    ptstatus.print_status(status, verbose=getattr(args, 'verbose', False))

    if is_recoverable_initial_communication_error(status):
        print('=> Retrying printer status query once after communication error...', flush=True)
        status = query_printer_status(ser, 'retried initial printer status')
        ptstatus.print_status(status, verbose=getattr(args, 'verbose', False))

    if not is_ready(status):
        print('** Printer indicates that it is not ready. Refusing to continue.')
        sys.exit(1)

    if getattr(args, 'status_only', False):
        print('=> Status query completed.')
        return

    print('=> Configuring printer...')

    raster_lines = len(data) // 16
    configure_printer(ser, raster_lines, (status.tape_type,
                                          status.tape_width,
                                          status.tape_length),
                      chaining=args.no_feed,
                      auto_cut=args.auto_cut,
                      end_margin=args.end_margin,
                      compress=not args.nocomp)

    # Send image data
    print(f"=> Sending image data ({raster_lines} lines)...")
    sys.stdout.write('[')
    for line in encode_raster_transfer(data, args.nocomp):
        if line[0:1] == b'G':
            sys.stdout.write(BARS[min((len(line) - 3) // 2, 7) + 1])
        elif line[0:1] == b'Z':
            sys.stdout.write(BARS[0])
        sys.stdout.flush()
        ser.write(line)
    sys.stdout.write(']')

    print()
    print("=> Image data was sent successfully. Printing will begin soon.")

    if not args.no_print:
        # Print and feed
        ser.write(ptcbp.serialize_control('print'))
        wait_for_print_completion(ser, args)

    print("=> All done.")

def main():
    p, args = parse_args()

    data = None
    if args.status_only:
        data = b''
    elif args.image is None:
        p.error('An image must be specified for printing job.')
    else:
        # Read input image into memory
        if args.raw:
            data = read_png(args.image, False, False, False)
        else:
            data = read_png(args.image)

    sys.stdout.flush()
    try:
        assert data is not None
        run_print_job(args, data)
    except PrinterCommunicationError as e:
        sys.stdout.flush()
        print(f'{p.prog}: error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
