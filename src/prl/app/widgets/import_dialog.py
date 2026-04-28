from __future__ import annotations

from pathlib import Path

import shiboken6 as shiboken
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QCheckBox,
    QWidget,
    QSizePolicy,
)

import prl.core.services.import_service as service
from prl.app.workers.import_worker import ImportThread


def _count_dat_files(folder: Path) -> int:
    try:
        return sum(1 for _ in folder.rglob("*.dat"))
    except OSError:
        return 0


class ImportDataDialog(QDialog):
    """Two-state import dialog — setup view and progress view are mutually exclusive."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import New Data")
        self.setFixedWidth(520)
        self.setObjectName("importDialog")

        self._selected_paths: list[Path] = []
        self._thread: ImportThread | None = None
        self._advanced_visible = False

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # Build both panels — only one visible at a time
        self._setup_panel    = self._build_setup_panel()
        self._progress_panel = self._build_progress_panel()

        self._root_layout.addWidget(self._setup_panel)
        self._root_layout.addWidget(self._progress_panel)

        self._show_setup()

    # ══════════════════════════════════════════════════════════════════
    # PANEL A — Setup
    # ══════════════════════════════════════════════════════════════════

    def _build_setup_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(0)

        # ── Title ────────────────────────────────────────────────────
        title = QLabel("Import New Data")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(6)

        subtitle = QLabel("Select the folder where your .dat instrument files are stored.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("plotStatus")
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        # ── Step 1 ───────────────────────────────────────────────────
        step1 = QLabel("Step 1 — Choose your data folder")
        step1.setObjectName("sidebarSubtitle")
        layout.addWidget(step1)
        layout.addSpacing(8)

        self.add_btn = QPushButton("＋  Add Data Folder…")
        self.add_btn.setMinimumHeight(36)
        self.add_btn.clicked.connect(self._browse_folders)
        layout.addWidget(self.add_btn)
        layout.addSpacing(10)

        # Folder list — clearly separate from labels below
        self.folder_list = QListWidget()
        self.folder_list.setObjectName("importFolderList")
        self.folder_list.setFixedHeight(80)
        self.folder_list.setVisible(False)
        layout.addWidget(self.folder_list)

        # File count — outside and below the list box
        self.file_count_label = QLabel("")
        self.file_count_label.setObjectName("sidebarSubtitle")
        self.file_count_label.setVisible(False)
        self.file_count_label.setContentsMargins(2, 6, 0, 0)
        layout.addWidget(self.file_count_label)

        # Last import — below file count
        self.last_import_label = QLabel("")
        self.last_import_label.setObjectName("sidebarSubtitle")
        self.last_import_label.setContentsMargins(2, 2, 0, 0)
        self._refresh_last_import()
        layout.addWidget(self.last_import_label)

        layout.addSpacing(18)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")
        layout.addWidget(divider)
        layout.addSpacing(14)

        # ── Step 2 ───────────────────────────────────────────────────
        step2 = QLabel("Step 2 — Import")
        step2.setObjectName("sidebarSubtitle")
        layout.addWidget(step2)
        layout.addSpacing(8)

        self.start_btn = QPushButton("Start Import")
        self.start_btn.setProperty("accent", True)
        self.start_btn.setEnabled(False)
        self.start_btn.setMinimumHeight(44)
        self.start_btn.clicked.connect(self._start_import)
        layout.addWidget(self.start_btn)
        layout.addSpacing(8)

        self.close_btn = QPushButton("Cancel / Close")
        self.close_btn.setMinimumHeight(36)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)
        layout.addSpacing(12)

        # ── Advanced (collapsed toggle) ───────────────────────────────
        self.advanced_toggle = QPushButton("▸  Advanced options")
        self.advanced_toggle.setFlat(True)
        self.advanced_toggle.setObjectName("advancedToggle")
        self.advanced_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.advanced_toggle.setMinimumHeight(32)
        self.advanced_toggle.clicked.connect(self._toggle_advanced)
        layout.addWidget(self.advanced_toggle)

        # Advanced content — hidden by default
        self.advanced_panel = QWidget()
        self.advanced_panel.setVisible(False)
        adv = QVBoxLayout(self.advanced_panel)
        adv.setContentsMargins(12, 8, 0, 0)
        adv.setSpacing(10)

        self.force_reimport_cb = QCheckBox("Re-process all files (ignore previous imports)")
        self.force_reimport_cb.setToolTip(
            "The app normally skips files it has already processed.\n"
            "Enable this only to re-import everything from scratch."
        )
        adv.addWidget(self.force_reimport_cb)

        self.wipe_db_btn = QPushButton("Wipe All Data…")
        self.wipe_db_btn.setProperty("danger", True)
        self.wipe_db_btn.setMinimumHeight(36)
        self.wipe_db_btn.setToolTip(
            "Permanently deletes all imported data.\n"
            "Use only if you want a completely fresh start."
        )
        self.wipe_db_btn.clicked.connect(self._wipe_database)
        adv.addWidget(self.wipe_db_btn)

        layout.addWidget(self.advanced_panel)

        return panel

    # ══════════════════════════════════════════════════════════════════
    # PANEL B — Progress (shown instead of setup while importing)
    # ══════════════════════════════════════════════════════════════════

    def _build_progress_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 48, 28, 32)
        layout.setSpacing(0)

        self._prog_title = QLabel("Importing your data…")
        self._prog_title.setObjectName("sectionTitle")
        self._prog_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._prog_title)
        layout.addSpacing(8)

        self._prog_subtitle = QLabel("")
        self._prog_subtitle.setObjectName("plotStatus")
        self._prog_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._prog_subtitle.setWordWrap(True)
        layout.addWidget(self._prog_subtitle)
        layout.addSpacing(40)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("importProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setMinimumHeight(28)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.progress_bar)
        layout.addSpacing(16)

        self.status_label = QLabel("Scanning for new files…")
        self.status_label.setObjectName("plotStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(52)
        layout.addWidget(self.status_label)
        layout.addSpacing(40)

        self._cancel_import_btn = QPushButton("Cancel Import")
        self._cancel_import_btn.setMinimumHeight(40)
        self._cancel_import_btn.clicked.connect(self._cancel_import)
        layout.addWidget(self._cancel_import_btn)

        return panel

    # ══════════════════════════════════════════════════════════════════
    # State switching — mutual exclusive show/hide
    # ══════════════════════════════════════════════════════════════════

    def _show_setup(self) -> None:
        self._progress_panel.setVisible(False)
        self._setup_panel.setVisible(True)
        self.adjustSize()

    def _show_progress(self) -> None:
        self._setup_panel.setVisible(False)
        self._progress_panel.setVisible(True)
        self.adjustSize()

    # ══════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════

    def _refresh_last_import(self) -> None:
        last = service.get_last_import_date()
        if last:
            self.last_import_label.setText(f"Last import: {last.strftime('%d %b %Y, %H:%M')}")
        else:
            self.last_import_label.setText("Last import: never")

    def _rebuild_folder_list(self) -> None:
        self.folder_list.clear()
        for path in self._selected_paths:
            count = _count_dat_files(path)
            item = QListWidgetItem(f"  {path}   [{count:,} file{'s' if count != 1 else ''}]")
            item.setToolTip(str(path))
            self.folder_list.addItem(item)
        self.folder_list.setVisible(bool(self._selected_paths))

    def _refresh_summary(self) -> None:
        if not self._selected_paths:
            self.file_count_label.setVisible(False)
            self.start_btn.setEnabled(False)
            return
        total = sum(_count_dat_files(p) for p in self._selected_paths)
        if total == 0:
            self.file_count_label.setText("⚠️  No .dat files found in selected folder(s).")
        else:
            self.file_count_label.setText(
                f"✓  {total:,} .dat file{'s' if total != 1 else ''} ready to import."
            )
        self.file_count_label.setVisible(True)
        self.start_btn.setEnabled(total > 0)
        self.adjustSize()

    def _toggle_advanced(self) -> None:
        self._advanced_visible = not self._advanced_visible
        self.advanced_panel.setVisible(self._advanced_visible)
        arrow = "▾" if self._advanced_visible else "▸"
        self.advanced_toggle.setText(f"{arrow}  Advanced options")
        self.adjustSize()

    # ══════════════════════════════════════════════════════════════════
    # Slots
    # ══════════════════════════════════════════════════════════════════

    def _browse_folders(self) -> None:
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dialog.exec():
            added = False
            for p in dialog.selectedFiles():
                path = Path(p)
                if path not in self._selected_paths:
                    self._selected_paths.append(path)
                    added = True
            if added:
                self._rebuild_folder_list()
                self._refresh_summary()

    def _start_import(self) -> None:
        if not self._selected_paths:
            return

        total = sum(_count_dat_files(p) for p in self._selected_paths)
        folder_names = ", ".join(p.name for p in self._selected_paths[:2])
        if len(self._selected_paths) > 2:
            folder_names += f" +{len(self._selected_paths) - 2} more"

        self._prog_title.setText("Importing your data…")
        self._prog_subtitle.setText(
            f"Processing {total:,} file{'s' if total != 1 else ''} from: {folder_names}"
        )
        self.progress_bar.setValue(0)
        self.status_label.setText("Scanning for new files…")

        self._show_progress()

        force = self.force_reimport_cb.isChecked()
        self._thread = ImportThread(self._selected_paths, force_reimport=force)
        self._thread.worker.progress.connect(self.status_label.setText)
        self._thread.worker.numeric_progress.connect(self.progress_bar.setValue)
        self._thread.worker.finished.connect(self._on_finished)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _cancel_import(self) -> None:
        if self._safe_thread_check():
            reply = QMessageBox.question(
                self, "Cancel Import?",
                "Import is still running. Cancel it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._thread.terminate()
                self._thread.wait()
                self._show_setup()
        else:
            self._show_setup()

    def _on_finished(self, success: bool, result: object) -> None:
        if success and isinstance(result, dict):
            new_files = result.get("new_files", 0)
            skipped   = result.get("skipped_files", 0)
            rows      = result.get("row_count", 0)

            self.progress_bar.setValue(100)
            self.status_label.setText("Done!")
            self._prog_title.setText("Import Complete")

            if new_files == 0:
                msg = (
                    f"Everything is already up to date.\n\n"
                    f"Skipped {skipped} file(s) that were already imported."
                )
            else:
                msg = (
                    f"Import finished successfully!\n\n"
                    f"  • {new_files} new file(s) processed\n"
                    f"  • {skipped} file(s) already up to date\n"
                    f"  • {rows:,} data points added\n\n"
                    f"The dashboard is ready."
                )
            QMessageBox.information(self, "Done", msg)
            self._refresh_last_import()
            self.accept()
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText("Import failed.")
            QMessageBox.critical(
                self, "Import Failed",
                f"Something went wrong:\n\n{result}\n\n"
                f"Please check your folder and try again."
            )
            self._prog_title.setText("Importing your data…")
            self._show_setup()

    def _wipe_database(self) -> None:
        reply = QMessageBox.warning(
            self, "Wipe All Data?",
            "This will permanently delete ALL imported data.\n\n"
            "You will need to re-import your folders afterwards.\n\n"
            "Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            service.clear_database()
            QMessageBox.information(self, "Done", "All data has been cleared.")
            self._selected_paths.clear()
            self._rebuild_folder_list()
            self._refresh_summary()
            self._refresh_last_import()

    def _safe_thread_check(self) -> bool:
        try:
            return (
                self._thread is not None
                and shiboken.isValid(self._thread)
                and self._thread.isRunning()
            )
        except RuntimeError:
            return False

    def closeEvent(self, event) -> None:
        if self._safe_thread_check():
            reply = QMessageBox.question(
                self, "Cancel Import?",
                "Import is still running. Close and cancel it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._thread.terminate()
                self._thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
