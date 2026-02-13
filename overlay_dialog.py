from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QDialogButtonBox, QSizePolicy, QCheckBox
)
from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsWkbTypes
from qgis.gui import QgsMessageBar

from .overlay_logic import build_intersection_memory_layer


class OverlayDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface

        self.setWindowTitle("Interseção (Overlay) - Camada temporária")
        self.setMinimumWidth(560)

        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.bar)

        # Linha 1: camada base + checkbox "selecionadas"
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Camada BASE (polígono):"))
        self.cbo_base = QComboBox()
        row1.addWidget(self.cbo_base)
        self.chk_base_selected = QCheckBox("Apenas selecionadas")
        row1.addWidget(self.chk_base_selected)
        layout.addLayout(row1)

        # Linha 2: camada overlay + checkbox "selecionadas"
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Camada SOBREPOSIÇÃO (polígono):"))
        self.cbo_overlay = QComboBox()
        row2.addWidget(self.cbo_overlay)
        self.chk_overlay_selected = QCheckBox("Apenas selecionadas")
        row2.addWidget(self.chk_overlay_selected)
        layout.addLayout(row2)

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

        if not layer_base.crs().isValid() or not layer_over.crs().isValid():
            self._msg(
                "Erro",
                "Uma das camadas está sem SRC/CRS definido. Defina o SRC da camada e tente novamente.",
                Qgis.Critical
            )
            return

        only_sel_base = self.chk_base_selected.isChecked()
        only_sel_over = self.chk_overlay_selected.isChecked()

        # Se marcou "apenas selecionadas" mas não tem seleção, avisa
        if only_sel_base and layer_base.selectedFeatureCount() == 0:
            self._msg("Aviso", "BASE: nenhuma feição selecionada.", Qgis.Warning)
            return
        if only_sel_over and layer_over.selectedFeatureCount() == 0:
            self._msg("Aviso", "SOBREPOSIÇÃO: nenhuma feição selecionada.", Qgis.Warning)
            return

        out_layer = build_intersection_memory_layer(
            layer_base,
            layer_over,
            only_selected_a=only_sel_base,
            only_selected_b=only_sel_over
        )

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
        self.bar.pushMessage(title, text, level=level)
