import bpy
import os
from datetime import datetime
import xml.etree.ElementTree as ET
import math
from mathutils import Vector

def format_therm_value(value):
    """Formatuje wartość do 6 miejsc po przecinku z zerami"""
    return f"{float(value):.6f}"

def get_material_properties(material):
    conductivity = "0.04"
    emissivity = "0.90"
    
    if material and material.use_nodes:
        for node in material.node_tree.nodes:
            if node.label == "conductivity" and hasattr(node, 'outputs') and node.outputs:
                if hasattr(node.outputs[0], 'default_value'):
                    conductivity = format_therm_value(node.outputs[0].default_value)
            
            if node.label == "emissivity" and hasattr(node, 'outputs') and node.outputs:
                if hasattr(node.outputs[0], 'default_value'):
                    emissivity = format_therm_value(node.outputs[0].default_value)
    
    return conductivity, emissivity

def get_material_color(material):
    if material and hasattr(material, 'diffuse_color'):
        r = int(material.diffuse_color[0] * 255)
        g = int(material.diffuse_color[1] * 255)
        b = int(material.diffuse_color[2] * 255)
        return f"0x{r:02X}{g:02X}{b:02X}"
    return "0x808080"

def get_curve_points(curve_obj):
    """Pobiera punkty z krzywej w przestrzeni świata"""
    points = []
    world_matrix = curve_obj.matrix_world
    
    for spline in curve_obj.data.splines:
        if spline.type == 'POLY':
            for point in spline.points:
                world_point = world_matrix @ point.co.xyz
                x = round(world_point.x * 1000, 2)
                y = round(world_point.y * 1000, 2)
                points.append((x, y))
    
    return points

def get_all_therm_collections():
    """Zwraca wszystkie kolekcje THERM"""
    therm_collections = []
    for coll in bpy.data.collections:
        if coll.name.startswith('THERM_'):
            therm_collections.append(coll)
    return therm_collections

def get_all_polygons_from_mesh(obj):
    """Pobiera WSZYSTKIE polygony z obiektu siatki"""
    mesh = obj.data
    world_matrix = obj.matrix_world
    
    polygons_data = []
    
    for poly_index, polygon in enumerate(mesh.polygons):
        points = []
        
        for loop_index in polygon.loop_indices:
            loop = mesh.loops[loop_index]
            vert = mesh.vertices[loop.vertex_index]
            world_vert = world_matrix @ vert.co
            
            x = round(world_vert.x * 1000, 2)
            y = round(world_vert.y * 1000, 2)
            points.append((str(len(points)), format_therm_value(x), format_therm_value(y)))
        
        if len(points) >= 3:
            polygons_data.append({
                'points': points,
                'num_sides': len(points),
                'material_index': polygon.material_index
            })
    
    return polygons_data

class THERMExporter:
    def __init__(self):
        pass
    
    def export_to_therm(self, context):
        """Główna funkcja eksportująca do formatu THERM"""
        blend_filepath = bpy.data.filepath
        if not blend_filepath:
            return {'ERROR'}, "Zapisz plik Blender przed eksportem"
        
        blend_filename = os.path.splitext(os.path.basename(blend_filepath))[0]
        filepath = os.path.join(os.path.dirname(blend_filepath), f"{blend_filename}.thmx")
        
        if self.create_therm_file(filepath):
            return {'INFO'}, f"Utworzono plik: {filepath}"
        else:
            return {'ERROR'}, "Błąd eksportu"
    
    def get_boundary_curves_from_collections(self):
        """Pobiera krzywe z wszystkich kolekcji THERM i dopasowuje kolejność do polygonów"""
        boundary_curves = []
        
        polygons_data = []
        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        for obj in selected_objects:
            polygons_data.extend(get_all_polygons_from_mesh(obj))
        
        ufactor_curves = []
        other_curves = []
        
        for coll in get_all_therm_collections():
            for obj in coll.objects:
                if obj.type == 'CURVE':
                    points = get_curve_points(obj)
                    if len(points) >= 2:
                        matched_polygon = self.find_matching_polygon(points, polygons_data)
                        
                        if matched_polygon:
                            v1, v2 = self.get_edge_points_in_polygon_order(points, matched_polygon)
                        else:
                            v1 = (points[0][0], points[0][1])
                            v2 = (points[1][0], points[1][1])
                        
                        curve_data = {
                            'collection': coll.name,
                            'object': obj.name,
                            'v1': v1,
                            'v2': v2,
                            'length': math.sqrt((v2[0]-v1[0])**2 + (v2[1]-v1[1])**2)
                        }
                        
                        if coll.name.startswith('THERM_Ti='):
                            curve_data['type'] = 'Ti'
                            try:
                                parts = coll.name.replace('THERM_Ti=', '').split('_Rsi=')
                                curve_data['ti_temperature'] = float(parts[0])
                                curve_data['ti_rsi'] = float(parts[1])
                            except:
                                curve_data['ti_temperature'] = bpy.context.scene.therm_edge_props.ti_temperature
                                curve_data['ti_rsi'] = bpy.context.scene.therm_edge_props.ti_rsi
                                
                        elif coll.name.startswith('THERM_Te='):
                            curve_data['type'] = 'Te'
                            try:
                                parts = coll.name.replace('THERM_Te=', '').split('_Rse=')
                                curve_data['te_temperature'] = float(parts[0])
                                curve_data['te_rse'] = float(parts[1])
                            except:
                                curve_data['te_temperature'] = bpy.context.scene.therm_edge_props.te_temperature
                                curve_data['te_rse'] = bpy.context.scene.therm_edge_props.te_rse
                                
                        elif coll.name.startswith('THERM_UFactor_'):
                            curve_data['type'] = 'UFactor'
                            curve_data['ufactor_name'] = coll.name.replace('THERM_UFactor_', '')
                            ufactor_curves.append(curve_data)
                            continue
                                
                        elif coll.name == 'THERM_Adiabatic':
                            curve_data['type'] = 'Adiabatic'
                            
                        else:
                            curve_data['type'] = 'Unknown'
                        
                        other_curves.append(curve_data)
        
        for ufactor_curve in ufactor_curves:
            matching_curve = self.find_matching_curve(ufactor_curve, other_curves)
            
            if matching_curve:
                matching_curve['ufactor_name'] = ufactor_curve['ufactor_name']
            else:
                ufactor_curve['type'] = 'Adiabatic'
                other_curves.append(ufactor_curve)
        
        return other_curves

    def find_matching_curve(self, ufactor_curve, other_curves):
        """Znajduje krzywą która pasuje do krzywej U-Factor"""
        tolerance = 0.1
        
        for curve in other_curves:
            if (self.points_match(ufactor_curve['v1'], curve['v1'], tolerance) and 
                self.points_match(ufactor_curve['v2'], curve['v2'], tolerance)):
                return curve
            elif (self.points_match(ufactor_curve['v1'], curve['v2'], tolerance) and 
                  self.points_match(ufactor_curve['v2'], curve['v1'], tolerance)):
                return curve
        
        return None

    def find_matching_polygon(self, curve_points, polygons_data):
        """Znajduje polygon który pasuje do krzywej"""
        for polygon in polygons_data:
            poly_points = [(float(x), float(y)) for _, x, y in polygon['points']]
            
            curve_start = (curve_points[0][0], curve_points[0][1])
            curve_end = (curve_points[1][0], curve_points[1][1])
            
            for i in range(len(poly_points)):
                poly_point1 = poly_points[i]
                poly_point2 = poly_points[(i + 1) % len(poly_points)]
                
                if (self.points_match(curve_start, poly_point1) and self.points_match(curve_end, poly_point2)) or \
                   (self.points_match(curve_start, poly_point2) and self.points_match(curve_end, poly_point1)):
                    return polygon
        
        return None

    def points_match(self, point1, point2, tolerance=0.1):
        """Sprawdza czy dwa punkty są takie same z tolerancją"""
        return abs(point1[0] - point2[0]) < tolerance and abs(point1[1] - point2[1]) < tolerance

    def get_edge_points_in_polygon_order(self, curve_points, polygon):
        """Zwraca punkty krzywej w kolejności zgodnej z polygonem"""
        poly_points = [(float(x), float(y)) for _, x, y in polygon['points']]
        curve_start = (curve_points[0][0], curve_points[0][1])
        curve_end = (curve_points[1][0], curve_points[1][1])
        
        for i in range(len(poly_points)):
            poly_point1 = poly_points[i]
            poly_point2 = poly_points[(i + 1) % len(poly_points)]
            
            if self.points_match(curve_start, poly_point1) and self.points_match(curve_end, poly_point2):
                return (curve_start, curve_end)
            elif self.points_match(curve_start, poly_point2) and self.points_match(curve_end, poly_point1):
                return (curve_end, curve_start)
        
        return ((curve_points[0][0], curve_points[0][1]), (curve_points[1][0], curve_points[1][1]))
    
    def create_therm_file(self, filepath):
        try:
            therm_xml = ET.Element("THERM-XML")
            therm_xml.set("xmlns", "http://windows.lbl.gov")
            
            ET.SubElement(therm_xml, "ThermVersion").text = "Version 7.8.74.0"
            ET.SubElement(therm_xml, "FileVersion").text = "1"
            ET.SubElement(therm_xml, "SaveDate").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            ET.SubElement(therm_xml, "Title").text = ""
            ET.SubElement(therm_xml, "CreatedBy").text = ""
            ET.SubElement(therm_xml, "Company").text = ""
            ET.SubElement(therm_xml, "Client").text = ""
            ET.SubElement(therm_xml, "CrossSectionType").text = "Sill"
            ET.SubElement(therm_xml, "Notes").text = ""
            ET.SubElement(therm_xml, "Units").text = "SI"
            
            mesh_control = ET.SubElement(therm_xml, "MeshControl")
            mesh_control.set("MeshLevel", "8")
            mesh_control.set("ErrorCheckFlag", "1")
            mesh_control.set("ErrorLimit", "10.00")
            mesh_control.set("MaxIterations", "10")
            mesh_control.set("CMAflag", "0")
            
            materials = ET.SubElement(therm_xml, "Materials")
            selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
            
            all_materials = set()
            for obj in selected_objects:
                if obj.data.materials:
                    for mat in obj.data.materials:
                        if mat and mat.name not in ['RED', 'BLUE', 'GREY', 'GREEN']:
                            all_materials.add(mat)
            
            if not all_materials:
                default_mat = bpy.data.materials.new("DefaultMaterial")
                all_materials.add(default_mat)
            
            sorted_materials = sorted(all_materials, key=lambda x: x.name)
            
            for i, mat in enumerate(sorted_materials, 1):
                conductivity, emissivity = get_material_properties(mat)
                color = get_material_color(mat)
                
                material_elem = ET.SubElement(materials, "Material", 
                                           Name=mat.name, 
                                           Index=str(i), 
                                           Type="0", 
                                           Conductivity=conductivity, 
                                           Tir="0.00",
                                           EmissivityFront=emissivity, 
                                           EmissivityBack=emissivity, 
                                           RGBColor=color)
                
                for side, range_type, specularity in [
                    ("Front", "Visible", "Direct"), ("Front", "Visible", "Diffuse"),
                    ("Front", "Solar", "Direct"), ("Front", "Solar", "Diffuse"),
                    ("Back", "Visible", "Direct"), ("Back", "Visible", "Diffuse"),
                    ("Back", "Solar", "Direct"), ("Back", "Solar", "Diffuse")
                ]:
                    ET.SubElement(material_elem, "Property",
                                Side=side, Range=range_type, Specularity=specularity,
                                T="0.00", R="0.00")
            
            boundary_conditions = ET.SubElement(therm_xml, "BoundaryConditions")
            
            unique_conditions = set()
            boundary_curves = self.get_boundary_curves_from_collections()
            
            for curve in boundary_curves:
                if curve['type'] == 'Ti':
                    condition = f"Ti={curve.get('ti_temperature', 20.0)} Rsi={curve.get('ti_rsi', 0.13):.2f}"
                    unique_conditions.add(('Ti', condition))
                elif curve['type'] == 'Te':
                    condition = f"Te={curve.get('te_temperature', -20.0)} Rse={curve.get('te_rse', 0.04):.2f}"
                    unique_conditions.add(('Te', condition))
                elif curve['type'] == 'Adiabatic':
                    unique_conditions.add(('Adiabatic', 'Adiabatic'))
            
            ET.SubElement(boundary_conditions, "BoundaryCondition",
                         Name="Adiabatic", Type="0", H="0.00", HeatFLux="0.00",
                         Temperature="0.00", RGBColor="0x000000")
            
            for condition_type, condition_name in unique_conditions:
                if condition_type == 'Ti':
                    ti_temp = float(condition_name.split('Ti=')[1].split(' ')[0])
                    ti_rsi = float(condition_name.split('Rsi=')[1])
                    ET.SubElement(boundary_conditions, "BoundaryCondition",
                                 Name=condition_name, Type="0", 
                                 H=format_therm_value(1.0/ti_rsi if ti_rsi > 0 else 7.69),
                                 HeatFLux="0.00", Temperature=format_therm_value(ti_temp),
                                 RGBColor="0xFF0000")
                elif condition_type == 'Te':
                    te_temp = float(condition_name.split('Te=')[1].split(' ')[0])
                    te_rse = float(condition_name.split('Rse=')[1])
                    ET.SubElement(boundary_conditions, "BoundaryCondition",
                                 Name=condition_name, Type="0", 
                                 H=format_therm_value(1.0/te_rse if te_rse > 0 else 25.0),
                                 HeatFLux="0.00", Temperature=format_therm_value(te_temp),
                                 RGBColor="0x0000FF")
            
            polygons = ET.SubElement(therm_xml, "Polygons")
            polygon_id = 1
            
            for obj in selected_objects:
                polygons_data = get_all_polygons_from_mesh(obj)
                
                for poly_data in polygons_data:
                    material_name = "DefaultMaterial"
                    if obj.data.materials and poly_data['material_index'] < len(obj.data.materials):
                        material = obj.data.materials[poly_data['material_index']]
                        if material:
                            material_name = material.name
                    
                    polygon = ET.SubElement(polygons, "Polygon",
                                          ID=str(polygon_id), 
                                          Material=material_name,
                                          NSides=str(poly_data['num_sides']),
                                          Type="1", 
                                          units="mm")
                    
                    for index, x, y in poly_data['points']:
                        ET.SubElement(polygon, "Point", index=index, x=x, y=y)
                    
                    polygon_id += 1
            
            boundaries = ET.SubElement(therm_xml, "Boundaries")
            boundary_id = polygon_id
            
            for curve in boundary_curves:
                if curve['type'] in ['Ti', 'Te', 'Adiabatic']:
                    if curve['type'] == 'Ti':
                        bc_name = f"Ti={curve.get('ti_temperature', 20.0)} Rsi={curve.get('ti_rsi', 0.13):.2f}"
                    elif curve['type'] == 'Te':
                        bc_name = f"Te={curve.get('te_temperature', -20.0)} Rse={curve.get('te_rse', 0.04):.2f}"
                    else:
                        bc_name = "Adiabatic"
                    
                    ufactor_tag = curve.get('ufactor_name', '')
                    
                    bc_polygon = ET.SubElement(boundaries, "BCPolygon",
                                             ID=str(boundary_id), 
                                             BC=bc_name,
                                             units="mm", 
                                             MaterialName="",
                                             PolygonID="1",
                                             EnclosureID="0", 
                                             UFactorTag=ufactor_tag,
                                             Emissivity="0.90",
                                             MaterialSide="Front", 
                                             IlluminatedSurface="FALSE")
                    
                    ET.SubElement(bc_polygon, "Point", index="0", 
                                x=format_therm_value(curve['v1'][0]), 
                                y=format_therm_value(curve['v1'][1]))
                    ET.SubElement(bc_polygon, "Point", index="1", 
                                x=format_therm_value(curve['v2'][0]), 
                                y=format_therm_value(curve['v2'][1]))
                    
                    boundary_id += 1
            
            def indent(elem, level=0):
                i = "\n" + level * "\t"
                if len(elem):
                    if not elem.text or not elem.text.strip():
                        elem.text = i + "\t"
                    if not elem.tail or not elem.tail.strip():
                        elem.tail = i
                    for child in elem:
                        indent(child, level + 1)
                    if not elem.tail or not elem.tail.strip():
                        elem.tail = i
                else:
                    if level and (not elem.tail or not elem.tail.strip()):
                        elem.tail = i
            
            indent(therm_xml)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0"?>\n')
                tree = ET.ElementTree(therm_xml)
                tree.write(f, encoding='unicode')
            
            print(f"Wyeksportowano {polygon_id-1} polygonów i {len(boundary_curves)} warunków brzegowych")
            return True
            
        except Exception as e:
            print(f"Błąd eksportu: {e}")
            import traceback
            traceback.print_exc()
            return False