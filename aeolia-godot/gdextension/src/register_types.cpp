#include "register_types.h"
#include "terrain_math_ext.h"

#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/godot.hpp>
#include <godot_cpp/classes/engine.hpp>

using namespace godot;

// Singleton instance — owned by the extension, lifetime tied to the module.
static TerrainMathExt *terrain_math_singleton = nullptr;

void initialize_terrain_math_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    ClassDB::register_class<TerrainMathExt>();

    // Register as Engine singleton so GDScript can reach it via
    // Engine.get_singleton("TerrainMathExt") without referencing the class name
    // directly (which would be a parse error when the extension is not built).
    terrain_math_singleton = memnew(TerrainMathExt);
    Engine::get_singleton()->register_singleton("TerrainMathExt", terrain_math_singleton);
}

void uninitialize_terrain_math_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    Engine::get_singleton()->unregister_singleton("TerrainMathExt");
    memdelete(terrain_math_singleton);
    terrain_math_singleton = nullptr;
}

extern "C" {

GDExtensionBool GDE_EXPORT terrain_math_ext_init(
        GDExtensionInterfaceGetProcAddress p_get_proc_address,
        const GDExtensionClassLibraryPtr p_library,
        GDExtensionInitialization *r_initialization) {

    godot::GDExtensionBinding::InitObject init_obj(
            p_get_proc_address, p_library, r_initialization);

    init_obj.register_initializer(initialize_terrain_math_module);
    init_obj.register_terminator(uninitialize_terrain_math_module);
    init_obj.set_minimum_library_initialization_level(
            MODULE_INITIALIZATION_LEVEL_SCENE);

    return init_obj.init();
}

} // extern "C"
