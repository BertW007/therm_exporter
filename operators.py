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
    THERM_OT_clean_to_boundary
    
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