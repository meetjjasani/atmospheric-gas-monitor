from __future__ import annotations

import shutil
from pathlib import Path
import tempfile

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineDownloadRequest
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QLabel, QMenu, QSizePolicy, 
    QVBoxLayout, QWidget
)

import plotly.graph_objects as go
from plotly.offline.offline import get_plotlyjs


class PlotSection(QWidget):
    """Panel that hosts the responsive Plotly web view."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("plotSection")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._theme_name = "light"
        self._figure: go.Figure | None = None
        self._message: str | None = "Choose a section to load data."
        self.current_html = ""
        self._is_loading = False
        self.smart_filename = ""
        self.full_title = "Chart View"


        self.preview_dir = Path(tempfile.gettempdir()) / "prl_plotly_preview"
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        self.preview_path = self.preview_dir / "plot_section_preview.html"
        self.plotly_js_path = self.preview_dir / "plotly.min.js"
        
        self.web_view = QWebEngineView(self)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.web_view.customContextMenuRequested.connect(self._show_context_menu)
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # ── Settings ──────────────────────────────────────────────────
        profile = self.web_view.page().profile()
        profile.downloadRequested.connect(self._handle_download)
        
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        
        # ── UI Construction ───────────────────────────────────────────
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(0)
        
        self.layout.addWidget(self.web_view)
        
        self.show_message(self._message)

    def set_heading(self, title: str, subtitle: str) -> None:
        """Deprecated: headings are now handled in-plot for maximum space."""
        pass

    def set_theme(self, theme_name: str) -> None:
        self._theme_name = theme_name
        if self._figure is not None:
            self._render_figure(self._figure)
        elif self._message:
            self._render_message(self._message)

    def set_figure(self, figure: go.Figure) -> None:
        """DEPRECATED: Use set_plot_html to avoid blocking the UI thread."""
        self._figure = go.Figure(figure)
        self._message = None
        self._is_loading = False
        self._render_figure(self._figure)

    def set_plot_html(self, html: str) -> None:
        """Load a pre-rendered HTML string directly into the web view."""
        self._figure = None
        self._message = None
        self._is_loading = False
        self.current_html = html
        self.preview_path.write_text(self.current_html, encoding="utf-8")
        self.web_view.load(QUrl.fromLocalFile(str(self.preview_path)))

    def show_message(self, message: str) -> None:
        self._figure = None
        self._message = message
        self._is_loading = False
        self._render_message(message)

    def set_loading(self, loading: bool) -> None:
        """Inform the user that a background task is running."""
        self._is_loading = loading
        if loading:
            self._render_message("Analyzing data and building charts...")

    def save_html(self) -> bool:
        if not self.current_html:
            return False

        suggested_name = f"{self.smart_filename}.html" if self.smart_filename else ""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save interactive chart",
            suggested_name,
            "HTML Files (*.html)",
        )
        if not path:
            return False
        if not path.lower().endswith(".html"):
            path = f"{path}.html"

        # Replace local plotly.min.js with web CDN so the standalone HTML file works perfectly on any computer
        export_html = self.current_html.replace(
            "<script src='plotly.min.js'></script>",
            "<script src='https://cdn.plot.ly/plotly-2.32.0.min.js'></script>"
        )
        Path(path).write_text(export_html, encoding="utf-8")
        return True

    def _render_figure(self, figure: go.Figure) -> None:
        themed = self._apply_figure_theme(go.Figure(figure))
        if not self.plotly_js_path.exists():
            self.plotly_js_path.write_text(get_plotlyjs(), encoding="utf-8")

        body = themed.to_html(
            include_plotlyjs=False,
            full_html=False,
            config={
                "displaylogo": False,
                "responsive": True,
                "displayModeBar": True,
                "scrollZoom": True,
                "modeBarButtonsToRemove": ["lasso2d"],
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": self.smart_filename or "plot",
                    "scale": 2,
                },
            },
            default_width="100%",
            default_height="100%",
        )

        self.current_html = self._wrap_html(body)
        self.preview_path.write_text(self.current_html, encoding="utf-8")
        self.web_view.load(QUrl.fromLocalFile(str(self.preview_path)))

    def _render_message(self, message: str) -> None:
        background = "#ffffff" if self._theme_name == "light" else "#252c36"
        foreground = "#334155" if self._theme_name == "light" else "#e2e8f0"
        
        self.current_html = (
            "<html><body style='margin:0;display:flex;align-items:center;justify-content:center;"
            f"height:100vh;background:{background};color:{foreground};"
            "font-family:Segoe UI, sans-serif;'>"
            f"<div style='font-size:16px;font-weight:600;'>{message}</div></body></html>"
        )
        self.preview_path.write_text(self.current_html, encoding="utf-8")
        self.web_view.load(QUrl.fromLocalFile(str(self.preview_path)))

    def _wrap_html(self, body: str) -> str:
        background = "#ffffff" if self._theme_name == "light" else "#252c36"

        return (
            "<html><head><meta charset='utf-8'>"
            "<script src='plotly.min.js'></script>"
            "<style>"
            f"html,body{{margin:0;padding:0;background:{background};width:100%;height:100%;overflow:hidden;}}"
            "body{font-family:Segoe UI, sans-serif;}"
            "#plot-host{width:100%;height:100vh;min-height:300px;}"
            ".plotly-graph-div{width:100% !important;height:100% !important;min-height:300px;}"
            ".modebar-container{position: absolute !important; top: 10px !important; left: 0 !important; width: 100% !important; display: flex !important; justify-content: center !important; height: 32px !important; z-index: 10000 !important; background: transparent !important; pointer-events: none !important;}"
            f".modebar{{pointer-events: auto !important; display: flex !important; flex-direction: row !important; align-items: center !important; background: {background} !important; border-radius: 10px !important; padding: 2px 14px !important; border: 1px solid rgba(128,128,128,0.25) !important; box-shadow: 0 3px 12px rgba(0,0,0,0.15) !important;}}"
            ".modebar-group{display: flex !important; flex-direction: row !important; white-space: nowrap !important; margin: 0 2px !important; padding: 0 !important;}"
            "</style></head>"
            f"<body><div id='plot-host'>{body}</div>"
            "<script>"
            "const resizePlots=()=>{document.querySelectorAll('.plotly-graph-div').forEach((node)=>{"
            "if(window.Plotly){window.Plotly.Plots.resize(node);}});};"
            "window.addEventListener('resize', resizePlots);"
            "new ResizeObserver(resizePlots).observe(document.body);"
            "setTimeout(resizePlots, 40);"
            "</script></body></html>"
        )

    def _apply_figure_theme(self, figure: go.Figure) -> go.Figure:
        if self._theme_name == "dark":
            figure.update_layout(
                template="plotly_dark",
                paper_bgcolor="#252c36",
                plot_bgcolor="#252c36",
                font=dict(color="#e2e8f0"),
            )
            figure.update_xaxes(
                gridcolor="#3b4552",
                linecolor="#64748b",
                zerolinecolor="#3b4552",
                color="#e2e8f0",
            )
            figure.update_yaxes(
                gridcolor="#3b4552",
                linecolor="#64748b",
                zerolinecolor="#3b4552",
                color="#e2e8f0",
            )
        else:
            figure.update_layout(
                template="plotly_white",
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                font=dict(color="#1f2937"),
            )
            figure.update_xaxes(
                gridcolor="#dbe2ea",
                linecolor="#94a3b8",
                zerolinecolor="#dbe2ea",
                color="#1f2937",
            )
            figure.update_yaxes(
                gridcolor="#dbe2ea",
                linecolor="#94a3b8",
                zerolinecolor="#dbe2ea",
                color="#1f2937",
            )
        figure.update_layout(autosize=True, width=None, height=None)
        return figure

    def _show_context_menu(self, pos) -> None:
        if not self.current_html:
            return
        menu = QMenu(self)
        if self._theme_name == "light":
            menu.setStyleSheet("""
                QMenu { background: #ffffff; border: 1px solid #c9d4df; padding: 4px; border-radius: 6px; }
                QMenu::item { padding: 6px 16px; color: #1f2937; margin: 2px; border-radius: 4px; }
                QMenu::item:selected { background: #2f6fed; color: white; }
            """)
        else:
            menu.setStyleSheet("""
                QMenu { background: #1f2937; border: 1px solid #374151; padding: 4px; border-radius: 6px; }
                QMenu::item { padding: 6px 16px; color: #e5e7eb; margin: 2px; border-radius: 4px; }
                QMenu::item:selected { background: #3b82f6; color: white; }
            """)
            
        popup_action = menu.addAction("Open Plot in New Window")
        action = menu.exec(self.web_view.mapToGlobal(pos))
        if action == popup_action:
            self._open_popup()

    def _open_popup(self) -> None:
        if not hasattr(self, "_popups"):
            self._popups = []
            
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._popups.append(dialog)
        dialog.finished.connect(lambda: self._popups.remove(dialog) if dialog in self._popups else None)
        
        dialog.setWindowTitle(self.full_title)
        
        screen_geom = self.screen().availableGeometry()
        dialog.resize(screen_geom.width() // 2, screen_geom.height() // 2)
        
        view = QWebEngineView(dialog)
        settings = view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view)
        
        base_url = QUrl.fromLocalFile(str(self.preview_dir) + "/")
        view.setHtml(self.current_html, base_url)
        
        dialog.show()

    def _handle_download(self, download: QWebEngineDownloadRequest) -> None:
        suggested = download.suggestedFileName()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Downloaded File",
            suggested,
            "Images (*.png);;All Files (*)",
        )
        if path:
            directory = str(Path(path).parent)
            filename = Path(path).name
            download.setDownloadDirectory(directory)
            download.setDownloadFileName(filename)
            download.accept()
        else:
            download.cancel()
