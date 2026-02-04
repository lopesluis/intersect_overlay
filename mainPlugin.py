import os

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication

from .overlay_dialog import OverlayDialog


class IntersecaoOverlayPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dlg = None
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        # 1) tenta ícone na raiz (icon.png)
        icon_path_root = os.path.join(self.plugin_dir, "icon.png")

        # 2) fallback: ícone em subpasta (icons/icon.png)
        icon_path_icons = os.path.join(self.plugin_dir, "icons", "icon.png")

        if os.path.exists(icon_path_root):
            icon = QIcon(icon_path_root)
        elif os.path.exists(icon_path_icons):
            icon = QIcon(icon_path_icons)
        else:
            # fallback final: ícone padrão do QGIS
            icon = QgsApplication.getThemeIcon("/mActionIntersection.svg")

        self.action = QAction(
            icon,
            "Interseção (Overlay) - Camada temporária",
            self.iface.mainWindow()
        )
        self.action.setObjectName("intersectOverlayAction")
        self.action.setStatusTip("Gera a interseção entre duas camadas poligonais e calcula área e perímetro.")
        self.action.triggered.connect(self.run)

        self.iface.addPluginToMenu("&Interseção Overlay", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&Interseção Overlay", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

        if self.dlg is not None:
            try:
                self.dlg.close()
            except Exception:
                pass
            self.dlg = None

    def run(self):
        # recria o dialog sempre (pra refletir mudanças)
        if self.dlg is not None:
            try:
                self.dlg.close()
            except Exception:
                pass
            self.dlg = None

        self.dlg = OverlayDialog(self.iface)
        self.dlg.refresh_layers()
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()
