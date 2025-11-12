import bpy
import os
import xml.etree.ElementTree as ET
from datetime import datetime

class THERMUSectionExporter:
    def __init__(self):
        self.usection_data = {}
    
    def get_geometry_nodes_values(self, curve_obj):
        """Pobiera wartości z Geometry Nodes dla krzywej U-Section"""
        try:
            data = {
                'usection_name': '',
                'ti_curve': None,
                'te_curve': None, 
                'objects': [],
                'materials': {}
            }
            
            for modifier in curve_obj.modifiers:
                if modifier.type == 'NODES' and modifier.node_group:
                    # Pobierz dostępne socket-y
                    available_inputs = list(modifier.keys())
                    
                    # Pobierz USection
                    if 'Socket_2' in available_inputs:
                        data['usection_name'] = modifier['Socket_2']
                    
                    # Pobierz Ti curve
                    if 'Socket_22' in available_inputs and modifier['Socket_22']:
                        data['ti_curve'] = modifier['Socket_22']
                    elif 'Socket_8' in available_inputs and modifier['Socket_8']:
                        data['ti_curve'] = modifier['Socket_8']
                    
                    # Pobierz Te curve  
                    if 'Socket_23' in available_inputs and modifier['Socket_23']:
                        data['te_curve'] = modifier['Socket_23']
                    elif 'Socket_25' in available_inputs and modifier['Socket_25']:
                        data['te_curve'] = modifier['Socket_25']
                    
                    # Pobierz Objects (M1-M10)
                    object_sockets = ['Socket_14', 'Socket_15', 'Socket_16', 'Socket_17', 'Socket_18',
                                     'Socket_19', 'Socket_20', 'Socket_13', 'Socket_12', 'Socket_8']
                    
                    for socket_id in object_sockets:
                        if socket_id in available_inputs and modifier[socket_id]:
                            obj = modifier[socket_id]
                            if obj and obj.type == 'MESH':
                                data['objects'].append(obj)
                                
                                # Pobierz materiały
                                if obj.data.materials:
                                    for mat in obj.data.materials:
                                        if mat:
                                            conductivity, emissivity = self.get_material_properties(mat)
                                            data['materials'][mat.name] = {
                                                'conductivity': conductivity,
                                                'emissivity': emissivity
                                            }
            
            return data
            
        except Exception as e:
            print(f"Błąd pobierania Geometry Nodes: {e}")
            return data
    
    def get_material_properties(self, material):
        """Pobiera właściwości materiału"""
        conductivity = "0.04"  # domyślna wartość
        emissivity = "0.90"    # domyślna wartość
        
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.label and "conductivity" in node.label.lower():
                    if hasattr(node.outputs[0], 'default_value'):
                        conductivity = f"{node.outputs[0].default_value:.6f}"
                
                if node.label and "emissivity" in node.label.lower():
                    if hasattr(node.outputs[0], 'default_value'):
                        emissivity = f"{node.outputs[0].default_value:.6f}"
        
        return conductivity, emissivity
    
    def find_adiabatic_edges(self, mesh_objects, ti_curve, te_curve):
        """Znajduje krawędzie adiabatyczne (nieprzypisane do Ti/Te)"""
        adiabatic_edges = []
        
        # Tutaj dodaj logikę znajdowania krawędzi adiabatycznych
        # Na razie zwracamy pustą listę - trzeba dostosować do Twojej struktury
        return adiabatic_edges
    
    def export_usection_thmx(self, curve_obj, filepath):
        """Eksportuje pojedynczą sekcję U do pliku .thmx z właściwą geometrią"""
        try:
            # Pobierz dane z Geometry Nodes
            data = self.get_geometry_nodes_values(curve_obj)
            
            if not data['usection_name']:
                data['usection_name'] = curve_obj.name.replace('USection_', 'U')
                print(f"⚠️  Używam nazwy z obiektu: {data['usection_name']}")
            
            print(f"📦 Eksportowanie {data['usection_name']} do {filepath}...")
            print(f"   Obiekty: {[obj.name for obj in data['objects']]}")
            print(f"   Ti: {data['ti_curve'].name if data['ti_curve'] else 'Brak'}")
            print(f"   Te: {data['te_curve'].name if data['te_curve'] else 'Brak'}")
            
            # Utwórz strukturę XML dla THERM
            therm_xml = ET.Element("THERM-XML")
            therm_xml.set("xmlns", "http://windows.lbl.gov")
            
            # Nagłówek
            ET.SubElement(therm_xml, "ThermVersion").text = "Version 7.8.74.0"
            ET.SubElement(therm_xml, "FileVersion").text = "1"
            ET.SubElement(therm_xml, "SaveDate").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            ET.SubElement(therm_xml, "Title").text = data['usection_name']
            ET.SubElement(therm_xml, "CreatedBy").text = "Blender THERM Exporter"
            ET.SubElement(therm_xml, "Company").text = ""
            ET.SubElement(therm_xml, "Client").text = ""
            ET.SubElement(therm_xml, "CrossSectionType").text = "Sill"
            ET.SubElement(therm_xml, "Notes").text = f"Auto-generated from {curve_obj.name}"
            ET.SubElement(therm_xml, "Units").text = "SI"
            
            # Kontrola siatki
            mesh_control = ET.SubElement(therm_xml, "MeshControl")
            mesh_control.set("MeshLevel", "8")
            mesh_control.set("ErrorCheckFlag", "1")
            mesh_control.set("ErrorLimit", "10.00")
            mesh_control.set("MaxIterations", "10")
            mesh_control.set("CMAflag", "0")
            
            # Materiały
            materials_elem = ET.SubElement(therm_xml, "Materials")
            for i, (mat_name, mat_props) in enumerate(data['materials'].items(), 1):
                material_elem = ET.SubElement(materials_elem, "Material",
                                        Name=mat_name,
                                        Index=str(i),
                                        Type="0",
                                        Conductivity=mat_props['conductivity'],
                                        Tir="0.00",
                                        EmissivityFront=mat_props['emissivity'],
                                        EmissivityBack=mat_props['emissivity'],
                                        RGBColor="0x808080")
                
                # Dodaj właściwości materiału
                for side, range_type, specularity in [
                    ("Front", "Visible", "Direct"), ("Front", "Visible", "Diffuse"),
                    ("Front", "Solar", "Direct"), ("Front", "Solar", "Diffuse"),
                    ("Back", "Visible", "Direct"), ("Back", "Visible", "Diffuse"),
                    ("Back", "Solar", "Direct"), ("Back", "Solar", "Diffuse")
                ]:
                    ET.SubElement(material_elem, "Property",
                                Side=side, Range=range_type, Specularity=specularity,
                                T="0.00", R="0.00")
            
            # Jeśli brak materiałów, dodaj domyślny
            if not data['materials']:
                material_elem = ET.SubElement(materials_elem, "Material",
                                        Name="DefaultMaterial",
                                        Index="1",
                                        Type="0",
                                        Conductivity="0.04",
                                        Tir="0.00",
                                        EmissivityFront="0.90",
                                        EmissivityBack="0.90",
                                        RGBColor="0x808080")
                
                for side, range_type, specularity in [
                    ("Front", "Visible", "Direct"), ("Front", "Visible", "Diffuse"),
                    ("Front", "Solar", "Direct"), ("Front", "Solar", "Diffuse"),
                    ("Back", "Visible", "Direct"), ("Back", "Visible", "Diffuse"),
                    ("Back", "Solar", "Direct"), ("Back", "Solar", "Diffuse")
                ]:
                    ET.SubElement(material_elem, "Property",
                                Side=side, Range=range_type, Specularity=specularity,
                                T="0.00", R="0.00")
            
            # Warunki brzegowe
            boundary_conditions = ET.SubElement(therm_xml, "BoundaryConditions")
            
            # Dodaj warunki Ti i Te
            if data['ti_curve']:
                ET.SubElement(boundary_conditions, "BoundaryCondition",
                            Name="Ti", Type="0", H="7.69", HeatFLux="0.00", 
                            Temperature="20.00", RGBColor="0xFF0000")
            
            if data['te_curve']:
                ET.SubElement(boundary_conditions, "BoundaryCondition",
                            Name="Te", Type="0", H="25.00", HeatFLux="0.00",
                            Temperature="-20.00", RGBColor="0x0000FF")
            
            # Warunek adiabatyczny
            ET.SubElement(boundary_conditions, "BoundaryCondition",
                        Name="Adiabatic", Type="0", H="0.00", HeatFLux="0.00",
                        Temperature="0.00", RGBColor="0x808080")
            
            # Polygony (geometria) - EKSPORTUJ RZECZYWISTĄ GEOMETRIĘ
            polygons = ET.SubElement(therm_xml, "Polygons")
            polygon_id = 1
            
            for obj in data['objects']:
                if obj.type == 'MESH':
                    mesh_polygons = self.get_polygons_from_mesh(obj)
                    
                    for poly_data in mesh_polygons:
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
            
            # Warunki brzegowe jako krzywe
            boundaries = ET.SubElement(therm_xml, "Boundaries")
            boundary_id = polygon_id
            
            # Eksportuj krzywe Ti
            if data['ti_curve']:
                ti_points = self.get_curve_points(data['ti_curve'])
                if len(ti_points) >= 2:
                    bc_polygon = ET.SubElement(boundaries, "BCPolygon",
                                            ID=str(boundary_id), 
                                            BC="Ti",
                                            units="mm", 
                                            MaterialName="",
                                            PolygonID="1",
                                            EnclosureID="0", 
                                            UFactorTag="",
                                            Emissivity="0.90",
                                            MaterialSide="Front", 
                                            IlluminatedSurface="FALSE")
                    
                    for i, (x, y) in enumerate(ti_points[:2]):  # Tylko pierwsze 2 punkty
                        ET.SubElement(bc_polygon, "Point", index=str(i), 
                                    x=self.format_therm_value(x), 
                                    y=self.format_therm_value(y))
                    
                    boundary_id += 1
            
            # Eksportuj krzywe Te
            if data['te_curve']:
                te_points = self.get_curve_points(data['te_curve'])
                if len(te_points) >= 2:
                    bc_polygon = ET.SubElement(boundaries, "BCPolygon",
                                            ID=str(boundary_id), 
                                            BC="Te",
                                            units="mm", 
                                            MaterialName="",
                                            PolygonID="1",
                                            EnclosureID="0", 
                                            UFactorTag="",
                                            Emissivity="0.90",
                                            MaterialSide="Front", 
                                            IlluminatedSurface="FALSE")
                    
                    for i, (x, y) in enumerate(te_points[:2]):  # Tylko pierwsze 2 punkty
                        ET.SubElement(bc_polygon, "Point", index=str(i), 
                                    x=self.format_therm_value(x), 
                                    y=self.format_therm_value(y))
                    
                    boundary_id += 1
            
            # Formatuj i zapisz XML
            self.indent_xml(therm_xml)
            
            # Zapisz plik
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0"?>\n')
                tree = ET.ElementTree(therm_xml)
                tree.write(f, encoding='unicode')
            
            print(f"✅ Wyeksportowano: {filepath}")
            print(f"   Polygony: {polygon_id-1}")
            print(f"   Boundary conditions: {boundary_id - polygon_id}")
            return True
            
        except Exception as e:
            print(f"❌ Błąd eksportu {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return False



    def export_selected_usections(self, context):
        """Eksportuje TYLKO ZAZNACZONE U-Sections"""
        try:
            # Znajdź TYLKO ZAZNACZONE krzywe U-Section
            selected_usection_curves = []
            
            for obj in context.selected_objects:
                # Sprawdź czy obiekt jest krzywą U-Section
                if (obj.type == 'CURVE' and 
                    any(coll.name == "THERM_USections" for coll in obj.users_collection)):
                    selected_usection_curves.append(obj)
            
            if not selected_usection_curves:
                print("❌ Nie znaleziono ZAZNACZONYCH krzywych U-Section")
                # Możesz też sprawdzić czy zaznaczone są w kolekcji THERM_USections
                if "THERM_USections" in bpy.data.collections:
                    usection_coll = bpy.data.collections["THERM_USections"]
                    for obj in context.selected_objects:
                        if obj in usection_coll.objects and obj.type == 'CURVE':
                            selected_usection_curves.append(obj)
                
                if not selected_usection_curves:
                    print("❌ Nadal nie znaleziono ZAZNACZONYCH krzywych U-Section")
                    return []
            
            print(f"📋 Znaleziono {len(selected_usection_curves)} ZAZNACZONYCH krzywych U-Section:")
            for curve in selected_usection_curves:
                print(f"   - {curve.name}")
            
            # Ścieżka eksportu
            blend_filepath = bpy.data.filepath
            if not blend_filepath:
                print("❌ Zapisz plik Blender przed eksportem")
                return []
            
            base_dir = os.path.dirname(blend_filepath)
            base_name = os.path.splitext(os.path.basename(blend_filepath))[0]
            
            exported_files = []
            
            # Eksportuj każdą ZAZNACZONĄ sekcję U
            for curve_obj in selected_usection_curves:
                # Pobierz nazwę USection
                data = self.get_geometry_nodes_values(curve_obj)
                usection_name = data['usection_name'] or curve_obj.name.replace('USection_', 'U')
                
                # Utwórz nazwę pliku
                filename = f"{base_name}-{usection_name}.thmx"
                filepath = os.path.join(base_dir, filename)
                
                print(f"🎯 Eksportuję ZAZNACZONĄ sekcję: {usection_name} -> {filename}")
                
                # Eksportuj
                if self.export_usection_thmx(curve_obj, filepath):
                    exported_files.append(filepath)
            
            print(f"📦 Wyeksportowano {len(exported_files)} ZAZNACZONYCH plików U-Section")
            return exported_files
            
        except Exception as e:
            print(f"❌ Błąd eksportu ZAZNACZONYCH U-Sections: {e}")
            return []

    def get_polygons_from_mesh(self, obj):
        """Pobiera polygony z obiektu siatki"""
        mesh = obj.data
        world_matrix = obj.matrix_world
        
        polygons_data = []
        
        for poly_index, polygon in enumerate(mesh.polygons):
            points = []
            
            for loop_index in polygon.loop_indices:
                loop = mesh.loops[loop_index]
                vert = mesh.vertices[loop.vertex_index]
                world_vert = world_matrix @ vert.co
                
                # Konwertuj metry na milimetry i zaokrąglij
                x = round(world_vert.x * 1000, 2)
                y = round(world_vert.y * 1000, 2)
                points.append((str(len(points)), self.format_therm_value(x), self.format_therm_value(y)))
            
            if len(points) >= 3:
                polygons_data.append({
                    'points': points,
                    'num_sides': len(points),
                    'material_index': polygon.material_index
                })
        
        return polygons_data

    def get_curve_points(self, curve_obj):
        """Pobiera punkty z krzywej"""
        points = []
        world_matrix = curve_obj.matrix_world
        
        for spline in curve_obj.data.splines:
            if spline.type == 'POLY':
                for point in spline.points:
                    world_point = world_matrix @ point.co.xyz
                    x = round(world_point.x * 1000, 2)  # m to mm
                    y = round(world_point.y * 1000, 2)
                    points.append((x, y))
        
        return points

    def format_therm_value(self, value):
        """Formatuje wartość dla THERM"""
        return f"{float(value):.6f}"

    def indent_xml(self, elem, level=0):
        """Formatuje XML z wcięciami"""
        i = "\n" + level * "\t"
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "\t"
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self.indent_xml(child, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i    
    def export_all_usections(self, context):
        """Eksportuje wszystkie U-Sections"""
        try:
            # Znajdź wszystkie krzywe U-Section
            usection_curves = []
            if "THERM_USections" in bpy.data.collections:
                usection_coll = bpy.data.collections["THERM_USections"]
                usection_curves = [obj for obj in usection_coll.objects if obj.type == 'CURVE']
            
            if not usection_curves:
                print("❌ Nie znaleziono krzywych U-Section")
                return []
            
            # Ścieżka eksportu
            blend_filepath = bpy.data.filepath
            if not blend_filepath:
                print("❌ Zapisz plik Blender przed eksportem")
                return []
            
            base_dir = os.path.dirname(blend_filepath)
            base_name = os.path.splitext(os.path.basename(blend_filepath))[0]
            
            exported_files = []
            
            # Eksportuj każdą sekcję U
            for curve_obj in usection_curves:
                # Pobierz nazwę USection
                data = self.get_geometry_nodes_values(curve_obj)
                usection_name = data['usection_name'] or curve_obj.name
                
                # Utwórz nazwę pliku
                filename = f"{base_name}-{usection_name}.thmx"
                filepath = os.path.join(base_dir, filename)
                
                # Eksportuj
                if self.export_usection_thmx(curve_obj, filepath):
                    exported_files.append(filepath)
            
            print(f"📦 Wyeksportowano {len(exported_files)} plików U-Section")
            return exported_files
            
        except Exception as e:
            print(f"❌ Błąd eksportu U-Sections: {e}")
            return []
    
    def get_all_polygons_from_mesh(self, obj):
        """Pobiera WSZYSTKIE polygony z obiektu siatki - alternatywna wersja"""
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
                points.append((str(len(points)), self.format_therm_value(x), self.format_therm_value(y)))
            
            if len(points) >= 3:
                polygons_data.append({
                    'points': points,
                    'num_sides': len(points),
                    'material_index': polygon.material_index
                })
        
        return polygons_data
    
    def run_therm_calculations(self, filepaths):
        """Uruchamia obliczenia THERM dla plików"""
        try:
            from . import therm_runner
            
            runner = therm_runner.THERMRunner()
            success_count = 0
            
            for filepath in filepaths:
                print(f"🔄 Uruchamianie obliczeń dla: {os.path.basename(filepath)}")
                
                # Uruchom obliczenia
                if runner._run_therm_calculation_thmx(filepath):
                    success_count += 1
                    print(f"✅ Ukończono obliczenia: {os.path.basename(filepath)}")
                else:
                    print(f"❌ Błąd obliczeń: {os.path.basename(filepath)}")
            
            print(f"🎯 Ukończono {success_count}/{len(filepaths)} obliczeń")
            return success_count
            
        except Exception as e:
            print(f"❌ Błąd uruchamiania obliczeń: {e}")
            return 0