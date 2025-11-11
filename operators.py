import bpy
import os
import subprocess
from . import geometry_utils, boundary_conditions, therm_export, therm_import, therm_runner

# Operatory dla sprawdzania i naprawy geometrii
class THERM_OT_check_normals(bpy.types.Operator):
    """Sprawdza czy wszystkie faces mają normalne skierowane w górę"""
    bl_idname = "therm.check_normals"
    bl_label = "Sprawdź normalne"
    bl_description = "Sprawdza czy wszystkie faces mają normalne skierowane w górę"
    
    def execute(self, context):
        result = geometry_utils.check_and_fix_normals()
        if result == {'FINISHED'}:
            self.report({'INFO'}, "Wszystkie normalne są skierowane w górę")
        return result

class THERM_OT_clean_to_boundary(bpy.types.Operator):
    """Czyści geometrię do samej obwiedni"""
    bl_idname = "therm.clean_to_boundary"
    bl_label = "Wyczyść do obwiedni"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            if bpy.context.mode != 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')
            
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.region_to_loop()
            bpy.ops.mesh.select_all(action='INVERT')
            bpy.ops.mesh.delete(type='EDGE_FACE')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.edge_face_add()
            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, "Wyczyścino geometrię do obwiedni")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Błąd: {str(e)}")
            return {'CANCELLED'}

class THERM_OT_check_vertices(bpy.types.Operator):
    """Sprawdza czy wierzchołki mają współrzędne z dokładnością do 0.1m"""
    bl_idname = "therm.check_vertices"
    bl_label = "Sprawdź wierzchołki"
    bl_description = "Sprawdza czy wierzchołki mają współrzędne z dokładnością do 0.1m"
    
    def execute(self, context):
        result = geometry_utils.check_and_round_vertices()
        if result == {'FINISHED'}:
            self.report({'INFO'}, "Wszystkie wierzchołki są wielokrotnościami 0.1m")
        return result

class THERM_OT_round_vertices(bpy.types.Operator):
    """Zaokrągla wierzchołki zaznaczonych obiektów"""
    bl_idname = "therm.round_vertices"
    bl_label = "Zaokrągl wierzchołki"
    bl_description = "Zaokrągla współrzędne wierzchołków zaznaczonych obiektów do określonej precyzji"
    
    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'WARNING'}, "Zaznacz przynajmniej jeden obiekt siatki")
            return {'CANCELLED'}
        
        precision = float(context.scene.therm_props.round_precision)
        vertices_modified = geometry_utils.round_vertices_to_precision(precision)
        
        self.report({'INFO'}, f"Zaokrąglono {vertices_modified} wierzchołków z precyzją {precision}m")
        return {'FINISHED'}

class THERM_OT_force_round_vertices(bpy.types.Operator):
    """Wymusza zaokrąglenie wszystkich wierzchołków zaznaczonych obiektów"""
    bl_idname = "therm.force_round_vertices"
    bl_label = "Wymuś zaokrąglenie wierzchołków"
    bl_description = "Wymusza zaokrąglenie wszystkich wierzchołków bez sprawdzania"
    
    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'WARNING'}, "Zaznacz przynajmniej jeden obiekt siatki")
            return {'CANCELLED'}
        
        precision = float(context.scene.therm_props.round_precision)
        vertices_modified = geometry_utils.round_vertices_to_precision(precision)
        
        self.report({'INFO'}, f"Zaokrąglono {vertices_modified} wierzchołków z precyzją {precision}m")
        return {'FINISHED'}

# Operatory potwierdzające
class THERM_OT_recalc_normals_confirm(bpy.types.Operator):
    """Operator potwierdzający odwrócenie normalnych"""
    bl_idname = "therm.recalc_normals_confirm"
    bl_label = "Odwróć normalne"
    bl_description = "Odwróć normalne faces do góry"
    
    def execute(self, context):
        geometry_utils.recalc_normals_upward()
        self.report({'INFO'}, "Odwrócono normalne do góry")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class THERM_OT_round_vertices_confirm(bpy.types.Operator):
    """Operator potwierdzający zaokrąglenie wierzchołków"""
    bl_idname = "therm.round_vertices_confirm"
    bl_label = "Zaokrągl wierzchołki"
    bl_description = "Zaokrągl wierzchołki do dokładności 0.1m"
    
    def execute(self, context):
        precision = 0.1
        vertices_modified = geometry_utils.round_vertices_to_precision(precision)
        self.report({'INFO'}, f"Zaokrąglono {vertices_modified} wierzchołków do {precision}m")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

# Operatory do odwracania faces skierowanych w dół
class THERM_OT_flip_downward_faces(bpy.types.Operator):
    """Odwraca tylko faces skierowane w dół"""
    bl_idname = "therm.flip_downward_faces"
    bl_label = "Odwróć faces skierowane w dół"
    bl_description = "Automatycznie znajduje i odwraca tylko faces które są skierowane w dół"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        threshold = context.scene.therm_props.flip_threshold
        faces_flipped = geometry_utils.flip_downward_faces_with_threshold(threshold)
        self.report({'INFO'}, f"Odwrócono {faces_flipped} faces skierowanych w dół (próg: {threshold})")
        return {'FINISHED'}

class THERM_OT_quick_flip_downward_faces(bpy.types.Operator):
    """Szybkie odwracanie faces skierowanych w dół"""
    bl_idname = "therm.quick_flip_downward_faces"
    bl_label = "Szybko odwróć faces w dół"
    bl_description = "Szybkie odwracanie faces skierowanych w dół z domyślnym progiem"
    
    def execute(self, context):
        faces_flipped = geometry_utils.flip_downward_faces_only()
        self.report({'INFO'}, f"Odwrócono {faces_flipped} faces skierowanych w dół")
        return {'FINISHED'}

# Operatory dla tworzenia krzywych ręcznie
class THERM_OT_create_ti_edges(bpy.types.Operator):
    """Tworzy krzywe Ti ze wszystkich zaznaczonych krawędzi"""
    bl_idname = "therm.create_ti_edges"
    bl_label = "Utwórz krzywe Ti"
    
    def execute(self, context):
        curve_objs = boundary_conditions.create_continuous_curve_from_edges('Ti')
        if curve_objs:
            coll_name = boundary_conditions.get_therm_collection_name('Ti')
            self.report({'INFO'}, f"Utworzono {len(curve_objs)} krzywych Ti w kolekcji '{coll_name}'")
        else:
            self.report({'WARNING'}, "Nie zaznaczono żadnych krawędzi")
        return {'FINISHED'}

class THERM_OT_create_te_edges(bpy.types.Operator):
    """Tworzy krzywe Te ze wszystkich zaznaczonych krawędzi"""
    bl_idname = "therm.create_te_edges"
    bl_label = "Utwórz krzywe Te"
    
    def execute(self, context):
        curve_objs = boundary_conditions.create_continuous_curve_from_edges('Te')
        if curve_objs:
            coll_name = boundary_conditions.get_therm_collection_name('Te')
            self.report({'INFO'}, f"Utworzono {len(curve_objs)} krzywych Te w kolekcji '{coll_name}'")
        else:
            self.report({'WARNING'}, "Nie zaznaczono żadnych krawędzi")
        return {'FINISHED'}

class THERM_OT_create_adiabatic_edges(bpy.types.Operator):
    """Tworzy krzywe Adiabatic ze wszystkich zaznaczonych krawędzi"""
    bl_idname = "therm.create_adiabatic_edges"
    bl_label = "Utwórz krzywe Adiabatic"
    
    def execute(self, context):
        curve_objs = boundary_conditions.create_continuous_curve_from_edges('Adiabatic')
        if curve_objs:
            coll_name = boundary_conditions.get_therm_collection_name('Adiabatic')
            self.report({'INFO'}, f"Utworzono {len(curve_objs)} krzywych Adiabatic w kolekcji '{coll_name}'")
        else:
            self.report({'WARNING'}, "Nie zaznaczono żadnych krawędzi")
        return {'FINISHED'}

class THERM_OT_create_ufactor_edges(bpy.types.Operator):
    """Tworzy krzywe U-Factor ze wszystkich zaznaczonych krawędzi"""
    bl_idname = "therm.create_ufactor_edges"
    bl_label = "Utwórz krzywe U-Factor"
    
    def execute(self, context):
        ufactor_name = context.scene.therm_edge_props.ufactor_name
        if not ufactor_name:
            self.report({'WARNING'}, "Ustaw nazwę U-Factor")
            return {'CANCELLED'}
        
        curve_objs = boundary_conditions.create_continuous_curve_from_edges('UFactor', ufactor_name)
        if curve_objs:
            coll_name = boundary_conditions.get_therm_collection_name('UFactor', ufactor_name)
            self.report({'INFO'}, f"Utworzono {len(curve_objs)} krzywych U-Factor w kolekcji '{coll_name}'")
        else:
            self.report({'WARNING'}, "Nie zaznaczono żadnych krawędzi")
        return {'FINISHED'}

# Operatory dla automatycznego tworzenia krzywych
class THERM_OT_create_adiabatic_auto(bpy.types.Operator):
    """Automatycznie tworzy krzywe Adiabatic na zewnętrznych krawędziach z kierunkiem lewoskrętnym"""
    bl_idname = "therm.create_adiabatic_auto"
    bl_label = "Auto Adiabatic (zewnętrzne krawędzie)"
    bl_description = "Automatycznie znajduje zewnętrzne krawędzie i tworzy krzywe Adiabatic z kierunkiem lewoskrętnym"
    
    def execute(self, context):
        created_curves = boundary_conditions.create_auto_curves_on_external_edges('Adiabatic')
        
        if created_curves:
            self.report({'INFO'}, f"Utworzono {len(created_curves)} krzywych Adiabatic na zewnętrznych krawędziach")
        else:
            self.report({'WARNING'}, "Nie znaleziono zewnętrznych krawędzi")
        
        return {'FINISHED'}

class THERM_OT_create_ti_auto(bpy.types.Operator):
    """Automatycznie tworzy krzywe Ti na zewnętrznych krawędziach z kierunkiem lewoskrętnym"""
    bl_idname = "therm.create_ti_auto"
    bl_label = "Auto Ti (zewnętrzne krawędzie)"
    bl_description = "Automatycznie znajduje zewnętrzne krawędzie i tworzy krzywe Ti z kierunkiem lewoskrętnym"
    
    def execute(self, context):
        created_curves = boundary_conditions.create_auto_curves_on_external_edges('Ti')
        
        if created_curves:
            self.report({'INFO'}, f"Utworzono {len(created_curves)} krzywych Ti na zewnętrznych krawędziach")
        else:
            self.report({'WARNING'}, "Nie znaleziono zewnętrznych krawędzi")
        
        return {'FINISHED'}

class THERM_OT_create_te_auto(bpy.types.Operator):
    """Automatycznie tworzy krzywe Te na zewnętrznych krawędziach z kierunkiem lewoskrętnym"""
    bl_idname = "therm.create_te_auto"
    bl_label = "Auto Te (zewnętrzne krawędzie)"
    bl_description = "Automatycznie znajduje zewnętrzne krawędzie i tworzy krzywe Te z kierunkiem lewoskrętnym"
    
    def execute(self, context):
        created_curves = boundary_conditions.create_auto_curves_on_external_edges('Te')
        
        if created_curves:
            self.report({'INFO'}, f"Utworzono {len(created_curves)} krzywych Te na zewnętrznych krawędziach")
        else:
            self.report({'WARNING'}, "Nie znaleziono zewnętrznych krawędzi")
        
        return {'FINISHED'}

class THERM_OT_create_ufactor_auto(bpy.types.Operator):
    """Automatycznie tworzy krzywe U-Factor na zewnętrznych krawędziach z kierunkiem lewoskrętnym"""
    bl_idname = "therm.create_ufactor_auto"
    bl_label = "Auto U-Factor (zewnętrzne krawędzie)"
    bl_description = "Automatycznie znajduje zewnętrzne krawędzie i tworzy krzywe U-Factor z kierunkiem lewoskrętnym"
    
    def execute(self, context):
        ufactor_name = bpy.context.scene.therm_edge_props.ufactor_name
        if not ufactor_name:
            self.report({'WARNING'}, "Ustaw nazwę U-Factor")
            return {'CANCELLED'}
        
        created_curves = boundary_conditions.create_auto_curves_on_external_edges('UFactor', ufactor_name)
        
        if created_curves:
            self.report({'INFO'}, f"Utworzono {len(created_curves)} krzywych U-Factor na zewnętrznych krawędziach")
        else:
            self.report({'WARNING'}, "Nie znaleziono zewnętrznych krawędzi")
        
        return {'FINISHED'}

# Operatory dla uruchamiania THERM
class THERM_OT_run_therm_calculation_thmx(bpy.types.Operator):
    """Uruchom obliczenia THERM z plikiem .thmx"""
    bl_idname = "therm.run_therm_calculation_thmx"
    bl_label = "Uruchom obliczenia THERM (.thmx)"
    bl_description = "Uruchom obliczenia w THERM z plikiem .thmx (wymaga THERM7.exe)"
    
    def execute(self, context):
        runner = therm_runner.THERMRunner()
        result_type, message = runner.run_calculation_thmx(context)
        self.report(result_type, message)
        return {'FINISHED'}

class THERM_OT_run_therm_calculation_thm(bpy.types.Operator):
    """Uruchom obliczenia THERM z plikiem .thm"""
    bl_idname = "therm.run_therm_calculation_thm"
    bl_label = "Uruchom obliczenia THERM (.thm)"
    bl_description = "Uruchom obliczenia w THERM z plikiem .thm (wymaga THERM7.exe)"
    
    def execute(self, context):
        runner = therm_runner.THERMRunner()
        result_type, message = runner.run_calculation_thm(context)
        self.report(result_type, message)
        return {'FINISHED'}

class THERM_OT_open_therm_folder(bpy.types.Operator):
    """Otwórz folder z plikami THERM"""
    bl_idname = "therm.open_therm_folder"
    bl_label = "Otwórz folder THERM"
    bl_description = "Otwórz folder z plikami THERM"
    
    def execute(self, context):
        runner = therm_runner.THERMRunner()
        result_type, message = runner.open_therm_folder(context)
        self.report(result_type, message)
        return {'FINISHED'}

# Operator importu THERM
class THERM_OT_import_from_therm(bpy.types.Operator):
    """Importuj plik THERM (.thmx) do Blendera"""
    bl_idname = "therm.import_from_therm"
    bl_label = "Importuj z THERM"
    bl_description = "Importuj plik THERM (.thmx) do Blendera"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "Nie wybrano pliku")
            return {'CANCELLED'}
        
        if not os.path.exists(self.filepath):
            self.report({'ERROR'}, f"Plik nie istnieje: {self.filepath}")
            return {'CANCELLED'}
        
        try:
            importer = therm_import.THERMImporter()
            success = importer.import_therm_file(self.filepath)
            if success:
                self.report({'INFO'}, f"Zaimportowano plik THERM: {os.path.basename(self.filepath)}")
            else:
                self.report({'ERROR'}, "Błąd importu pliku THERM")
        except Exception as e:
            self.report({'ERROR'}, f"Błąd importu: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# Operator eksportu THERM
class THERM_OT_export_to_therm(bpy.types.Operator):
    """Eksportuj do pliku THERM"""
    bl_idname = "therm.export_to_therm"
    bl_label = "Eksportuj do THERM"
    
    def execute(self, context):
        exporter = therm_export.THERMExporter()
        result_type, message = exporter.export_to_therm(context)
        
        if result_type == {'INFO'} and context.scene.therm_props.open_export_folder:
            self.open_export_folder()
        
        self.report(result_type, message)
        return {'FINISHED'}
    
    def open_export_folder(self):
        """Otwiera folder z wyeksportowanym plikiem"""
        blend_filepath = bpy.data.filepath
        if not blend_filepath:
            return
        
        folder_path = os.path.dirname(blend_filepath)
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            print(f"Nie można otworzyć folderu: {e}")


# W pliku operators.py, dodaj te klasy operatorów:

class THERM_OT_create_usection_base(bpy.types.Operator):
    """Klasa bazowa dla tworzenia sekcji U"""

    
    socket_map = {
        'u1': 'Socket_25',
        'usection': 'Socket_2',
        'y': 'Socket_24', 
        'u-value': 'Socket_26',
        'r01': 'Socket_28',
        'r02': 'Socket_29',
        'r03': 'Socket_30',
        'r04': 'Socket_31',
        'r05': 'Socket_32',
        'r06': 'Socket_33',
        'r07': 'Socket_34',
        'r08': 'Socket_35',
        'r09': 'Socket_36',
        'r10': 'Socket_37',
        'ti': 'Socket_22',
        'te': 'Socket_23',
        'm01': 'Socket_8',
        'm02': 'Socket_14',
        'm03': 'Socket_15',
        'm04': 'Socket_16',
        'm05': 'Socket_17',
        'm06': 'Socket_18',
        'm07': 'Socket_19',
        'm08': 'Socket_20',
        'm09': 'Socket_13',
        'm10': 'Socket_12',
    }
    
    def find_ti_curves_from_selected(self):
        """Znajduje krzywe Ti tylko z zaznaczonych obiektów/kolekcji"""
        ti_curves = []
        selected_objects = bpy.context.selected_objects
        
        # Sprawdź wszystkie zaznaczone krzywe w kolekcjach Ti
        for obj in selected_objects:
            if obj.type == 'CURVE':
                # Sprawdź czy obiekt jest w kolekcji Ti
                for coll in obj.users_collection:
                    if coll.name.startswith('THERM_Ti='):
                        ti_curves.append(obj)
                        break
        
        return ti_curves
    
    def ensure_usection_collection(self):
        """Tworzy kolekcję THERM_USections jeśli nie istnieje"""
        collection_name = "THERM_USections"
        if collection_name not in bpy.data.collections:
            coll = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(coll)
        return bpy.data.collections[collection_name]
    
    def check_usection_exists(self, usection_name):
        """Sprawdza czy krzywa USection już istnieje"""
        target_name = f"USection_{usection_name}"
        return target_name in bpy.data.objects
    
    def create_usection_geometry_nodes(self, curve_obj, usection_name):
        """Dodaje geometry nodes do krzywej U-Section i ustawia wartości"""
        try:
            # Usuń istniejące modyfikatory geometry nodes
            for mod in curve_obj.modifiers:
                if mod.type == 'NODES':
                    curve_obj.modifiers.remove(mod)
            
            node_group_name = "THERM U-Section"
            if node_group_name not in bpy.data.node_groups:
                self.create_usection_node_group(node_group_name)
            
            node_group = bpy.data.node_groups[node_group_name]
            modifier = curve_obj.modifiers.new(name=f"THERM_U_{usection_name}", type='NODES')
            modifier.node_group = node_group
            
            # Ustaw wartości w geometry nodes
            success = self.set_geometry_nodes_values(curve_obj, usection_name, modifier)
            
            return success, "Success"
            
        except Exception as e:
            print(f"Błąd dodawania geometry nodes: {e}")
            return False, str(e)
    
    def create_usection_node_group(self, node_group_name):
        """Tworzy grupę geometry nodes dla U-Section jeśli nie istnieje"""
        if node_group_name in bpy.data.node_groups:
            return bpy.data.node_groups[node_group_name]
        
        node_group = bpy.data.node_groups.new(node_group_name, 'GeometryNodeTree')
        
        # Dodaj inputy
        group_input = node_group.nodes.new('NodeGroupInput')
        group_input.location = (-400, 0)
        
        # Dodaj outputy  
        group_output = node_group.nodes.new('NodeGroupOutput')
        group_output.location = (400, 0)
        
        # Zdefiniuj socket-y
        node_group.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        node_group.interface.new_socket('Ti', in_out='INPUT', socket_type='NodeSocketGeometry')
        node_group.interface.new_socket('Te', in_out='INPUT', socket_type='NodeSocketGeometry')
        node_group.interface.new_socket('Object', in_out='INPUT', socket_type='NodeSocketGeometry')
        node_group.interface.new_socket('USection', in_out='INPUT', socket_type='NodeSocketString')
        node_group.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        
        return node_group
    
    def set_geometry_nodes_values(self, curve_obj, usection_name, modifier):
        """Ustawia wartości w geometry nodes - POPRAWIONE I UJEDNOLICONE"""
        try:
            # Znajdź krzywe Ti i Te
            ti_curves = self.find_all_ti_curves()
            te_curves = self.find_all_te_curves()
            
            # Znajdź obiekty siatki (geometrię)
            mesh_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
            
            print(f"Ustawianie Geometry Nodes dla {curve_obj.name}:")
            
            available_inputs = list(modifier.keys())
            print(f"  Dostępne socket-y: {sorted(available_inputs)}")
            
            # Używaj mapowania socketów
            socket_map = self.socket_map
            
            results = {}
            
            # Ustaw podstawowe wartości
            if 'usection' in socket_map and socket_map['usection'] in available_inputs:
                modifier[socket_map['usection']] = usection_name
                print(f"  ✅ Ustawiono {socket_map['usection']} (USection) = {usection_name}")
                results['usection'] = True
            
            # Ustaw Ti
            if 'ti' in socket_map and socket_map['ti'] in available_inputs and ti_curves:
                modifier[socket_map['ti']] = ti_curves[0]
                print(f"  ✅ Ustawiono {socket_map['ti']} (Ti) = {ti_curves[0].name}")
                results['ti'] = True
            
            # Ustaw Te  
            if 'te' in socket_map and socket_map['te'] in available_inputs and te_curves:
                modifier[socket_map['te']] = te_curves[0]
                print(f"  ✅ Ustawiono {socket_map['te']} (Te) = {te_curves[0].name}")
                results['te'] = True
            
            # Ustaw obiekty i wartości conductivity
            objects_set = 0
            conductivity_values_set = 0
            
            # Mapowanie socketów obiektów M01-M10
            object_keys = ['m01', 'm02', 'm03', 'm04', 'm05', 'm06', 'm07', 'm08', 'm09', 'm10']
            conductivity_keys = ['r01', 'r02', 'r03', 'r04', 'r05', 'r06', 'r07', 'r08', 'r09', 'r10']
            
            for i, (obj_key, cond_key) in enumerate(zip(object_keys, conductivity_keys)):
                if (obj_key in socket_map and socket_map[obj_key] in available_inputs and 
                    i < len(mesh_objects)):
                    
                    # Ustaw obiekt
                    modifier[socket_map[obj_key]] = mesh_objects[i]
                    print(f"  ✅ Ustawiono {socket_map[obj_key]} ({obj_key.upper()}) = {mesh_objects[i].name}")
                    objects_set += 1
                    
                    # Ustaw wartość conductivity
                    if cond_key in socket_map and socket_map[cond_key] in available_inputs:
                        conductivity = self.get_material_conductivity(mesh_objects[i])
                        try:
                            modifier[socket_map[cond_key]] = conductivity
                            print(f"  ✅ Ustawiono {socket_map[cond_key]} ({cond_key.upper()}) = {conductivity} W/mK")
                            conductivity_values_set += 1
                        except Exception as e:
                            print(f"  ❌ Błąd ustawiania {socket_map[cond_key]}: {e}")
            
            print(f"  ✅ Ustawiono {objects_set} obiektów i {conductivity_values_set} wartości conductivity")
            return True
                            
        except Exception as e:
            print(f"Błąd ustawiania geometry nodes: {e}")
            import traceback
            traceback.print_exc()
            return False




    def find_conductivity_sockets(self, available_inputs):
        """Znajduje właściwe sockety dla wartości conductivity - POPRAWIONE"""
        conductivity_sockets = []
        
        # Używamy mapowania z socket_map dla R01-R10
        r_sockets = []
        for i in range(1, 11):
            r_key = f'r{i:02d}'
            if r_key in self.socket_map and self.socket_map[r_key] in available_inputs:
                r_sockets.append(self.socket_map[r_key])
        
        # Posortuj sockety R01-R10
        r_sockets.sort()
        
        return r_sockets
        
    def find_r_sockets(self, available_inputs):
        """Znajduje socket-y R01-R10 w dostępnych inputach"""
        r_sockets = []
        
        # Szukaj socketów o nazwach związanych z R/conductivity
        r_keywords = ['r', 'conductivity', 'lambda', 'thermal']
        
        for socket_id in available_inputs:
            socket_lower = socket_id.lower()
            
            # Szukaj socketów R01, R02, etc.
            if socket_lower.startswith('socket_'):
                # Sprawdź czy to może być socket R (pomijamy już znane socket-y)
                if any(keyword in socket_lower for keyword in r_keywords):
                    r_sockets.append(socket_id)
        
        # Jeśli nie znaleziono po nazwach, spróbuj znaleźć wolne socket-y float
        if not r_sockets:
            # Socket-y które mogą być dla wartości R (float)
            possible_r_sockets = ['Socket_3', 'Socket_4', 'Socket_5', 'Socket_6', 'Socket_7',
                                'Socket_9', 'Socket_10', 'Socket_11', 'Socket_24', 'Socket_25']
            
            for socket_id in possible_r_sockets:
                if socket_id in available_inputs and socket_id not in r_sockets:
                    r_sockets.append(socket_id)
        
        # Ogranicz do 10 socketów (R01-R10)
        return r_sockets[:10]

    def get_material_conductivity(self, mesh_object):
        """Pobiera wartość conductivity z materiału obiektu - POPRAWIONA WERSJA"""
        try:
            if not mesh_object.data.materials:
                print(f"    ❌ Obiekt {mesh_object.name} nie ma materiałów")
                return 0.04  # Wartość domyślna
            
            # Weź pierwszy materiał
            material = mesh_object.data.materials[0]
            if not material:
                return 0.04
            
            print(f"    🔍 Szukam conductivity w materiale: {material.name}")
            
            # METODA 1: Sprawdź CUSTOM PROPERTIES (najpierw)
            if 'conductivity' in material:
                conductivity = material['conductivity']
                print(f"    ✅ Znaleziono conductivity w custom properties: {conductivity}")
                return conductivity
            if 'thermal_conductivity' in material:
                conductivity = material['thermal_conductivity']
                print(f"    ✅ Znaleziono thermal_conductivity w custom properties: {conductivity}")
                return conductivity
            if 'lambda' in material:
                conductivity = material['lambda']
                print(f"    ✅ Znaleziono lambda w custom properties: {conductivity}")
                return conductivity
            
            # METODA 2: Sprawdź NODE'y MATERIALU (główna metoda)
            if material.use_nodes:
                print(f"    🔍 Przeszukuję node'y materiału...")
                
                for node in material.node_tree.nodes:
                    node_name = node.name
                    node_label = getattr(node, 'label', '') or ''
                    
                    print(f"    🔍 Node: {node_name}, Label: '{node_label}'")
                    
                    # SPRAWDŹ CZY NODE MA LABEL "conductivity"
                    if node_label and 'conductivity' in node_label.lower():
                        print(f"    ✅ Znaleziono node z label 'conductivity': {node_name}")
                        
                        # Sprawdź wartość w outputach node'a
                        if hasattr(node, 'outputs') and node.outputs:
                            for output in node.outputs:
                                if hasattr(output, 'default_value'):
                                    conductivity = output.default_value
                                    print(f"    ✅ Pobrano conductivity z output {output.name}: {conductivity}")
                                    return conductivity
                        
                        # Jeśli nie ma outputów, sprawdź czy to node Value
                        if hasattr(node, 'inputs') and node.inputs and hasattr(node.inputs[0], 'default_value'):
                            conductivity = node.inputs[0].default_value
                            print(f"    ✅ Pobrano conductivity z node Value: {conductivity}")
                            return conductivity
                    
                    # SPRAWDŹ CZY NODE MA NAME "conductivity"
                    if 'conductivity' in node_name.lower():
                        print(f"    ✅ Znaleziono node z name 'conductivity': {node_name}")
                        
                        if hasattr(node, 'outputs') and node.outputs:
                            for output in node.outputs:
                                if hasattr(output, 'default_value'):
                                    conductivity = output.default_value
                                    print(f"    ✅ Pobrano conductivity z output: {conductivity}")
                                    return conductivity
                        
                        if hasattr(node, 'inputs') and node.inputs and hasattr(node.inputs[0], 'default_value'):
                            conductivity = node.inputs[0].default_value
                            print(f"    ✅ Pobrano conductivity z node inputs: {conductivity}")
                            return conductivity
                    
                    # SPRAWDŹ SPECJALNIE DLA NODE'ÓW VALUE
                    if node.bl_idname == 'ShaderNodeValue':
                        node_value = getattr(node, 'outputs', [])
                        if node_value and hasattr(node_value[0], 'default_value'):
                            conductivity = node_value[0].default_value
                            # Sprawdź czy wartość jest realistyczna (nie 0.0)
                            if conductivity > 0.001:
                                print(f"    ✅ Pobrano conductivity z ShaderNodeValue: {conductivity}")
                                return conductivity
            
            # METODA 3: Sprawdź po nazwie materiału (fallback)
            material_name_lower = material.name.lower()
            print(f"    🔍 Sprawdzam nazwę materiału: {material_name_lower}")
            
            material_conductivity_map = {
                'beton': 1.7, 'concrete': 1.7, 'cement': 1.7,
                'cegła': 0.8, 'brick': 0.8, 'ceramika': 0.8,
                'drewno': 0.15, 'wood': 0.15, 'timber': 0.15,
                'szkło': 1.0, 'glass': 1.0,
                'stal': 50.0, 'steel': 50.0, 'metal': 50.0,
                'aluminium': 200.0, 'aluminum': 200.0,
                'izolacja': 0.04, 'insulation': 0.04, 'wełna': 0.04, 'wool': 0.04,
                'styropian': 0.035, 'eps': 0.035, 'xps': 0.035,
                'l0_80': 0.80, 'l0_04': 0.04, 'l0_15': 0.15, 'l0_035': 0.035,
                'l0_113': 0.113, 'l0_113_rama': 0.113  # Dodaj specyficzne nazwy z Twoich materiałów
            }
            
            for material_keyword, conductivity_value in material_conductivity_map.items():
                if material_keyword in material_name_lower:
                    print(f"    ✅ Znaleziono conductivity po nazwie '{material_keyword}': {conductivity_value}")
                    return conductivity_value
            
            print(f"    ⚠️  Nie znaleziono conductivity, używam wartości domyślnej 0.04 W/mK")
            return 0.04  # Wartość domyślna dla izolacji
                
        except Exception as e:
            print(f"    ❌ Błąd pobierania conductivity: {e}")
            import traceback
            traceback.print_exc()
            return 0.04  # Wartość domyślna






    def find_conductivity_in_material(self, material):
        """Znajduje wartość conductivity w materiale"""
        
        # METODA 1: Sprawdź właściwości materiału
        if hasattr(material, 'thermal_conductivity'):
            return material.thermal_conductivity
        
        # METODA 2: Sprawdź custom properties
        if 'conductivity' in material:
            return material['conductivity']
        if 'thermal_conductivity' in material:
            return material['thermal_conductivity'] 
        if 'lambda' in material:
            return material['lambda']
        
        # METODA 3: Sprawdź w node'ach materiału
        if material.use_nodes:
            for node in material.node_tree.nodes:
                # Sprawdź czy node ma conductivity
                if hasattr(node, 'inputs'):
                    for input in node.inputs:
                        if input and hasattr(input, 'default_value'):
                            # Sprawdź nazwę inputa
                            if input.name.lower() in ['conductivity', 'thermal conductivity', 'lambda']:
                                return input.default_value
                
                # Sprawdź nazwę i label node'a
                node_name_lower = node.name.lower()
                node_label_lower = node.label.lower() if node.label else ""
                
                if any(keyword in node_name_lower for keyword in ['conductivity', 'thermal', 'lambda']):
                    if hasattr(node, 'outputs') and node.outputs:
                        # Spróbuj pobrać wartość z pierwszego outputa
                        try:
                            return node.outputs[0].default_value
                        except:
                            pass
        
        # METODA 4: Sprawdź po nazwie materiału (heurystyka)
        material_name_lower = material.name.lower()
        
        # Mapowanie nazw materiałów na typowe wartości conductivity
        material_conductivity_map = {
            'beton': 1.7, 'concrete': 1.7, 'cement': 1.7,
            'cegła': 0.8, 'brick': 0.8, 'ceramika': 0.8,
            'drewno': 0.15, 'wood': 0.15, 'timber': 0.15,
            'szkło': 1.0, 'glass': 1.0,
            'stal': 50.0, 'steel': 50.0, 'metal': 50.0,
            'aluminium': 200.0, 'aluminum': 200.0,
            'izolacja': 0.04, 'insulation': 0.04, 'wełna': 0.04, 'wool': 0.04,
            'styropian': 0.035, 'eps': 0.035, 'xps': 0.035
        }
        
        for material_keyword, conductivity_value in material_conductivity_map.items():
            if material_keyword in material_name_lower:
                return conductivity_value
        
        return None
        
    def find_all_ti_curves(self):
        """Znajduje wszystkie krzywe Ti w scenie"""
        ti_curves = []
        for coll in bpy.data.collections:
            if coll.name.startswith('THERM_Ti='):
                for obj in coll.objects:
                    if obj.type == 'CURVE':
                        ti_curves.append(obj)
        return ti_curves
    
    def find_all_te_curves(self):
        """Znajduje wszystkie krzywe Te w scenie"""
        te_curves = []
        for coll in bpy.data.collections:
            if coll.name.startswith('THERM_Te='):
                for obj in coll.objects:
                    if obj.type == 'CURVE':
                        te_curves.append(obj)
        return te_curves
    
    def create_usection(self, usection_name):
        """Główna funkcja tworząca sekcję U tylko z zaznaczonych obiektów"""
        try:
            target_name = f"USection_{usection_name}"
            
            # Sprawdź czy krzywa już istnieje
            if self.check_usection_exists(usection_name):
                self.report({'WARNING'}, f"Krzywa {target_name} już istnieje!")
                return {'CANCELLED'}
            
            # Znajdź krzywe Ti tylko z zaznaczonych obiektów
            ti_curves = self.find_ti_curves_from_selected()
            if not ti_curves:
                self.report({'WARNING'}, "Nie znaleziono zaznaczonych krzywych Ti")
                return {'CANCELLED'}
            
            print(f"Znaleziono {len(ti_curves)} zaznaczonych krzywych Ti")
            
            # Używamy tylko pierwszej zaznaczonej krzywej Ti
            ti_curve = ti_curves[0]
            
            print(f"Kopiowanie krzywej: {ti_curve.name} -> {target_name}")
            
            # Sprawdź ponownie czy krzywa już nie powstała (dla bezpieczeństwa)
            if self.check_usection_exists(usection_name):
                self.report({'WARNING'}, f"Krzywa {target_name} już istnieje! (ponowne sprawdzenie)")
                return {'CANCELLED'}
            
            # Utwórz kolekcję
            usection_coll = self.ensure_usection_collection()
            
            # Skopiuj krzywą
            new_curve = ti_curve.copy()
            new_curve.data = ti_curve.data.copy()
            new_curve.name = target_name
            new_curve.data.name = target_name
            
            # Dodaj do kolekcji
            usection_coll.objects.link(new_curve)
            
            # Odśwież scenę
            bpy.context.view_layer.update()
            
            # Sprawdź czy krzywa została poprawnie utworzona
            if new_curve.name not in bpy.data.objects:
                self.report({'ERROR'}, f"Błąd: Krzywa {target_name} nie została utworzona")
                return {'CANCELLED'}
            
            print(f"✅ Krzywa {target_name} została utworzona")
            
            # Dodaj geometry nodes
            success, message = self.create_usection_geometry_nodes(new_curve, usection_name)
            if success:
                print(f"✅ Geometry Nodes dodane do {target_name}")
                self.report({'INFO'}, f"Utworzono krzywą {target_name} z Geometry Nodes")
            else:
                print(f"❌ Błąd Geometry Nodes: {message}")
                self.report({'WARNING'}, f"Utworzono krzywą {target_name} ale błąd Geometry Nodes: {message}")
            
            # Odznacz wszystko i zaznacz nową krzywą
            bpy.ops.object.select_all(action='DESELECT')
            new_curve.select_set(True)
            bpy.context.view_layer.objects.active = new_curve
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Błąd tworzenia U{usection_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

class THERM_OT_create_usection_1(THERM_OT_create_usection_base):
    """Tworzy sekcję U1 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_1"
    bl_label = "Utwórz U1"
    
    def execute(self, context):
        return self.create_usection("U1")

class THERM_OT_create_usection_2(THERM_OT_create_usection_base):
    """Tworzy sekcję U2 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_2"
    bl_label = "Utwórz U2"
    
    def execute(self, context):
        return self.create_usection("U2")

class THERM_OT_create_usection_3(THERM_OT_create_usection_base):
    """Tworzy sekcję U3 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_3"
    bl_label = "Utwórz U3"
    
    def execute(self, context):
        return self.create_usection("U3")

class THERM_OT_create_usection_4(THERM_OT_create_usection_base):
    """Tworzy sekcję U4 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_4"
    bl_label = "Utwórz U4"
    
    def execute(self, context):
        return self.create_usection("U4")

class THERM_OT_create_usection_5(THERM_OT_create_usection_base):
    """Tworzy sekcję U5 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_5"
    bl_label = "Utwórz U5"
    
    def execute(self, context):
        return self.create_usection("U5")

class THERM_OT_create_usection_6(THERM_OT_create_usection_base):
    """Tworzy sekcję U6 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_6"
    bl_label = "Utwórz U6"
    
    def execute(self, context):
        return self.create_usection("U6")

class THERM_OT_create_usection_7(THERM_OT_create_usection_base):
    """Tworzy sekcję U7 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_7"
    bl_label = "Utwórz U7"
    
    def execute(self, context):
        return self.create_usection("U7")

class THERM_OT_create_usection_8(THERM_OT_create_usection_base):
    """Tworzy sekcję U8 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_8"
    bl_label = "Utwórz U8"
    
    def execute(self, context):
        return self.create_usection("U8")

class THERM_OT_create_usection_9(THERM_OT_create_usection_base):
    """Tworzy sekcję U9 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_9"
    bl_label = "Utwórz U9"
    
    def execute(self, context):
        return self.create_usection("U9")

class THERM_OT_create_usection_10(THERM_OT_create_usection_base):
    """Tworzy sekcję U10 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_10"
    bl_label = "Utwórz U10"
    
    def execute(self, context):
        return self.create_usection("U10")

class THERM_OT_create_usection_11(THERM_OT_create_usection_base):
    """Tworzy sekcję U11 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_11"
    bl_label = "Utwórz U11"
    
    def execute(self, context):
        return self.create_usection("U11")

class THERM_OT_create_usection_12(THERM_OT_create_usection_base):
    """Tworzy sekcję U12 z zaznaczonych krzywych Ti"""
    bl_idname = "therm.create_usection_12"
    bl_label = "Utwórz U12"
    
    def execute(self, context):
        return self.create_usection("U12")

# Możesz dodać tę funkcję tymczasowo do sprawdzenia sytuacji
class THERM_OT_debug_usections(bpy.types.Operator):
    """Debugowanie sekcji U"""
    bl_idname = "therm.debug_usections"
    bl_label = "Debug USections"
    
    def execute(self, context):
        print("=== DEBUG USECTIONS ===")
        
        # Sprawdź wszystkie krzywe
        all_curves = [obj for obj in bpy.data.objects if obj.type == 'CURVE']
        print(f"Wszystkie krzywe ({len(all_curves)}):")
        for curve in all_curves:
            print(f"  - {curve.name} (w kolekcjach: {[coll.name for coll in curve.users_collection]})")
        
        # Sprawdź kolekcje THERM_USections
        if "THERM_USections" in bpy.data.collections:
            usection_coll = bpy.data.collections["THERM_USections"]
            print(f"Kolekcja THERM_USections ({len(usection_coll.objects)} obiektów):")
            for obj in usection_coll.objects:
                print(f"  - {obj.name}")
        else:
            print("Kolekcja THERM_USections nie istnieje")
        
        # Sprawdź czy istnieją USection_*
        usection_objects = [obj for obj in bpy.data.objects if obj.name.startswith('USection_')]
        print(f"Obiekty USection_* ({len(usection_objects)}):")
        for obj in usection_objects:
            print(f"  - {obj.name}")
        
        print("=== KONIEC DEBUG ===")
        return {'FINISHED'}

class THERM_OT_debug_sockets(bpy.types.Operator):
    """Debugowanie socketów Geometry Nodes"""
    bl_idname = "therm.debug_sockets"
    bl_label = "Debug Sockets"
    
    def execute(self, context):
        print("=== DEBUG SOCKETS ===")
        
        # Sprawdź zaznaczone obiekty z Geometry Nodes
        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            if obj.type == 'CURVE':
                for modifier in obj.modifiers:
                    if modifier.type == 'NODES' and modifier.node_group:
                        print(f"Obiekt: {obj.name}")
                        print(f"Grupa: {modifier.node_group.name}")
                        print("Socket-y INPUT:")
                        
                        # Wejścia grupy - POPRAWIONE
                        for item in modifier.node_group.interface.items_tree:
                            if hasattr(item, 'in_out') and item.in_out == 'INPUT':
                                print(f"  - {item.name} (typ: {item.socket_type})")
                        
                        # Socket-y w modyfikatorze
                        available_inputs = list(modifier.keys())
                        print(f"  Dostępne w modyfikatorze: {sorted(available_inputs)}")
                        
                        # Sprawdź panele
                        print("  Panele:")
                        for item in modifier.node_group.interface.items_tree:
                            if hasattr(item, 'panel') and item.panel:
                                print(f"    Panel: {item.panel.name}")
                                # Sprawdź elementy w panelu
                                for panel_item in modifier.node_group.interface.items_tree:
                                    if hasattr(panel_item, 'parent') and panel_item.parent == item.panel:
                                        print(f"      - {panel_item.name} (typ: {panel_item.socket_type})")
                        print("---")
        
        print("=== KONIEC DEBUG SOCKETS ===")
        return {'FINISHED'}
# Lista wszystkich klas operatorów do rejestracji
classes = (
    THERM_OT_check_normals,
    THERM_OT_check_vertices,
    THERM_OT_round_vertices,
    THERM_OT_force_round_vertices,
    THERM_OT_recalc_normals_confirm,
    THERM_OT_round_vertices_confirm,
    THERM_OT_flip_downward_faces,
    THERM_OT_quick_flip_downward_faces,
    THERM_OT_create_ti_edges,
    THERM_OT_create_te_edges,
    THERM_OT_create_adiabatic_edges,
    THERM_OT_create_adiabatic_auto,
    THERM_OT_create_ti_auto,
    THERM_OT_create_te_auto,
    THERM_OT_create_ufactor_auto,
    THERM_OT_create_ufactor_edges,
    THERM_OT_export_to_therm,
    THERM_OT_run_therm_calculation_thmx,
    THERM_OT_run_therm_calculation_thm,
    THERM_OT_open_therm_folder,
    THERM_OT_import_from_therm,
    THERM_OT_clean_to_boundary,
    THERM_OT_create_usection_1,
    THERM_OT_create_usection_2,
    THERM_OT_create_usection_3,
    THERM_OT_create_usection_4,
    THERM_OT_create_usection_5,
    THERM_OT_create_usection_6,
    THERM_OT_create_usection_7,
    THERM_OT_create_usection_8,
    THERM_OT_create_usection_9,
    THERM_OT_create_usection_10,
    THERM_OT_create_usection_11,
    THERM_OT_create_usection_12,
    THERM_OT_debug_usections,  # Dodaj tę klasę tymczasowo
    THERM_OT_debug_sockets
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Błąd rejestracji {cls}: {e}")

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Błąd wyrejestrowania {cls}: {e}")