import logging
from src.config import settings

logger = logging.getLogger(__name__)


class MockScannerService:
    """Mock scanner that reads from standard input for local macOS testing."""
    def __init__(self):
        self._running = False

    def start(self):
        self._running = True
        logger.info("MockScannerService started. Waiting for terminal input...")

    def read_barcode(self):
        if not self._running:
            return None
        try:
            barcode = input("Mock Scanner (Enter Barcode): ")
            return barcode.strip()
        except (EOFError, KeyboardInterrupt):
            self._running = False
            return None

    def stop(self):
        self._running = False
        logger.info("MockScannerService stopped.")


class EvdevScannerService:
    """
    Reads from HID devices on Linux via evdev.
    Suitable for Raspberry Pi 5 USB Scanners.
    """
    def __init__(self):
        self._running = False
        try:
            import evdev
            self.evdev = evdev
        except ImportError:
            logger.error("evdev not installed. Cannot use EvdevScannerService.")
            self.evdev = None
        self.device = None

    def start(self):
        if not self.evdev:
            return
        
        # Auto-discover keyboard-like device
        devices = [self.evdev.InputDevice(path) for path in self.evdev.list_devices()]
        for dev in devices:
            # Common keywords for barcode scanners
            name_lower = dev.name.lower()
            if "keyboard" in name_lower or "scanner" in name_lower or "barcode" in name_lower:
                self.device = dev
                logger.info(f"Scanner discovered: {dev.name} at {dev.path}")
                # Grab the device to prevent input from leaking to the terminal
                try:
                    self.device.grab()
                except Exception as e:
                    logger.warning(f"Could not grab scanner device exclusively: {e}")
                break
        
        if not self.device:
            logger.error("No barcode scanner device found via evdev.")
        self._running = True

    def read_barcode(self):
        if not self.device or not self._running:
            import time
            time.sleep(1)
            return None
        
        barcode = ""
        try:
            for event in self.device.read_loop():
                if not self._running:
                    break
                if event.type == self.evdev.ecodes.EV_KEY:
                    key_event = self.evdev.categorize(event)
                    if key_event.keystate == key_event.key_down:
                        key_str = key_event.keycode
                        
                        # Support cases where keycode is a list (e.g. shift+key combinations)
                        if isinstance(key_str, list):
                            key_str = key_str[0]
                        
                        if key_str == 'KEY_ENTER':
                            return barcode
                        elif isinstance(key_str, str) and key_str.startswith('KEY_'):
                            char = key_str[4:]
                            if len(char) == 1:
                                barcode += char
                            elif char == 'MINUS':
                                barcode += '-'
        except Exception as e:
            if self._running:
                logger.error(f"Scanner read error: {e}")
        return None

    def stop(self):
        self._running = False
        if self.device:
            try:
                self.device.ungrab()
                self.device.close()
            except Exception:
                pass
        logger.info("EvdevScannerService stopped.")


def get_scanner_service():
    """Factory method based on config."""
    if settings.scanner_mode == "mock":
        return MockScannerService()
    else:
        return EvdevScannerService()
