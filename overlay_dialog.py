from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QDialogButtonBox, QSizePolicy
)
from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsWkbTypes
from qgis.gui import QgsMessageBar

from .overlay_logic import build_intersection_memory_layer


class OverlayDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface

        self.setWindowTitle("Interseção (Overlay) - Camada temporária")
        self.setMinimumWidth(520)

        # Message bar dentro do dialog (Cookbook)
        # :contentReference[oaicite:10]{index=10}
        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        # Layout principal
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.bar)

        # Linha 1: camada base
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Camada BASE (polígono):"))
        self.cbo_base = QComboBox()
        row1.addWidget(self.cbo_base)
        layout.addLayout(row1)

        # Linha 2: camada overlay
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Camada SOBREPOSIÇÃO (polígono):"))
        self.cbo_overlay = QComboBox()
        row2.addWidget(self.cbo_overlay)
        layout.addLayout(row2)

        # Botão executar + Fechar
        self.btn_run = QPushButton("Executar")
        self.btn_run.clicked.connect(self.on_run)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)

        row_buttons = QHBoxLayout()
        row_buttons.addWidget(self.btn_run)
        row_buttons.addStretch(1)
        row_buttons.addWidget(buttons)
        layout.addLayout(row_buttons)

        self.setLayout(layout)

    def refresh_layers(self):
        """Recarrega a lista de camadas poligonais do projeto."""
        self.cbo_base.clear()
        self.cbo_overlay.clear()

        polygon_layers = self._get_polygon_layers()
        if len(polygon_layers) == 0:
            self._msg("Aviso", "Nenhuma camada poligonal encontrada no projeto.", Qgis.Warning)
            return

        for lyr in polygon_layers:
            self.cbo_base.addItem(lyr.name(), lyr.id())
            self.cbo_overlay.addItem(lyr.name(), lyr.id())

        if len(polygon_layers) == 1:
            self._msg("Aviso", "Carregue pelo menos 2 camadas poligonais para fazer a interseção.", Qgis.Warning)

    def on_run(self):
        base_id = self.cbo_base.currentData()
        over_id = self.cbo_overlay.currentData()

        if not base_id or not over_id:
            self._msg("Erro", "Selecione as duas camadas.", Qgis.Critical)
            return

        if base_id == over_id:
            self._msg("Erro", "Selecione camadas diferentes.", Qgis.Critical)
            return

        layer_base = QgsProject.instance().mapLayer(base_id)
        layer_over = QgsProject.instance().mapLayer(over_id)

        if not layer_base or not layer_over:
            self._msg("Erro", "Não foi possível obter as camadas selecionadas.", Qgis.Critical)
            return

        out_layer = build_intersection_memory_layer(layer_base, layer_over)

        if out_layer is None:
            self._msg("Erro", "Falha ao gerar a camada de interseção.", Qgis.Critical)
            return

        QgsProject.instance().addMapLayer(out_layer)

        self._msg(
            "Sucesso",
            f"Camada criada: {out_layer.name()} | Feições: {out_layer.featureCount()}",
            Qgis.Success
        )

    def _get_polygon_layers(self):
        layers = []
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                if lyr.geometryType() == QgsWkbTypes.GeometryType.PolygonGeometry:
                    layers.append(lyr)
        layers.sort(key=lambda l: l.name().lower())
        return layers

    def _msg(self, title, text, level):
        # Message bar (Cookbook mostra pushMessage e níveis Qgis.*)
        self.bar.pushMessage(title, text, level=level)
