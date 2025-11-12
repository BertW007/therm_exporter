import bpy
import bmesh
from mathutils import Vector, geometry
import math

def flip_downward_faces_only():
    """Znajduje i odwraca tylko faces które są skierowane w dół"""
    
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not selected_objects:
        print("Nie zaznaczono żadnych obiektów siatki")
        return 0
    
    original_mode = bpy.context.mode
    original_active = bpy.context.active_object
    
    if original_mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    total_flipped = 0
    
    for obj in selected_objects:
        print(f"Sprawdzanie obiektu: {obj.name}")
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        faces_flipped = 0
        
        for face in bm.faces:
            world_normal = obj.matrix_world.to_3x3() @ face.normal
            
            if world_normal.z < -0.01:
                face.normal_flip()
                faces_flipped += 1
                print(f"   Odwrócono face {face.index} (normalna: {world_normal})")
        
        bm.to_mesh(obj.data)
        bm.free()
        
        total_flipped += faces_flipped
        print(f"  Odwrócono {faces_flipped} faces skierowanych w dół w obiekcie {obj.name}")
    
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected_objects:
        obj.select_set(True)
    if original_active:
        bpy.context.view_layer.objects.active = original_active
    
    if original_mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='EDIT')
    
    print(f"Zakończono! Odwrócono łącznie {total_flipped} faces skierowanych w dół w {len(selected_objects)} obiektach")
    return total_flipped

def flip_downward_faces_with_threshold(threshold=-0.01):
    """Znajduje i odwraca tylko faces które są skierowane w dół z możliwością ustawienia progu"""
    
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not selected_objects:
        print("Nie zaznaczono żadnych obiektów siatki")
        return 0
    
    original_mode = bpy.context.mode
    original_active = bpy.context.active_object
    
    if original_mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    total_flipped = 0
    
    for obj in selected_objects:
        print(f"Sprawdzanie obiektu: {obj.name} (próg: {threshold})")
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        faces_flipped = 0
        
        for face in bm.faces:
            world_normal = obj.matrix_world.to_3x3() @ face.normal
            
            if world_normal.z < threshold:
                face.normal_flip()
                faces_flipped += 1
        
        bm.to_mesh(obj.data)
        bm.free()
        
        total_flipped += faces_flipped
        print(f"  Odwrócono {faces_flipped} faces skierowanych w dół")
    
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected_objects:
        obj.select_set(True)
    if original_active:
        bpy.context.view_layer.objects.active = original_active
    
    if original_mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='EDIT')
    
    print(f"Zakończono! Odwrócono łącznie {total_flipped} faces skierowanych w dół")
    return total_flipped

def check_and_fix_normals():
    """Sprawdza czy wszystkie faces mają normalne skierowane w górę i pyta o odwrócenie"""
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not selected_objects:
        return {'CANCELLED'}
    
    objects_with_wrong_normals = []
    
    for obj in selected_objects:
        mesh = obj.data
        world_matrix = obj.matrix_world
        
        original_mode = bpy.context.mode
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        wrong_faces_count = 0
        
        for poly in mesh.polygons:
            world_normal = world_matrix.to_3x3() @ poly.normal
            
            if world_normal.z < -0.1:
                wrong_faces_count += 1
        
        if wrong_faces_count > 0:
            objects_with_wrong_normals.append((obj.name, wrong_faces_count))
        
        if original_mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except:
                pass
    
    if objects_with_wrong_normals:
        bpy.ops.therm.recalc_normals_confirm('INVOKE_DEFAULT')
        return {'CANCELLED'}
    
    return {'FINISHED'}

def recalc_normals_upward():
    """Odwraca normalne wszystkich zaznaczonych obiektów do góry - PROSTE ODWRÓCENIE"""
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    original_mode = bpy.context.mode
    
    if original_mode == 'EDIT_MESH':
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()
        return
    
    for obj in selected_objects:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode='OBJECT')
    
    if original_mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode=original_mode)
        except:
            pass

def check_and_round_vertices():
    """Sprawdza czy wierzchołki mają współrzędne z dokładnością do 0.1m i pyta o zaokrąglenie"""
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not selected_objects:
        return {'CANCELLED'}
    
    objects_with_irregular_vertices = []
    precision = 0.1
    
    for obj in selected_objects:
        mesh = obj.data
        
        original_mode = bpy.context.mode
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        irregular_vertices_count = 0
        
        for vert in mesh.vertices:
            for coord in vert.co:
                remainder = abs(coord) % precision
                if remainder > 0.001 and remainder < (precision - 0.001):
                    irregular_vertices_count += 1
                    break
        
        if irregular_vertices_count > 0:
            objects_with_irregular_vertices.append((obj.name, irregular_vertices_count))
        
        if original_mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except:
                pass
    
    if objects_with_irregular_vertices:
        bpy.ops.therm.round_vertices_confirm('INVOKE_DEFAULT')
        return {'CANCELLED'}
    
    return {'FINISHED'}

def round_vertices_to_precision(precision=0.1):
    """Zaokrągla wierzchołki zaznaczonych obiektów do określonej precyzji"""
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    original_mode = bpy.context.mode
    original_active = bpy.context.active_object
    original_selection = bpy.context.selected_objects.copy()
    
    vertices_modified = 0
    
    for obj in selected_objects:
        mesh = obj.data
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.mesh.select_all(action='SELECT')
        
        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()
        
        for vert in bm.verts:
            original_co = vert.co.copy()
            
            vert.co.x = round(vert.co.x / precision) * precision
            vert.co.y = round(vert.co.y / precision) * precision
            vert.co.z = round(vert.co.z / precision) * precision
            
            if (original_co - vert.co).length > 0.0001:
                vertices_modified += 1
        
        bmesh.update_edit_mesh(mesh)
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.object.select_all(action='DESELECT')
    for obj in original_selection:
        obj.select_set(True)
    if original_active:
        bpy.context.view_layer.objects.active = original_active
    
    if original_mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode=original_mode)
        except:
            pass
    
    return vertices_modified

# =============================================================================
# FUNKCJE DO OBLICZANIA GRUBOŚCI
# =============================================================================

def get_curve_points_world(curve_obj):
    """Pobiera punkty krzywej w przestrzeni świata"""
    points = []
    world_matrix = curve_obj.matrix_world
    
    for spline in curve_obj.data.splines:
        if spline.type == 'POLY' and len(spline.points) >= 2:
            for point in spline.points[:2]:  # Tylko pierwsze 2 punkty
                world_point = world_matrix @ point.co.xyz
                points.append(world_point)
    
    return points

def find_closest_point_on_line(point, line_start, line_end):
    """Znajduje najbliższy punkt na linii do danego punktu"""
    line_vec = line_end - line_start
    point_vec = point - line_start
    
    line_length = line_vec.length
    line_unitvec = line_vec.normalized()
    
    # Rzut punktu na linię
    projection_length = point_vec.dot(line_unitvec)
    projection_length = max(0, min(projection_length, line_length))
    
    return line_start + line_unitvec * projection_length

def calculate_material_thickness(mesh_object, ti_curve, te_curve):
    """Oblicza grubość materiału jako odległość prostopadłą między krzywymi Ti i Te"""
    try:
        print(f"🔍 Obliczanie grubości dla: {mesh_object.name}")
        
        # Pobierz punkty z krzywych Ti i Te
        ti_points = get_curve_points_world(ti_curve)
        te_points = get_curve_points_world(te_curve)
        
        if len(ti_points) < 2 or len(te_points) < 2:
            print("❌ Krzywe muszą mieć co najmniej 2 punkty")
            return 0.0
        
        # Weź środkowy punkt krzywej Ti jako punkt odniesienia
        ti_midpoint = (ti_points[0] + ti_points[1]) / 2
        ti_direction = (ti_points[1] - ti_points[0]).normalized()
        
        # Znajdź najbliższy punkt na krzywej Te
        closest_te_point = find_closest_point_on_line(ti_midpoint, te_points[0], te_points[1])
        
        # Oblicz wektor prostopadły do Ti
        perpendicular_vector = Vector((-ti_direction.y, ti_direction.x, 0))
        
        # Oblicz odległość prostopadłą
        thickness_vector = closest_te_point - ti_midpoint
        perpendicular_distance = abs(thickness_vector.dot(perpendicular_vector))
        
        print(f"✅ Grubość prostopadła {mesh_object.name}: {perpendicular_distance:.4f}m")
        return perpendicular_distance
        
    except Exception as e:
        print(f"❌ Błąd obliczania grubości: {e}")
        return 0.0

def get_mesh_dimensions(mesh_object, ti_curve, te_curve):
    """Oblicza wymiary mesha w kierunku prostopadłym do krzywych Ti/Te"""
    try:
        # Pobierz bounding box w przestrzeni świata
        bbox_corners = [mesh_object.matrix_world @ Vector(corner) for corner in mesh_object.bound_box]
        
        # Pobierz kierunek krzywej Ti
        ti_points = get_curve_points_world(ti_curve)
        if len(ti_points) < 2:
            return 0.0
        
        ti_direction = (ti_points[1] - ti_points[0]).normalized()
        perpendicular_direction = Vector((-ti_direction.y, ti_direction.x, 0))
        
        # Rzut wszystkie punkty bounding box na kierunek prostopadły
        projections = [point.dot(perpendicular_direction) for point in bbox_corners]
        
        # Oblicz rozpiętość (grubość) w kierunku prostopadłym
        thickness = max(projections) - min(projections)
        
        print(f"📏 Wymiar BBox {mesh_object.name}: {thickness:.4f}m")
        return thickness
        
    except Exception as e:
        print(f"❌ Błąd obliczania wymiarów: {e}")
        return 0.0

def calculate_smart_thickness(mesh_object, ti_curve, te_curve):
    """Zawsze używa bounding box do obliczania grubości"""
    try:
        print(f"🧮 OBLICZANIE GRUBOŚCI BOUNDING BOX: {mesh_object.name}")
        
        # Użyj tylko metody bounding box
        thickness = get_mesh_dimensions(mesh_object, ti_curve, te_curve)
        
        # Sprawdź czy wartość jest realistyczna
        if 0.001 <= thickness <= 2.0:
            print(f"✅ GRUBOŚĆ BOUNDING BOX: {thickness:.4f}m")
        else:
            print(f"⚠️  NIEREALISTYCZNA GRUBOŚĆ: {thickness:.4f}m")
        
        return thickness
        
    except Exception as e:
        print(f"❌ Błąd obliczania grubości: {e}")
        return 0.0