from qgis.PyQt.QtCore import QMetaType
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsWkbTypes,
    QgsFeature,
    QgsField,
    QgsSpatialIndex,
    QgsDistanceArea
)


def build_intersection_memory_layer(layer_a, layer_b):
    """
    Gera uma camada temporária (memory) com a interseção entre duas camadas poligonais.
    Campos: area_m2, area_ha, perim_m
    """
    if not _is_polygon_layer(layer_a) or not _is_polygon_layer(layer_b):
        return None

    # Camada temporária "memory" (Cookbook: memory provider via QgsVectorLayer(..., "memory"))
    # :contentReference[oaicite:16]{index=16}
    crs_auth = layer_a.crs().authid()
    out_layer = QgsVectorLayer(f"Polygon?crs={crs_auth}", "intersecao_temp", "memory")
    if not out_layer.isValid():
        return None

    pr = out_layer.dataProvider()

    # Campos (Cookbook: addAttributes + updateFields)
    # :contentReference[oaicite:17]{index=17}
    pr.addAttributes([
        QgsField("area_m2", QMetaType.Type.Double),
        QgsField("area_ha", QMetaType.Type.Double),
        QgsField("perim_m", QMetaType.Type.Double),
    ])
    out_layer.updateFields()

    # Medidas (Cookbook: QgsDistanceArea, setEllipsoid, measurePerimeter/measureArea)
    # :contentReference[oaicite:18]{index=18}
    d = QgsDistanceArea()
    d.setEllipsoid("WGS84")

    # Índice espacial da camada B (Cookbook: bulk loading)
    # :contentReference[oaicite:19]{index=19}
    index_b = QgsSpatialIndex(layer_b.getFeatures())

    out_feats = []

    # Itera features da camada A e usa bbox + spatial index para candidatos em B
    for fa in layer_a.getFeatures():
        ga = fa.geometry()
        if not ga or ga.isEmpty():
            continue

        candidate_ids = set(index_b.intersects(ga.boundingBox()))
        if not candidate_ids:
            continue

        # Para recuperar só os candidatos, fazemos um loop em B e filtramos por id.
        # (Mantém o exemplo alinhado ao Cookbook, que mostra o index retornando IDs)
        for fb in layer_b.getFeatures():
            if fb.id() not in candidate_ids:
                continue

            gb = fb.geometry()
            if not gb or gb.isEmpty():
                continue

            # Predicado/operador GEOS (Cookbook cita intersects() como predicate)
            # :contentReference[oaicite:20]{index=20}
            if not ga.intersects(gb):
                continue

            inter = ga.intersection(gb)
            if not inter or inter.isEmpty():
                continue

            perim_m = float(d.measurePerimeter(inter))
            area_m2 = float(d.measureArea(inter))
            area_ha = area_m2 / 10000.0

            f_out = QgsFeature(out_layer.fields())
            f_out.setGeometry(inter)
            f_out.setAttributes([area_m2, area_ha, perim_m])
            out_feats.append(f_out)

    pr.addFeatures(out_feats)
    out_layer.updateExtents()

    return out_layer


def _is_polygon_layer(layer):
    return (
        isinstance(layer, QgsVectorLayer)
        and layer.isValid()
        and layer.geometryType() == QgsWkbTypes.GeometryType.PolygonGeometry
    )
