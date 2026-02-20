import logging
import sys
import inspect
from typing import Optional, Any


_OLD_FACTORY = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):
    record = _OLD_FACTORY(*args, **kwargs)
    try:
        frame = inspect.currentframe()
        # walk back to find calling frame outside logging and this module
        f = frame
        classname = ""
        while f:
            modname = f.f_globals.get("__name__", "")
            if modname.startswith("logging") or modname == __name__:
                f = f.f_back
                continue
            if f.f_code.co_name == record.funcName:
                self_obj = f.f_locals.get("self")
                if self_obj is not None:
                    classname = type(self_obj).__name__
                break
            f = f.f_back
        record.classname = classname
    except Exception:
        record.classname = ""
    return record


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """Configure root logging with a detailed formatter and add `classname` to records.

    This function is idempotent — calling it multiple times will not add duplicate handlers.
    """
    logging.setLogRecordFactory(_record_factory)

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = "%(asctime)s %(levelname)s %(name)s %(module)s.%(funcName)s(%(lineno)d) [%(classname)s] - %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        root.setLevel(level)
        root.addHandler(handler)

        if log_file:
            fh = logging.FileHandler(log_file)
            fh.setFormatter(logging.Formatter(fmt))
            root.addHandler(fh)


def get_logger(name_or_obj: Any) -> logging.Logger:
    """Return a logger instance.

    Accepts either a string name or an object (instance or class). If an object
    is given the logger name will be the class name.
    """
    if isinstance(name_or_obj, str):
        name = name_or_obj
    else:
        try:
            # prefer class name for instances
            if hasattr(name_or_obj, "__class__"):
                name = name_or_obj.__class__.__name__
            else:
                name = str(name_or_obj)
        except Exception:
            name = str(name_or_obj)

    return logging.getLogger(name)
import logging
import sys
from typing import Any


class _SafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.__dict__.setdefault("classname", "")
        return super().format(record)


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(stream=sys.stdout)
    fmt = "%(asctime)s %(levelname)s [%(name)s %(classname)s %(funcName)s:%(lineno)d] - %(message)s"
    handler.setFormatter(_SafeFormatter(fmt))
    root.setLevel(level)
    root.addHandler(handler)


def get_logger(name_or_obj: Any) -> logging.Logger:
    if isinstance(name_or_obj, str):
        return logging.getLogger(name_or_obj)

    # If passed an instance, return a LoggerAdapter that injects the class name
    logger = logging.getLogger(name_or_obj.__class__.__module__)
    return logging.LoggerAdapter(logger, {"classname": name_or_obj.__class__.__name__})
