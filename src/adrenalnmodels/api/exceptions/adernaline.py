from abc import ABC, abstractmethod
import sys
from enum import Enum


class AdernalineException(ABC, Exception):
    DEFAULTCODE = 99999

    @abstractmethod
    def getHTTPCode(self):
        return 400

    def __init__(self, code='', message='', *args, **kwargs):
        if isinstance(code, Enum):
            self.error_msg = message or code.value.get('msg', '')
            self.error_code = code.value.get('code', self.DEFAULTCODE)

            try:
                self.error_msg = self.error_msg.format(*args, **kwargs)
            except (IndexError, KeyError):
                pass
        else:
            self.error_code = code or self.DEFAULTCODE
            self.error_msg = message
        self.traceback = sys.exc_info()
        try:
            msg = '[{0}] {1}'.format(
                self.error_code, self.error_msg.format(*args, **kwargs))
            print(msg)
        except (IndexError, KeyError):
            msg = '[{0}] {1}'.format(self.error_code, self.error_msg)
            print(msg)

        super().__init__(msg)