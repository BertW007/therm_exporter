import bpy
import os
import xml.etree.ElementTree as ET
from mathutils import Vector

class THERMImporter:
    def __init__(self):
        pass
    
    def import_from_therm(self, filepath):
        """Importuje plik THERM (.thmx) do Blendera"""
        if not self.filepath:
            return {'ERROR'}, "Nie wybrano pliku"
        
        if not os.path.exists(self.filepath):
            return {'ERROR'}, f"Plik nie istnieje: {self.filepath}"
        
        try:
            success = self.import_therm_file(self.filepath)
            if success:
                return {'INFO'}, f"Zaimportowano plik THERM: {os.path.basename(self.filepath)}"
            else:
                return {'ERROR'}, "Błąd importu pliku THERM"
        except Exception as e:
            return {'ERROR'}, f"Błąd importu: {str(e)}"
    
    def import_therm_file(self, filepath):
        """Importuje plik THERM do Blendera"""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            collection_name = f"THERM_Import_{base_name}"
            collection = self.ensure_collection(collection_name)
            
            mesh_section = root.find(".//MeshInput")
            if mesh_section is not None:
                self.import_mesh_geometry(mesh_section, collection)
            
            boundaries_section = root.find(".//Boundaries")
            if boundaries_section is not None:
                self.import_boundaries(boundaries_section, collection)
            
            results_section = root.find(".//Results")
            if results_section is not None:
                self.import_results(results_section, collection)
            
            return True
            
        except Exception as e:
            print(f"Błąd importu THERM: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def ensure_collection(self, collection_name):
        """Tworzy lub zwraca kolekcję"""
        if collection_name in bpy.data.collections:
            return bpy.data.collections[collection_name]
        
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
        return collection
    
    def import_mesh_geometry(self, mesh_section, collection):
        """Importuje siatkę z sekcji MeshInput"""
        nodes = {}
        nodes_elem = mesh_section.find("Nodes")
        if nodes_elem is not None:
            for node_elem in nodes_elem.findall("Node"):
                index = int(node_elem.get("index"))
                x = float(node_elem.get("x")) / 1000.0
                y = float(node_elem.get("y")) / 1000.0
                nodes[index] = (x, y, 0.0)
        
        materials_elements = {}
        elements_elem = mesh_section.find("Elements")
        if elements_elem is not None:
            for elem_elem in elements_elem.findall("Element"):
                material_id = elem_elem.get("materialID")
                if material_id not in materials_elements:
                    materials_elements[material_id] = []
                
                node_indices = []
                for i in range(1, 5):
                    node_attr = f"node{i}"
                    if node_attr in elem_elem.attrib:
                        node_idx = int(elem_elem.get(node_attr))
                        if node_idx in nodes:
                            node_indices.append(node_idx)
                
                if len(node_indices) >= 3:
                    materials_elements[material_id].append(node_indices)
        
        for material_id, elements in materials_elements.items():
            if not elements:
                continue
            
            mesh_name = f"THERM_Material_{material_id}"
            mesh = bpy.data.meshes.new(mesh_name)
            
            all_verts = []
            all_faces = []
            vertex_map = {}
            
            for element_nodes in elements:
                face_verts = []
                for node_idx in element_nodes:
                    if node_idx not in vertex_map:
                        global_co = nodes[node_idx]
                        vertex_map[node_idx] = len(all_verts)
                        all_verts.append(global_co)
                    face_verts.append(vertex_map[node_idx])
                
                if len(face_verts) == 4:
                    all_faces.append(face_verts)
                elif len(face_verts) == 3:
                    all_faces.append(face_verts)
                else:
                    for i in range(1, len(face_verts)-1):
                        all_faces.append([face_verts[0], face_verts[i], face_verts[i+1]])
            
            mesh.from_pydata(all_verts, [], all_faces)
            mesh.update()
            
            obj = bpy.data.objects.new(mesh_name, mesh)
            collection.objects.link(obj)
            
            material = self.create_material_for_id(material_id)
            obj.data.materials.append(material)
    
    def create_material_for_id(self, material_id):
        """Tworzy materiał na podstawie ID"""
        material_name = f"Material_{material_id}"
        
        if material_name in bpy.data.materials:
            return bpy.data.materials[material_name]
        
        color_map = {
            "1": (0.8, 0.8, 0.8, 1.0),
            "2": (0.2, 0.2, 0.8, 1.0),
            "3": (0.8, 0.2, 0.2, 1.0),
            "4": (0.2, 0.8, 0.2, 1.0),
            "5": (0.8, 0.8, 0.2, 1.0),
        }
        
        color = color_map.get(material_id, (0.5, 0.5, 0.5, 1.0))
        
        mat = bpy.data.materials.new(material_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value = color
        
        output = nodes.new(type='ShaderNodeOutputMaterial')
        mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        return mat

    def import_boundaries(self, boundaries_section, collection):
        """Importuje warunki brzegowe jako krzywe"""
        boundary_curves = []
        
        for bc_polygon in boundaries_section.findall("BCPolygon"):
            bc_name = bc_polygon.get("BC", "Unknown")
            ufactor_tag = bc_polygon.get("UFactorTag", "")
            
            points = []
            for point_elem in bc_polygon.findall("Point"):
                x = float(point_elem.get("x")) / 1000.0
                y = float(point_elem.get("y")) / 1000.0
                points.append((x, y, 0.0))
            
            if len(points) >= 2:
                curve_name = f"BC_{bc_name}"
                if ufactor_tag:
                    curve_name += f"_UFactor_{ufactor_tag}"
                
                curve_data = bpy.data.curves.new(curve_name, type='CURVE')
                curve_data.dimensions = '3D'
                
                spline = curve_data.splines.new('POLY')
                spline.points.add(len(points) - 1)
                
                for i, point in enumerate(points):
                    spline.points[i].co = (*point, 1.0)
                
                curve_data.bevel_mode = 'ROUND'
                curve_data.bevel_depth = 0.0
                
                curve_obj = bpy.data.objects.new(curve_name, curve_data)
                collection.objects.link(curve_obj)
                boundary_curves.append((curve_obj, bc_name))
        
        self.assign_boundary_materials(boundary_curves)
    
    def assign_boundary_materials(self, boundary_curves):
        """Przypisuje materiały do krzywych warunków brzegowych"""
        bc_materials = {
            "Ti": self.create_boundary_material("Ti_Boundary", (1.0, 0.0, 0.0, 1.0)),
            "Te": self.create_boundary_material("Te_Boundary", (0.0, 0.0, 1.0, 1.0)),
            "Adiabatic": self.create_boundary_material("Adiabatic_Boundary", (0.5, 0.5, 0.5, 1.0)),
        }
        
        for curve_obj, bc_name in boundary_curves:
            if "Ti" in bc_name:
                material = bc_materials["Ti"]
            elif "Te" in bc_name:
                material = bc_materials["Te"]
            else:
                material = bc_materials["Adiabatic"]
            
            curve_obj.data.materials.append(material)
    
    def create_boundary_material(self, name, color):
        """Tworzy materiał dla warunku brzegowego"""
        if name in bpy.data.materials:
            return bpy.data.materials[name]
        
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Emission Strength'].default_value = 0.1
        bsdf.inputs['Emission Color'].default_value = color
        
        output = nodes.new(type='ShaderNodeOutputMaterial')
        mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        return mat

    def import_results(self, results_section, collection):
        """Importuje wyniki obliczeń"""
        ufactors_elem = results_section.find(".//U-factors")
        if ufactors_elem is not None:
            self.import_ufactor_results(ufactors_elem, collection)
        
        node_results = results_section.findall(".//NodeResults")
        if node_results:
            self.import_temperature_results(node_results, collection)
    
    def import_ufactor_results(self, ufactors_elem, collection):
        """Importuje wyniki U-factor jako tekst"""
        tag_elem = ufactors_elem.find("Tag")
        tag = tag_elem.text if tag_elem is not None else "Unknown"
        
        projections = []
        for proj_elem in ufactors_elem.findall("Projection"):
            length_type_elem = proj_elem.find("Length-type")
            length_elem = proj_elem.find("Length")
            ufactor_elem = proj_elem.find("U-factor")
            
            if length_type_elem is not None and length_elem is not None and ufactor_elem is not None:
                projections.append({
                    'type': length_type_elem.text,
                    'length': float(length_elem.get('value')),
                    'length_units': length_elem.get('units', 'mm'),
                    'ufactor': float(ufactor_elem.get('value')),
                    'ufactor_units': ufactor_elem.get('units', 'W/m2-K')
                })
        
        if projections:
            text_content = f"U-Factor Results - {tag}\n\n"
            for proj in projections:
                text_content += f"{proj['type']}:\n"
                text_content += f"  Length: {proj['length']} {proj['length_units']}\n"
                text_content += f"  U-factor: {proj['ufactor']:.6f} {proj['ufactor_units']}\n\n"
            
            text_data = bpy.data.curves.new(type="FONT", name="UFactor_Results")
            text_data.body = text_content
            text_obj = bpy.data.objects.new("UFactor_Results", text_data)
            text_obj.location = (2, 0, 0)
            text_obj.scale = (0.1, 0.1, 0.1)
            collection.objects.link(text_obj)
    
    def import_temperature_results(self, node_results, collection):
        """Importuje wyniki temperatury"""
        print(f"Znaleziono {len(node_results)} wyników temperatury")