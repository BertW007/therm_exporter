import bpy

class THERMProperties(bpy.types.PropertyGroup):
    open_export_folder: bpy.props.BoolProperty(
        name="Otwórz folder po eksporcie",
        description="Otwórz folder z wyeksportowanym plikiem po zakończeniu eksportu",
        default=True
    )
    
    round_precision: bpy.props.EnumProperty(
        name="Precyzja zaokrąglania",
        description="Precyzja zaokrąglania wierzchołków",
        items=[
            ('1', "1 m", "Zaokrąglij do 1 metra"),
            ('0.1', "0.1 m", "Zaokrąglij do 1 decymetra"),
            ('0.01', "0.01 m", "Zaokrąglij do 1 centymetra"),
            ('0.001', "0.001 m", "Zaokrąglij do 1 milimetra"),
            ('0.0001', "0.0001 m", "Zaokrąglij do 1 mikrometra"),
        ],
        default='0.001'
    )
    
    show_normals: bpy.props.BoolProperty(
        name="Pokaż normalne",
        description="Pokaż wektory normalne dla zaznaczonych obiektów",
        default=False
    )
    
    flip_threshold: bpy.props.FloatProperty(
        name="Próg czułości odwracania",
        description="Jak bardzo w dół musi być skierowana normalna żeby ją odwrócić (ujemne wartości)",
        default=-0.01,
        min=-1.0,
        max=0.0
    )
    
    therm_executable_path: bpy.props.StringProperty(
        name="Ścieżka do THERM7.exe",
        description="Ręcznie wskaż ścieżkę do THERM7.exe jeśli nie jest automatycznie znajdowana",
        subtype='FILE_PATH',
        default=""
    )

class THERMEdgeProperties(bpy.types.PropertyGroup):
    ti_temperature: bpy.props.FloatProperty(
        name="Ti Temperature",
        description="Temperatura wewnętrzna",
        default=20.0
    )
    ti_rsi: bpy.props.FloatProperty(
        name="Rsi",
        description="Opór przejmowania ciepła od strony wewnętrznej",
        default=0.13,
        min=0.01,
        max=1.0
    )
    te_temperature: bpy.props.FloatProperty(
        name="Te Temperature",
        description="Temperatura zewnętrzna",
        default=-20.0
    )
    te_rse: bpy.props.FloatProperty(
        name="Rse",
        description="Opór przejmowania ciepła od strony zewnętrznej",
        default=0.04,
        min=0.00,
        max=1.0
    )
    ufactor_name: bpy.props.StringProperty(
        name="U-Factor Name",
        description="Nazwa U-Factor dla krawędzi",
        default="UFactor"
    )
    
    flip_direction: bpy.props.BoolProperty(
        name="Odwróć kierunek krawędzi",
        description="Odwróć kierunek wszystkich krawędzi (dla kierunku lewostronnego w THERM)",
        default=True
    )

def register():
    bpy.utils.register_class(THERMProperties)
    bpy.utils.register_class(THERMEdgeProperties)
    bpy.types.Scene.therm_props = bpy.props.PointerProperty(type=THERMProperties)
    bpy.types.Scene.therm_edge_props = bpy.props.PointerProperty(type=THERMEdgeProperties)

def unregister():
    del bpy.types.Scene.therm_props
    del bpy.types.Scene.therm_edge_props
    bpy.utils.unregister_class(THERMEdgeProperties)
    bpy.utils.unregister_class(THERMProperties)