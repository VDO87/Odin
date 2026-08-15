import os
import tempfile
import unittest
from pathlib import Path

from odin.contracts.events import OdinEvent
from odin.storage.sqlite_store import SQLiteStore


@unittest.skipUnless(Path("/proc/self/fd").exists(), "descriptor count is Linux-specific")
class SQLiteDescriptorLifecycleTests(unittest.TestCase):
    def test_repeated_writes_do_not_accumulate_sqlite_descriptors(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore(Path(tmp) / "audit.sqlite")
            store.initialize()
            before = len(os.listdir("/proc/self/fd"))
            for index in range(256):
                store.record_event(OdinEvent.create(run_id="fd-test", component="test", event=str(index)))
            after = len(os.listdir("/proc/self/fd"))
        self.assertLessEqual(after, before + 3)


if __name__ == "__main__":
    unittest.main()
