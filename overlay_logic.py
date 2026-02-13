import math

from qgis.PyQt.QtCore import QMetaType
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsWkbTypes,
    QgsFeature,
    QgsField,
    QgsSpatialIndex,
    QgsDistanceArea,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsGeometry,
    QgsCoordinateReferenceSystem,
)


def build_intersection_memory_layer(layer_a, layer_b, only_selected_a=False, only_selected_b=False):
    """
    Interseção (memory) entre duas camadas poligonais.
    Campos:
      - area_m2, area_ha, perim_m
      - perc_over: % de sobreposição da geometria de interseção em relação à área da feição BASE (layer_a)

    Regras:
      - Suporta CRS diferentes (transforma B -> CRS de A para interseção)
      - Mede sempre em EPSG:4326 (WGS84) com elipsóide, garantindo consistência global
      - Pode limitar a análise às feições selecionadas em A e/ou B
    """
    if not _is_polygon_layer(layer_a) or not _is_polygon_layer(layer_b):
        return None

    if not layer_a.crs().isValid() or not layer_b.crs().isValid():
        return None

    crs_auth = layer_a.crs().authid()
    out_layer = QgsVectorLayer(f"Polygon?crs={crs_auth}", "intersecao_temp", "memory")
    if not out_layer.isValid():
        return None

    pr = out_layer.dataProvider()
    pr.addAttributes([
        QgsField("area_m2", QMetaType.Type.Double),
        QgsField("area_ha", QMetaType.Type.Double),
        QgsField("perim_m", QMetaType.Type.Double),
        QgsField("perc_over", QMetaType.Type.Double),
    ])
    out_layer.updateFields()

    d = QgsDistanceArea()
    d.setEllipsoid("WGS84")

    crs_geo = QgsCoordinateReferenceSystem("EPSG:4326")
    ctx = QgsProject.instance()

    # transformações
    same_crs_ab = layer_a.crs() == layer_b.crs()
    xform_b_to_a = None
    if not same_crs_ab:
        xform_b_to_a = QgsCoordinateTransform(layer_b.crs(), layer_a.crs(), ctx)

    need_a_to_geo = layer_a.crs() != crs_geo
    xform_a_to_geo = None
    if need_a_to_geo:
        xform_a_to_geo = QgsCoordinateTransform(layer_a.crs(), crs_geo, ctx)

    # iteradores considerando seleção
    if only_selected_a:
        feats_a = layer_a.getSelectedFeatures()
    else:
        feats_a = layer_a.getFeatures()

    if only_selected_b:
        feats_b_for_index = layer_b.getSelectedFeatures()
    else:
        feats_b_for_index = layer_b.getFeatures()

    # índice espacial (no CRS de A)
    transformed_b = {}  # fid -> QgsGeometry no CRS de A (quando CRS diferente)
    if same_crs_ab:
        index_b = QgsSpatialIndex(feats_b_for_index)
    else:
        index_b = QgsSpatialIndex()
        for fb in feats_b_for_index:
            gb = fb.geometry()
            if not gb or gb.isEmpty():
                continue

            gb_t = QgsGeometry(gb)
            try:
                gb_t.transform(xform_b_to_a)
            except Exception:
                continue

            transformed_b[fb.id()] = gb_t
            fb_idx = QgsFeature(fb)
            fb_idx.setGeometry(gb_t)
            index_b.addFeature(fb_idx)

    # Para buscar apenas candidatos (principalmente útil quando NÃO estamos usando seleção em B)
    selected_b_ids = None
    if only_selected_b:
        selected_b_ids = set(layer_b.selectedFeatureIds())

    out_feats = []

    for fa in feats_a:
        ga = fa.geometry()
        if not ga or ga.isEmpty():
            continue

        # área da BASE para % (medida sempre em EPSG:4326)
        ga_for_measure = QgsGeometry(ga)
        if need_a_to_geo:
            try:
                ga_for_measure.transform(xform_a_to_geo)
            except Exception:
                continue

        area_base_m2 = float(d.measureArea(ga_for_measure))
        if area_base_m2 <= 0.0 or math.isnan(area_base_m2):
            continue

        candidate_ids = index_b.intersects(ga.boundingBox())
        if not candidate_ids:
            continue

        # se estamos usando "apenas selecionadas" em B, filtra candidatos pelos IDs selecionados
        if selected_b_ids is not None:
            candidate_ids = [fid for fid in candidate_ids if fid in selected_b_ids]
            if not candidate_ids:
                continue

        req = QgsFeatureRequest().setFilterFids(list(candidate_ids))

        for fb in layer_b.getFeatures(req):
            gb = fb.geometry()
            if not gb or gb.isEmpty():
                continue

            if same_crs_ab:
                gb_use = gb
            else:
                gb_use = transformed_b.get(fb.id())
                if gb_use is None:
                    gb_use = QgsGeometry(gb)
                    try:
                        gb_use.transform(xform_b_to_a)
                    except Exception:
                        continue

            if not ga.intersects(gb_use):
                continue

            inter = ga.intersection(gb_use)
            if not inter or inter.isEmpty():
                continue

            inter_for_measure = QgsGeometry(inter)
            if need_a_to_geo:
                try:
                    inter_for_measure.transform(xform_a_to_geo)
                except Exception:
                    continue

            perim_m = float(d.measurePerimeter(inter_for_measure))
            area_m2 = float(d.measureArea(inter_for_measure))

            if math.isnan(perim_m) or math.isnan(area_m2) or area_m2 <= 0.0:
                continue

            area_ha = area_m2 / 10000.0
            perc_over = (area_m2 / area_base_m2) * 100.0

            f_out = QgsFeature(out_layer.fields())
            f_out.setGeometry(inter)  # geometria no CRS da camada A
            f_out.setAttributes([area_m2, area_ha, perim_m, perc_over])
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
