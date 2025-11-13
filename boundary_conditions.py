import bpy
import bmesh
from mathutils import Vector
import math

def get_therm_collection_name(list_type, ufactor_name=None):
    """Generuje nazwę kolekcji na podstawie typu i parametrów"""
    if list_type == 'Ti':
        ti_temp = bpy.context.scene.therm_edge_props.ti_temperature
        ti_rsi = bpy.context.scene.therm_edge_props.ti_rsi
        return f"THERM_Ti={ti_temp}_Rsi={ti_rsi:.3f}"
    elif list_type == 'Te':
        te_temp = bpy.context.scene.therm_edge_props.te_temperature
        te_rse = bpy.context.scene.therm_edge_props.te_rse
        return f"THERM_Te={te_temp}_Rse={te_rse:.3f}"
    elif list_type == 'Adiabatic':
        return "THERM_Adiabatic"
    elif list_type == 'UFactor' and ufactor_name:
        return f"THERM_UFactor_{ufactor_name}"
    else:
        return f"THERM_{list_type}"

def ensure_therm_collection(collection_name):
    """Tworzy kolekcję jeśli nie istnieje i zwraca ją"""
    if collection_name not in bpy.data.collections:
        coll = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(coll)
    return bpy.data.collections[collection_name]

def create_material(name, color):
    """Tworza materiał o podanej nazwie i kolorze"""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.4
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (200, 0)
    
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    mat.diffuse_color = color
    
    return mat

def get_material_for_type(list_type):
    """Zwraca materiał odpowiedni dla danego typu warunku brzegowego"""
    materials = {
        'Ti': ('RED', (1.0, 0.0, 0.0, 1.0)),
        'Te': ('BLUE', (0.0, 0.0, 1.0, 1.0)),
        'Adiabatic': ('GREY', (0.5, 0.5, 0.5, 1.0)),
        'UFactor': ('GREEN', (0.0, 1.0, 0.0, 1.0))
    }
    
    if list_type in materials:
        mat_name, color = materials[list_type]
        return create_material(mat_name, color)
    
    return create_material('RED', (1.0, 0.0, 0.0, 1.0))

def get_ordered_edges_from_selection():
    """Pobiera wszystkie zaznaczone krawędzie jako osobne segmenty"""
    edges_data = []
    
    if bpy.context.mode == 'EDIT_MESH':
        for obj in bpy.context.selected_objects:
            if obj.type != 'MESH':
                continue
                
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()
            bm.verts.ensure_lookup_table()
            
            selected_edges = [edge for edge in bm.edges if edge.select]
            
            if not selected_edges:
                continue
            
            world_matrix = obj.matrix_world
            
            for edge in selected_edges:
                # Dla każdej krawędzi tworzymy osobny zestaw punktów
                v1_world = world_matrix @ edge.verts[0].co
                v2_world = world_matrix @ edge.verts[1].co
                
                edges_data.append({
                    'object': obj,
                    'points': [v1_world, v2_world],  # Tylko 2 punkty na krawędź
                    'object_name': obj.name,
                    'edge_index': edge.index
                })
    
    return edges_data



def create_arrow_geometry_nodes(curve_obj, arrow_type):
    """Dodaje geometry nodes z strzałkami do krzywej używając istniejących grup"""
    try:
        if curve_obj.modifiers and any(mod.type == 'NODES' for mod in curve_obj.modifiers):
            return
        
        if arrow_type == "RED":
            node_group_name = "THERM Arrows RED"
        elif arrow_type == "BLUE":
            node_group_name = "THERM Arrows BLUE"
        elif arrow_type == "UFactor":
            node_group_name = "THERM U-Factor"
        elif arrow_type == "Adiabatic":
            node_group_name = "THERM Adiabatic"
        else:
            print(f"Nieznany typ geometry nodes: {arrow_type}")
            return
        
        if node_group_name not in bpy.data.node_groups:
            print(f"Grupa Geometry Nodes '{node_group_name}' nie istnieje")
            return
        
        node_group = bpy.data.node_groups[node_group_name]
        modifier = curve_obj.modifiers.new(name=f"THERM_{arrow_type}", type='NODES')
        modifier.node_group = node_group
        
        print(f"Dodano Geometry Nodes '{node_group_name}' do krzywej {curve_obj.name}")
        
    except Exception as e:
        print(f"Błąd dodawania geometry nodes: {e}")

def create_continuous_curve_from_edges(list_type='Ti', ufactor_name=None):
    """Tworzy osobne krzywe dla każdej zaznaczonej krawędzi (każda z 2 punktami) - SPRAWDZA DUPLIKATY"""

    original_mode = bpy.context.mode
    original_active = bpy.context.active_object
    original_selection = bpy.context.selected_objects.copy()
    
    ordered_edges_data = get_ordered_edges_from_selection()
    if not ordered_edges_data:
        print("Nie znaleziono uporządkowanych krawędzi")
        return None
    
    created_curves = []
    
    collection_name = get_therm_collection_name(list_type, ufactor_name)
    target_collection = ensure_therm_collection(collection_name)
    
    material = get_material_for_type(list_type)
    
    was_in_edit_mode = (original_mode == 'EDIT_MESH')
    if was_in_edit_mode:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # Pobierz wszystkie obiekty siatki w scenie do sprawdzania kierunku
    all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    
    curve_counter = 1
    skipped_count = 0
    
    for edge_data in ordered_edges_data:
        obj = edge_data['object']
        world_points = edge_data['points']
        
        print(f"Tworzenie krzywych z {len(world_points)} punktów:")
        
        # Dla każdej pary punktów tworzymy osobną krzywą
        for j in range(len(world_points) - 1):
            v1 = world_points[j]
            v2 = world_points[j + 1]
            
            # Sprawdź czy trzeba odwrócić kierunek dla tej pary punktów
            edge_vector = v2 - v1
            edge_direction_2d = Vector((edge_vector.x, edge_vector.y)).normalized()
            normal_2d = Vector((-edge_direction_2d.y, edge_direction_2d.x))
            
            # Sprawdź geometrię po lewej stronie
            geometry_on_left = is_geometry_on_left_side_simple(v1, v2, normal_2d, all_objects)
            
            if geometry_on_left:
                final_v1, final_v2 = v1, v2
            else:
                final_v1, final_v2 = v2, v1
                print(f"  Odwrócono kierunek krawędzi {curve_counter}")
            
            # SPRAWDŹ CZY KRZYWA JUŻ ISTNIEJE NA TEJ KRAWĘDZI (tylko kolidujące typy)
            existing_curve_type = get_existing_curve_type_on_edge(final_v1, final_v2, list_type)
            if existing_curve_type:
                print(f"  ⚠️  Pominięto krawędź {curve_counter} - istnieje już krzywa typu {existing_curve_type}")
                skipped_count += 1
                curve_counter += 1
                continue
            
            # Sprawdź czy krzywa już istnieje (tylko dla tego samego typu)
            if list_type != 'UFactor' and is_curve_duplicate(final_v1, final_v2, target_collection):
                print(f"  Pominięto duplikat krzywej {curve_counter}")
                skipped_count += 1
                curve_counter += 1
                continue
            
            # Utwórz nazwę krzywej
            if list_type == 'UFactor' and ufactor_name:
                curve_name = f"UFactor_{ufactor_name}_{curve_counter}"
            elif list_type == 'Ti':
                ti_temp = bpy.context.scene.therm_edge_props.ti_temperature
                ti_rsi = bpy.context.scene.therm_edge_props.ti_rsi
                curve_name = f"Ti={ti_temp}_Rsi={ti_rsi:.3f}_{curve_counter}"
            elif list_type == 'Te':
                te_temp = bpy.context.scene.therm_edge_props.te_temperature
                te_rse = bpy.context.scene.therm_edge_props.te_rse
                curve_name = f"Te={te_temp}_Rse={te_rse:.3f}_{curve_counter}"
            else:
                curve_name = f"{list_type}_{curve_counter}"
            
            # Utwórz krzywą z 2 punktami
            curve_data = bpy.data.curves.new(curve_name, type='CURVE')
            curve_data.dimensions = '3D'
            curve_data.resolution_u = 2
            
            spline = curve_data.splines.new('POLY')
            spline.points.add(1)  # Dodaj jeden punkt (razem 2)
            
            spline.points[0].co = (final_v1.x, final_v1.y, final_v1.z, 1)
            spline.points[1].co = (final_v2.x, final_v2.y, final_v2.z, 1)
            
            curve_data.bevel_mode = 'ROUND'
            curve_data.bevel_depth = 0.0
            curve_data.bevel_resolution = 0
            
            curve_obj = bpy.data.objects.new(curve_name, curve_data)
            target_collection.objects.link(curve_obj)
            curve_obj.data.materials.append(material)
            
            if list_type == 'Ti':
                create_arrow_geometry_nodes(curve_obj, "RED")
            elif list_type == 'Te':
                create_arrow_geometry_nodes(curve_obj, "BLUE")
            elif list_type == 'UFactor':
                create_arrow_geometry_nodes(curve_obj, "UFactor")
            elif list_type == 'Adiabatic':
                create_arrow_geometry_nodes(curve_obj, "Adiabatic")
            
            created_curves.append(curve_obj)
            print(f"  Utworzono krzywą {curve_name}: {final_v1} -> {final_v2}")
            curve_counter += 1
    
    bpy.ops.object.select_all(action='DESELECT')
    for obj in original_selection:
        obj.select_set(True)
    if original_active:
        bpy.context.view_layer.objects.active = original_active
    
    if was_in_edit_mode:
        bpy.ops.object.mode_set(mode='EDIT')
    
    print(f"Utworzono {len(created_curves)} pojedynczych krzywych w kolekcji '{collection_name}', pominięto {skipped_count} duplikatów")
    return created_curves

def is_geometry_on_left_side_simple(v1, v2, normal_2d, all_objects):
    """Uproszczona wersja sprawdzania geometrii po lewej stronie dla pojedynczej krawędzi"""
    edge_center = (v1 + v2) / 2
    edge_center_2d = Vector((edge_center.x, edge_center.y))
    
    search_distance = 0.1
    test_point_2d = edge_center_2d + normal_2d * search_distance
    test_point_3d = Vector((test_point_2d.x, test_point_2d.y, edge_center.z))
    
    for obj in all_objects:
        if is_point_inside_any_face(test_point_3d, obj):
            return True
    
    return False
# Funkcje automatycznego tworzenia krzywych

def find_true_external_edges_corrected(selected_objects):
    """Znajduje tylko prawdziwe zewnętrzne krawędzie które NIE mają DWÓCH wspólnych wierzchołków z innymi obiektami"""
    
    if not selected_objects:
        print("Nie zaznaczono żadnych obiektów siatki")
        return []
    
    print("=== SZUKANIE PRAWDZIWYCH ZEWNĘTRZNYCH KRAWĘDZI ===")
    
    original_mode = bpy.context.mode
    if original_mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    true_external_edges = []
    all_boundary_edges = []
    all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    
    for obj in selected_objects:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        
        for edge in bm.edges:
            if len(edge.link_faces) == 1:
                v1_world = obj.matrix_world @ edge.verts[0].co
                v2_world = obj.matrix_world @ edge.verts[1].co
                
                edge_data = {
                    'object': obj,
                    'edge': edge,
                    'v1_world': v1_world,
                    'v2_world': v2_world,
                    'object_name': obj.name,
                    'edge_index': edge.index,
                    'length': (v2_world - v1_world).length
                }
                all_boundary_edges.append(edge_data)
        
        bm.free()
    
    print(f"Znaleziono {len(all_boundary_edges)} krawędzi brzegowych w zaznaczonych obiektach")
    
    for i, edge_data in enumerate(all_boundary_edges):
        if not has_matching_edge_in_other_objects(edge_data, all_objects):
            true_external_edges.append(edge_data)
    
    if original_mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='EDIT')
    
    print(f"=== Znaleziono {len(true_external_edges)} PRAWDZIWYCH zewnętrznych krawędzi ===")
    return true_external_edges

def has_matching_edge_in_other_objects(edge_data, all_objects):
    """Sprawdza czy krawędź ma ODPOWIADAJĄCĄ krawędź w innym obiekcie"""
    current_obj = edge_data['object']
    v1 = edge_data['v1_world']
    v2 = edge_data['v2_world']
    
    tolerance = 0.001
    
    for other_obj in all_objects:
        if other_obj == current_obj:
            continue
        
        bm_other = bmesh.new()
        bm_other.from_mesh(other_obj.data)
        bm_other.edges.ensure_lookup_table()
        
        for other_edge in bm_other.edges:
            other_v1_world = other_obj.matrix_world @ other_edge.verts[0].co
            other_v2_world = other_obj.matrix_world @ other_edge.verts[1].co
            
            if (edges_match(v1, v2, other_v1_world, other_v2_world, tolerance) or
                edges_match(v1, v2, other_v2_world, other_v1_world, tolerance)):
                bm_other.free()
                return True
        
        bm_other.free()
    
    return False

def edges_match(v1_a, v2_a, v1_b, v2_b, tolerance):
    """Sprawdza czy dwie krawędzie mają te same dwa punkty końcowe"""
    return ((v1_a - v1_b).length < tolerance and 
            (v2_a - v2_b).length < tolerance)

def ensure_correct_edge_direction(edge_data, all_objects):
    """Ustala prawidłowy kierunek krawędzi wg reguły lewoskrętnej"""
    v1_world = edge_data['v1_world']
    v2_world = edge_data['v2_world']
    
    edge_vector = v2_world - v1_world
    edge_direction_2d = Vector((edge_vector.x, edge_vector.y)).normalized()
    normal_2d = Vector((-edge_direction_2d.y, edge_direction_2d.x))
    
    geometry_on_left = is_geometry_on_left_side(edge_data, normal_2d, all_objects)
    
    if geometry_on_left:
        return v1_world, v2_world
    else:
        print(f"  Odwrócono kierunek krawędzi {edge_data['edge_index']} - geometria po prawej")
        return v2_world, v1_world

def is_geometry_on_left_side(edge_data, normal_2d, all_objects):
    """Sprawdza czy geometria znajduje się po lewej stronie krawędzi"""
    current_obj = edge_data['object']
    v1_world = edge_data['v1_world']
    v2_world = edge_data['v2_world']
    
    edge_center = (v1_world + v2_world) / 2
    edge_center_2d = Vector((edge_center.x, edge_center.y))
    
    search_distance = 0.1
    test_point_2d = edge_center_2d + normal_2d * search_distance
    test_point_3d = Vector((test_point_2d.x, test_point_2d.y, edge_center.z))
    
    for obj in all_objects:
        if is_point_inside_any_face(test_point_3d, obj):
            return True
    
    test_point_2d_right = edge_center_2d - normal_2d * search_distance
    test_point_3d_right = Vector((test_point_2d_right.x, test_point_2d_right.y, edge_center.z))
    
    for obj in all_objects:
        if is_point_inside_any_face(test_point_3d_right, obj):
            return False
    
    return True

def is_point_inside_any_face(point_3d, obj):
    """Sprawdza czy punkt znajduje się wewnątrz którejś ze ścian obiektu"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    world_to_local = obj.matrix_world.inverted()
    point_local = world_to_local @ point_3d
    
    for face in bm.faces:
        face_center = face.calc_center_median()
        if abs(point_local.z - face_center.z) < 0.1:
            if is_point_inside_face_2d(point_local, face):
                bm.free()
                return True
    
    bm.free()
    return False

def is_point_inside_face_2d(point, face):
    """Sprawdza czy punkt 2D znajduje się wewnątrz ściany (ignoruje Z)"""
    verts_2d = [Vector((v.co.x, v.co.y)) for v in face.verts]
    return is_point_in_polygon_2d(Vector((point.x, point.y)), verts_2d)

def is_point_in_polygon_2d(point, polygon):
    """Sprawdza czy punkt 2D znajduje się wewnątrz polygonu 2D (ray casting)"""
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0].x, polygon[0].y
    for i in range(n + 1):
        p2x, p2y = polygon[i % n].x, polygon[i % n].y
        if point.y > min(p1y, p2y):
            if point.y <= max(p1y, p2y):
                if point.x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (point.y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or point.x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def create_curve_between_points_with_direction(v1, v2, name, collection, list_type):
    """Tworzy krzywą między dwoma punktami z określonym kierunkiem"""
    try:
        curve_data = bpy.data.curves.new(name, type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 2
        
        spline = curve_data.splines.new('POLY')
        spline.points.add(1)
        
        spline.points[0].co = (v1.x, v1.y, v1.z, 1)
        spline.points[1].co = (v2.x, v2.y, v2.z, 1)
        
        curve_data.bevel_mode = 'ROUND'
        curve_data.bevel_depth = 0.0
        
        curve_obj = bpy.data.objects.new(name, curve_data)
        collection.objects.link(curve_obj)
        
        material = get_material_for_type(list_type)
        curve_obj.data.materials.append(material)
        
        if list_type == 'Ti':
            create_arrow_geometry_nodes(curve_obj, "RED")
        elif list_type == 'Te':
            create_arrow_geometry_nodes(curve_obj, "BLUE")
        elif list_type == 'UFactor':
            create_arrow_geometry_nodes(curve_obj, "UFactor")
        elif list_type == 'Adiabatic':
            create_arrow_geometry_nodes(curve_obj, "Adiabatic")
        
        return curve_obj
        
    except Exception as e:
        print(f"Błąd tworzenia krzywej {name}: {e}")
        return None

def is_curve_duplicate(v1, v2, collection):
    """Sprawdza czy krzywa już istnieje"""
    tolerance = 0.001
    
    for obj in collection.objects:
        if obj.type == 'CURVE' and obj.data.splines:
            spline = obj.data.splines[0]
            if len(spline.points) >= 2:
                existing_v1 = Vector((spline.points[0].co.x, spline.points[0].co.y, spline.points[0].co.z))
                existing_v2 = Vector((spline.points[1].co.x, spline.points[1].co.y, spline.points[1].co.z))
                
                if ((v1 - existing_v1).length < tolerance and (v2 - existing_v2).length < tolerance) or \
                   ((v1 - existing_v2).length < tolerance and (v2 - existing_v1).length < tolerance):
                    return True
    return False

def create_auto_curves_on_external_edges(list_type='Adiabatic', ufactor_name=None):
    """Tworzy krzywe automatycznie na zewnętrznych krawędziach z kierunkiem lewoskrętnym - SPRAWDZA DUPLIKATY"""
    
    print(f"=== TWORZENIE AUTOMATYCZNYCH KRZYWYCH {list_type} NA ZEWNĘTRZNYCH KRAWĘDZIACH ===")
    
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not selected_objects:
        print("Nie zaznaczono żadnych obiektów siatki!")
        return []
    
    external_edges = find_true_external_edges_corrected(selected_objects)
    
    if not external_edges:
        print("Nie znaleziono żadnych prawdziwych zewnętrznych krawędzi!")
        return []
    
    if list_type == 'UFactor' and ufactor_name:
        collection_name = f"THERM_UFactor_{ufactor_name}"
    else:
        collection_name = get_therm_collection_name(list_type)
    
    target_collection = ensure_therm_collection(collection_name)
    created_curves = []
    all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    
    skipped_count = 0
    
    for i, edge_data in enumerate(external_edges):
        v1_final, v2_final = ensure_correct_edge_direction(edge_data, all_objects)
        
        # SPRAWDŹ CZY NA TEJ KRAWĘDZI JUŻ ISTNIEJE KOLIDUJĄCA KRZYWA
        existing_curve_type = get_existing_curve_type_on_edge(v1_final, v2_final, list_type)
        
        if existing_curve_type:
            print(f"  ⚠️  Pominięto krawędź {i+1} - istnieje już krzywa typu {existing_curve_type}")
            skipped_count += 1
            continue
        
        # Sprawdź również prostym duplikatem (tylko dla tego samego typu)
        if list_type != 'UFactor' and has_existing_curve_on_edge(v1_final, v2_final):
            skipped_count += 1
            continue
        
        if list_type == 'UFactor' and ufactor_name:
            curve_name = f"UFactor_{ufactor_name}_{edge_data['object_name']}_{i+1}"
        elif list_type == 'Ti':
            ti_temp = bpy.context.scene.therm_edge_props.ti_temperature
            ti_rsi = bpy.context.scene.therm_edge_props.ti_rsi
            curve_name = f"Ti={ti_temp}_Rsi={ti_rsi:.3f}_{edge_data['object_name']}_{i+1}"
        elif list_type == 'Te':
            te_temp = bpy.context.scene.therm_edge_props.te_temperature
            te_rse = bpy.context.scene.therm_edge_props.te_rse
            curve_name = f"Te={te_temp}_Rse={te_rse:.3f}_{edge_data['object_name']}_{i+1}"
        else:
            curve_name = f"{list_type}_{edge_data['object_name']}_{i+1}"
        
        curve_obj = create_curve_between_points_with_direction(v1_final, v2_final, curve_name, target_collection, list_type)
        
        if curve_obj:
            created_curves.append(curve_obj)
            print(f"Utworzono krzywą: {curve_name}")
            
            edge_vector = v2_final - v1_final
            print(f"  Kierunek: {v1_final} -> {v2_final} (długość: {edge_vector.length:.3f}m)")
    
    print(f"=== UTWORZONO {len(created_curves)} KRZYWYCH {list_type}, POMINIĘTO {skipped_count} DUPLIKATÓW ===")
    return created_curves

def has_existing_curve_on_edge(v1, v2, tolerance=0.001):
    """Sprawdza czy na krawędzi już istnieje jakaś krzywa warunku brzegowego"""
    for coll in bpy.data.collections:
        if coll.name.startswith('THERM_'):
            for obj in coll.objects:
                if obj.type == 'CURVE' and obj.data.splines:
                    spline = obj.data.splines[0]
                    if len(spline.points) >= 2:
                        existing_v1 = Vector((spline.points[0].co.x, spline.points[0].co.y, spline.points[0].co.z))
                        existing_v2 = Vector((spline.points[1].co.x, spline.points[1].co.y, spline.points[1].co.z))
                        
                        if ((v1 - existing_v1).length < tolerance and (v2 - existing_v2).length < tolerance) or \
                           ((v1 - existing_v2).length < tolerance and (v2 - existing_v1).length < tolerance):
                            print(f"  ⚠️  Pominięto - istnieje już krzywa {obj.name} w kolekcji {coll.name}")
                            return True
    return False

def get_existing_curve_type_on_edge(v1, v2, list_type=None, tolerance=0.001):
    """Zwraca typ istniejącej krzywej na krawędzi lub None jeśli nie ma
    list_type: jeśli podany, sprawdza tylko krzywe które kolidują z tym typem"""
    
    for coll in bpy.data.collections:
        if coll.name.startswith('THERM_'):
            curve_type = None
            if coll.name.startswith('THERM_Ti='):
                curve_type = 'Ti'
            elif coll.name.startswith('THERM_Te='):
                curve_type = 'Te'
            elif coll.name == 'THERM_Adiabatic':
                curve_type = 'Adiabatic'
            elif coll.name.startswith('THERM_UFactor_'):
                curve_type = 'UFactor'
            
            # SPRAWDŹ CZY TEN TYP KRZYWEJ KOLIDUJE Z list_type
            if list_type and not do_curve_types_collide(list_type, curve_type):
                continue  # Pomijaj krzywe które nie kolidują
            
            for obj in coll.objects:
                if obj.type == 'CURVE' and obj.data.splines:
                    spline = obj.data.splines[0]
                    if len(spline.points) >= 2:
                        existing_v1 = Vector((spline.points[0].co.x, spline.points[0].co.y, spline.points[0].co.z))
                        existing_v2 = Vector((spline.points[1].co.x, spline.points[1].co.y, spline.points[1].co.z))
                        
                        if ((v1 - existing_v1).length < tolerance and (v2 - existing_v2).length < tolerance) or \
                           ((v1 - existing_v2).length < tolerance and (v2 - existing_v1).length < tolerance):
                            return curve_type
    return None



def do_curve_types_collide(new_type, existing_type):
    """Sprawdza czy dwa typy krzywych kolidują (nie mogą istnieć razem na tej samej krawędzi)"""
    
    # Jeśli któryś z typów jest None (nie znaleziono krzywej), nie ma kolizji
    if existing_type is None:
        return False
    
    # U-Factor może współistnieć z dowolnym innym typem
    if new_type == 'UFactor' or existing_type == 'UFactor':
        return False
    
    # Ti, Te, Adiabatic nie mogą współistnieć ze sobą
    collision_groups = [['Ti', 'Te', 'Adiabatic']]
    
    for group in collision_groups:
        if new_type in group and existing_type in group:
            return True
    
    return False