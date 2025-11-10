bl_info = {
    "name": "THERM Exporter",
    "author": "RX Studio Robert Wietecki",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Tool",
    "description": "Export geometry to THERM software with boundary conditions",
    "category": "Import-Export",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": ""
}

from . import (
    properties,
    operators,
    panels,
    geometry_utils,
    boundary_conditions,
    therm_export,
    therm_import,
    therm_runner
)

def register():
    properties.register()
    operators.register()
    panels.register()

def unregister():
    panels.unregister()
    operators.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()