import bpy
import os

def get_all_therm_collections():
    """Zwraca wszystkie kolekcje THERM - bezpieczna wersja"""
    try:
        therm_collections = []
        # Sprawdzamy czy bpy.data.collections jest dostępne
        if hasattr(bpy.data, 'collections'):
            for coll in bpy.data.collections:
                if coll.name.startswith('THERM_'):
                    therm_collections.append(coll)
        return therm_collections
    except Exception as e:
        print(f"Warning: Could not get THERM collections: {e}")
        return []

class THERM_PT_panel(bpy.types.Panel):
    """Panel THERM Exporter"""
    bl_label = "THERM Exporter"
    bl_idname = "THERM_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    
    def draw(self, context):
        layout = self.layout
        
        # Sekcja sprawdzania geometrii
        box = layout.box()
        box.label(text="Sprawdzanie geometrii:", icon='MESH_DATA')
        
        # row = box.row()
        # row.operator("therm.check_normals", text="Sprawdź normalne", icon='NORMALS_FACE')
        # row.operator("therm.check_vertices", text="Sprawdź wierzchołki", icon='SNAP_VERTEX')
        
        # Odwracanie faces skierowanych w dół
        col = box.column()
        col.label(text="Odwracanie faces skierowanych w dół:")
        col.prop(context.scene.therm_props, "flip_threshold", text="Próg czułości")
        
        row = col.row(align=True)
        row.operator("therm.quick_flip_downward_faces", text="Szybko odwróć", icon='MOD_SOLIDIFY')
        row.operator("therm.flip_downward_faces", text="Z ustawieniami", icon='MODIFIER')
        
        # # Zaokrąglanie wierzchołków
        # col = box.column()
        # col.label(text="Zaokrąglanie wierzchołków:")
        # row = col.row()
        # row.prop(context.scene.therm_props, "round_precision", text="Precyzja")
        
        # row = col.row(align=True)
        # row.operator("therm.round_vertices", text="Zaokrągl po sprawdzeniu", icon='SNAP_VERTEX')
        # row.operator("therm.force_round_vertices", text="Wymuś zaokrąglenie", icon='MOD_SOLIDIFY')
        
        # czyszczenie geometrii do warunków brzegowych
        col = box.column()
        col.label(text="Czyszczenie geometrii do warunków brzegowych:")
        row = col.row()
        row.operator("therm.clean_to_boundary", text="Wyczyść do obwiedni", icon='BRUSH_DATA')

        layout.separator()
        
        # Informacje
        box = layout.box()
        box.label(text="Tworzenie krzywych warunków brzegowych")
        box.label(text="Zaznacz krawędzie w trybie EDIT MODE")
        box.label(text="Możesz zaznaczyć wiele krawędzi z różnych obiektów")
        
        # Ustawienia warunków brzegowych
        box = layout.box()
        box.label(text="Ustawienia warunków brzegowych:", icon='SETTINGS')
        
        col = box.column()
        col.prop(context.scene.therm_edge_props, "flip_direction", text="Odwróć kierunek krawędzi")
        col.label(text="(Zaznacz dla kierunku lewostronnego w THERM)", icon='INFO')
        
        col.separator()
        
        # Warunki wewnętrzne (Ti)
        row = col.row()
        row.label(text="", icon='COLORSET_01_VEC')
        row.label(text="Warunki wewnętrzne (Ti):")
        col.prop(context.scene.therm_edge_props, "ti_temperature", text="Temperatura [°C]")
        col.prop(context.scene.therm_edge_props, "ti_rsi", text="Rsi [m²K/W]")

        row = col.row()
        row.operator("therm.create_ti_auto", text="Auto Ti", icon='AUTO')
        row.operator("therm.create_ti_edges", text="Z krawędzi", icon='CURVE_DATA')

        col.separator()

        # Warunki zewnętrzne (Te)
        row = col.row()
        row.label(text="", icon='COLORSET_04_VEC')
        row.label(text="Warunki zewnętrzne (Te):")
        col.prop(context.scene.therm_edge_props, "te_temperature", text="Temperatura [°C]")
        col.prop(context.scene.therm_edge_props, "te_rse", text="Rse [m²K/W]")

        row = col.row()
        row.operator("therm.create_te_auto", text="Auto Te", icon='AUTO')
        row.operator("therm.create_te_edges", text="Z krawędzi", icon='CURVE_DATA')

        col.separator()

        # Adiabatic
        row = col.row()
        row.label(text="", icon='COLORSET_13_VEC')
        row.label(text="Adiabatic:")

        row = col.row()
        row.operator("therm.create_adiabatic_auto", text="Auto Adiabatic", icon='AUTO')
        row.operator("therm.create_adiabatic_edges", text="Z krawędzi", icon='CURVE_DATA')

        col.separator()

        # U-Factor
        row = col.row()
        row.label(text="", icon='COLORSET_03_VEC')
        row.label(text="U-Factor:")
        col.prop(context.scene.therm_edge_props, "ufactor_name", text="Nazwa U-Factor")

        row = col.row()
        row.operator("therm.create_ufactor_auto", text="Auto U-Factor", icon='AUTO')
        row.operator("therm.create_ufactor_edges", text="Z krawędzi", icon='CURVE_DATA')

        col.label(text="U-Factor tworzy krzywe jak pozostałe typy", icon='INFO')
        
        # Lista istniejących kolekcji THERM - POPRAWIONE
        box = layout.box()
        box.label(text="Istniejące kolekcje THERM:")
        
        therm_collections = get_all_therm_collections()
        
        if therm_collections:
            # Bezpieczne pobranie aktywnej kolekcji
            active_coll_name = getattr(context.scene, 'active_therm_collection', "")
            
            # Sprawdź czy aktywna kolekcja nadal istnieje
            active_coll = None
            if active_coll_name:
                active_coll = next((coll for coll in therm_collections if coll.name == active_coll_name), None)
            
            # Jeśli nie ma aktywnej kolekcji, ustaw pierwszą
            if not active_coll:
                # Używamy operatora do ustawienia aktywnej kolekcji zamiast bezpośredniego przypisania
                row = box.row()
                row.label(text="Wybierz kolekcję:", icon='INFO')
                
                # Przyciski dla każdej kolekcji
                for coll in therm_collections:
                    row = box.row()
                    op = row.operator("therm.set_active_collection", text=f"{coll.name} ({len(coll.objects)})", icon='CURVE_DATA')
                    op.collection_name = coll.name
                    
                    # Przyciski akcji dla kolekcji
                    row_actions = box.row(align=True)
                    op_select = row_actions.operator("therm.select_collection_objects", text="Zaznacz", icon='RESTRICT_SELECT_OFF')
                    op_select.collection_name = coll.name
                    op_delete = row_actions.operator("therm.delete_collection", text="Usuń", icon='TRASH')
                    op_delete.collection_name = coll.name
            else:
                # Menu rozwijane z kolekcjami
                row = box.row()
                row.prop(context.scene, "active_therm_collection", text="")
                
                # Informacje o zaznaczonej kolekcji
                active_coll_name = context.scene.active_therm_collection
                active_coll = next((coll for coll in therm_collections if coll.name == active_coll_name), None)
                
                if active_coll:
                    col = box.column()
                    col.label(text=f"Wybrana kolekcja: {active_coll.name}", icon='INFO')
                    col.label(text=f"Liczba krzywych: {len(active_coll.objects)}")
                    
                    # Przyciski akcji dla zaznaczonej kolekcji
                    row = col.row(align=True)
                    op = row.operator("therm.select_collection_objects", text="Zaznacz obiekty", icon='RESTRICT_SELECT_OFF')
                    op.collection_name = active_coll.name
                    op = row.operator("therm.delete_collection", text="Usuń", icon='TRASH')
                    op.collection_name = active_coll.name
                    
                    # Lista obiektów w kolekcji - POPRAWIONE
                    if active_coll.objects:
                        # Używamy prostszego podejścia bez dynamicznych właściwości
                        show_prop_name = f"show_objects_{active_coll.name.replace(' ', '_')}"
                        show_objects = getattr(context.scene, show_prop_name, False)
                        
                        # Bezpieczne wyświetlanie właściwości
                        if hasattr(context.scene, show_prop_name):
                            row = col.row()
                            row.prop(context.scene, show_prop_name, 
                                    text=f"Obiekty w kolekcji ({len(active_coll.objects)})", 
                                    icon='TRIA_DOWN' if show_objects else 'TRIA_RIGHT',
                                    emboss=False, toggle=True)
                            
                            if show_objects:
                                sub_box = col.box()
                                for obj in active_coll.objects:
                                    row_obj = sub_box.row()
                                    row_obj.label(text=obj.name, icon='CURVE_DATA')
                                    
                                    # Przyciski dla każdego obiektu
                                    row_actions = sub_box.row(align=True)
                                    op_select = row_actions.operator("therm.select_single_object", text="Zaznacz", icon='RESTRICT_SELECT_OFF')
                                    op_select.object_name = obj.name
                                    op_delete = row_actions.operator("therm.delete_single_object", text="Usuń", icon='TRASH')
                                    op_delete.object_name = obj.name
                                    op_delete.collection_name = active_coll.name
                        else:
                            # Fallback - prosty przycisk rozwijania
                            row = col.row()
                            if show_objects:
                                row.operator("therm.toggle_show_objects", text=f"Ukryj obiekty ({len(active_coll.objects)})", icon='TRIA_DOWN').collection_name = active_coll.name
                                sub_box = col.box()
                                for obj in active_coll.objects:
                                    row_obj = sub_box.row()
                                    row_obj.label(text=obj.name, icon='CURVE_DATA')
                            else:
                                row.operator("therm.toggle_show_objects", text=f"Pokaż obiekty ({len(active_coll.objects)})", icon='TRIA_RIGHT').collection_name = active_coll.name
        else:
            box.label(text="Brak kolekcji THERM", icon='INFO')
        
        # Eksport
        box = layout.box()
        box.label(text="Opcje eksportu:")
        box.prop(context.scene.therm_props, "open_export_folder")
        
        layout.separator()
        layout.operator("therm.export_to_therm", text="Eksportuj do THERM", icon='EXPORT')
        
        # Uruchamianie obliczeń THERM
        box = layout.box()
        box.label(text="Uruchamianie obliczeń THERM:", icon='PLAY')
        
        col = box.column()
        col.prop(context.scene.therm_props, "therm_executable_path", text="Ścieżka do THERM")
        
        if context.scene.therm_props.therm_executable_path and os.path.exists(context.scene.therm_props.therm_executable_path):
            col.label(text="✓ THERM znaleziony", icon='CHECKMARK')
        else:
            col.label(text="✗ Wskaż ścieżkę do THERM7.exe", icon='ERROR')
        
        blend_filepath = bpy.data.filepath
        if not blend_filepath:
            box.label(text="Zapisz plik Blender aby użyć tej funkcji", icon='ERROR')
        else:
            blend_filename = os.path.splitext(os.path.basename(blend_filepath))[0]
            therm_thmx_path = os.path.join(os.path.dirname(blend_filepath), f"{blend_filename}.thmx")
            therm_thm_path = os.path.join(os.path.dirname(blend_filepath), f"{blend_filename}.thm")
            
            col = box.column()
            
            row = col.row()
            row.operator("therm.run_therm_calculation_thmx", text="Uruchom obliczenia (.thmx)", icon='RENDER_RESULT')
            
            if not os.path.exists(therm_thmx_path):
                row = col.row()
                row.label(text="Plik .thmx nie istnieje", icon='ERROR')
            
            row = col.row()
            row.operator("therm.run_therm_calculation_thm", text="Uruchom THERM (.thm)", icon='FILE')
            
            if not os.path.exists(therm_thm_path):
                row = col.row()
                row.label(text="Plik .thm nie istnieje", icon='ERROR')
            
            row = col.row()
            row.operator("therm.open_therm_folder", text="Otwórz folder", icon='FILE_FOLDER')

        # SEKCJA U-SECTIONS
        box = layout.box()
        box.label(text="Sekcje U:", icon='MOD_ARRAY')
        
        # Informacja o zaznaczeniu
        selected_count = len(bpy.context.selected_objects)
        box.label(text=f"Zaznacz JEDNĄ krzywą Ti ({selected_count} obiektów zaznaczonych)", icon='INFO')
        
        # Sprawdź które USection już istnieją
        existing_usections = []
        for obj in bpy.data.objects:
            if obj.name.startswith('USection_'):
                existing_usections.append(obj.name.replace('USection_', ''))
        
        if existing_usections:
            box.label(text=f"Istniejące: {', '.join(sorted(existing_usections))}", icon='CURVE_DATA')
        
        # Pierwszy wiersz U1-U6
        row = box.row(align=True)
        row.operator("therm.create_usection_1", text="U1")
        row.operator("therm.create_usection_2", text="U2")
        row.operator("therm.create_usection_3", text="U3")
        row.operator("therm.create_usection_4", text="U4")
        row.operator("therm.create_usection_5", text="U5")
        row.operator("therm.create_usection_6", text="U6")
        
        # Drugi wiersz U7-U12
        row = box.row(align=True)
        row.operator("therm.create_usection_7", text="U7")
        row.operator("therm.create_usection_8", text="U8")
        row.operator("therm.create_usection_9", text="U9")
        row.operator("therm.create_usection_10", text="U10")
        row.operator("therm.create_usection_11", text="U11")
        row.operator("therm.create_usection_12", text="U12")
        
        # Instrukcja
        box.label(text="Uwaga: Tworzy USection_U1 z zaznaczonej krzywej Ti", icon='RESTRICT_SELECT_OFF')
        box.label(text="Automatycznie ustawia wartości w Geometry Nodes", icon='NODETREE')

        # Tymczasowo dodaj w sekcji U-Sections:
        row = box.row()
        row.operator("therm.debug_usections", text="Debug", icon='CONSOLE')

        # W panels.py, w sekcji U-Sections:
        row = box.row()
        row.operator("therm.debug_sockets", text="Debug Sockets", icon='NODETREE')

# Nowy operator do przełączania widoczności obiektów
class THERM_OT_toggle_show_objects(bpy.types.Operator):
    """Przełącza widoczność listy obiektów w kolekcji"""
    bl_idname = "therm.toggle_show_objects"
    bl_label = "Przełącz widoczność obiektów"
    
    collection_name: bpy.props.StringProperty()
    
    def execute(self, context):
        prop_name = f"show_objects_{self.collection_name.replace(' ', '_')}"
        current_value = getattr(context.scene, prop_name, False)
        setattr(context.scene, prop_name, not current_value)
        return {'FINISHED'}

# Nowy operator do ustawiania aktywnej kolekcji
class THERM_OT_set_active_collection(bpy.types.Operator):
    """Ustawia aktywną kolekcję THERM"""
    bl_idname = "therm.set_active_collection"
    bl_label = "Ustaw aktywną kolekcję"
    
    collection_name: bpy.props.StringProperty()
    
    def execute(self, context):
        context.scene.active_therm_collection = self.collection_name
        return {'FINISHED'}

# Operatory dla zarządzania kolekcjami
class THERM_OT_select_collection_objects(bpy.types.Operator):
    """Zaznacza wszystkie obiekty w wybranej kolekcji"""
    bl_idname = "therm.select_collection_objects"
    bl_label = "Zaznacz obiekty kolekcji"
    
    collection_name: bpy.props.StringProperty()
    
    def execute(self, context):
        if self.collection_name in bpy.data.collections:
            selected_coll = bpy.data.collections[self.collection_name]
            
            # Odznacz wszystkie obiekty
            bpy.ops.object.select_all(action='DESELECT')
            
            # Zaznacz obiekty z kolekcji
            for obj in selected_coll.objects:
                obj.select_set(True)
            
            self.report({'INFO'}, f"Zaznaczono {len(selected_coll.objects)} obiektów z {selected_coll.name}")
        
        return {'FINISHED'}

class THERM_OT_delete_collection(bpy.types.Operator):
    """Usuwa wybraną kolekcję THERM"""
    bl_idname = "therm.delete_collection"
    bl_label = "Usuń kolekcję"
    
    collection_name: bpy.props.StringProperty()
    
    def execute(self, context):
        if self.collection_name in bpy.data.collections:
            selected_coll = bpy.data.collections[self.collection_name]
            coll_name = selected_coll.name
            
            # Usuń kolekcję i jej obiekty
            for obj in selected_coll.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(selected_coll)
            
            # Zaktualizuj aktywną kolekcję jeśli została usunięta
            therm_collections = get_all_therm_collections()
            if therm_collections:
                context.scene.active_therm_collection = therm_collections[0].name
            else:
                # Bezpieczne ustawienie pustej wartości
                context.scene.active_therm_collection = "NONE"
            
            self.report({'INFO'}, f"Usunięto kolekcję: {coll_name}")
        
        return {'FINISHED'}

class THERM_OT_select_single_object(bpy.types.Operator):
    """Zaznacza pojedynczy obiekt"""
    bl_idname = "therm.select_single_object"
    bl_label = "Zaznacz obiekt"
    
    object_name: bpy.props.StringProperty()
    
    def execute(self, context):
        if self.object_name in bpy.data.objects:
            # Odznacz wszystkie obiekty
            bpy.ops.object.select_all(action='DESELECT')
            
            # Zaznacz wybrany obiekt
            obj = bpy.data.objects[self.object_name]
            obj.select_set(True)
            context.view_layer.objects.active = obj
            
            self.report({'INFO'}, f"Zaznaczono obiekt: {obj.name}")
        
        return {'FINISHED'}

class THERM_OT_delete_single_object(bpy.types.Operator):
    """Usuwa pojedynczy obiekt z kolekcji"""
    bl_idname = "therm.delete_single_object"
    bl_label = "Usuń obiekt"
    
    object_name: bpy.props.StringProperty()
    collection_name: bpy.props.StringProperty()
    
    def execute(self, context):
        if (self.object_name in bpy.data.objects and 
            self.collection_name in bpy.data.collections):
            
            obj = bpy.data.objects[self.object_name]
            coll = bpy.data.collections[self.collection_name]
            
            # Usuń obiekt z kolekcji i z blendera
            coll.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)
            
            self.report({'INFO'}, f"Usunięto obiekt: {self.object_name}")
        
        return {'FINISHED'}

def register():
    # Najpierw rejestrujemy klasy
    bpy.utils.register_class(THERM_OT_toggle_show_objects)
    bpy.utils.register_class(THERM_OT_set_active_collection)
    bpy.utils.register_class(THERM_OT_select_single_object)
    bpy.utils.register_class(THERM_OT_delete_single_object)
    bpy.utils.register_class(THERM_OT_select_collection_objects)
    bpy.utils.register_class(THERM_OT_delete_collection)
    bpy.utils.register_class(THERM_PT_panel)
    
    # Rejestrujemy właściwość dla aktywnej kolekcji z bezpieczną obsługą braku kolekcji
    def get_collection_items(self, context):
        therm_collections = get_all_therm_collections()
        if therm_collections:
            return [(coll.name, coll.name, f"Kolekcja {coll.name} z {len(coll.objects)} krzywymi") for coll in therm_collections]
        else:
            return [("NONE", "Brak kolekcji", "Brak dostępnych kolekcji THERM")]
    
    # Bezpieczna rejestracja właściwości
    try:
        bpy.types.Scene.active_therm_collection = bpy.props.EnumProperty(
            name="Aktywna kolekcja",
            description="Wybierz kolekcję THERM",
            items=get_collection_items
        )
    except Exception as e:
        print(f"Warning: Could not register active_therm_collection property: {e}")



def unregister():
    bpy.utils.unregister_class(THERM_PT_panel)
    bpy.utils.unregister_class(THERM_OT_delete_single_object)
    bpy.utils.unregister_class(THERM_OT_select_single_object)
    bpy.utils.unregister_class(THERM_OT_delete_collection)
    bpy.utils.unregister_class(THERM_OT_select_collection_objects)
    bpy.utils.unregister_class(THERM_OT_set_active_collection)
    bpy.utils.unregister_class(THERM_OT_toggle_show_objects)
    
    # Usuwamy właściwość
    if hasattr(bpy.types.Scene, 'active_therm_collection'):
        del bpy.types.Scene.active_therm_collection
    
    # Usuwamy dynamiczne właściwości dla rozwinięć obiektów
    for prop_name in dir(bpy.types.Scene):
        if prop_name.startswith('show_objects_'):
            try:
                delattr(bpy.types.Scene, prop_name)
            except:
                pass