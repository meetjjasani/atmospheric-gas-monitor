from __future__ import annotations

import traceback
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QObject, QThread, Signal

from prl.core.services.import_service import import_raw_folders


class ImportWorker(QObject):
    """Background worker for the CRDS data pipeline.
    
    Emits progress and finished signals to the UI thread.
    """
    progress = Signal(str)            # Status message
    numeric_progress = Signal(int)    # Percentage (0-100)
    finished = Signal(bool, object)   # (success, result_dict_or_error_str)

    def __init__(self, folder_paths: Iterable[Path], force_reimport: bool = False, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.folder_paths = folder_paths
        self.force_reimport = force_reimport

    def run(self) -> None:
        """Main execution logic for the background thread."""
        try:
            # This is the blocking call to our backend service
            result = import_raw_folders(
                self.folder_paths, 
                force_reimport=self.force_reimport,
                progress_callback=self.progress.emit,
                percentage_callback=self.numeric_progress.emit
            )

            self.progress.emit("Cleaning data and building statistics...")
            # (The pipeline service currently does this in one go, 
            # but we could break it down more for granular progress if needed)
            
            self.finished.emit(True, result)
            
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Import error:\n{error_trace}")
            self.finished.emit(False, str(e))


class ImportThread(QThread):
    """Simple container thread for the ImportWorker."""
    # We follow the QObject.moveToThread pattern for maximum reliability.
    # We do NOT pass a parent to ensure this thread isn't killed by UI destruction.
    def __init__(self, folder_paths: Iterable[Path], force_reimport: bool = False) -> None:
        super().__init__(None) # Parentless!
        self.worker = ImportWorker(folder_paths, force_reimport=force_reimport)
        self.worker.moveToThread(self)
        self.started.connect(self.worker.run)
        
        # Ensure the thread quits gracefully when the worker is done
        self.worker.finished.connect(self.quit)
        self.finished.connect(self.worker.deleteLater)
