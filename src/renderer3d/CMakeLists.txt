find_package(Python3 COMPONENTS Interpreter REQUIRED)

set(MODEL_HEADER "${CMAKE_BINARY_DIR}/generated/renderer3d_models.h")
add_custom_command(
    OUTPUT "${MODEL_HEADER}"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/tools/assets/compile_models.py"
            "${CMAKE_SOURCE_DIR}/assets/3d/models.json" --header "${MODEL_HEADER}"
    DEPENDS "${CMAKE_SOURCE_DIR}/tools/assets/compile_models.py"
            "${CMAKE_SOURCE_DIR}/assets/3d/models.json"
    COMMENT "Compiling authored OpenTT3D model assemblies"
    VERBATIM
)
add_custom_target(renderer3d_models DEPENDS "${MODEL_HEADER}")
add_dependencies(openttd_lib renderer3d_models)
target_include_directories(openttd_lib PRIVATE "${CMAKE_BINARY_DIR}/generated" "${CMAKE_CURRENT_SOURCE_DIR}")
add_files(geometry.hpp camera.hpp gl_backend.hpp gl_backend.cpp viewport_3d.h viewport_3d.cpp)
add_files(sprite_textures.hpp sprite_textures.cpp)
add_files(texture_bounds.hpp atlas_allocator.hpp)
add_files(instance_batcher.hpp indexed_mesh.hpp)
add_files(material_chart.hpp)
add_files(voxel_geometry.hpp voxel_mesh_cache.hpp voxel_volume.hpp voxel_packed_mesh.hpp voxel_visibility.hpp voxel_visibility_worker.hpp voxel_models.h voxel_models.cpp)
add_files(profiling.h profiling.cpp)
add_files(camera_motion.hpp)
add_files(branding.h branding.cpp)
add_files(vulkan_backend.h)
if(Vulkan_FOUND)
    target_compile_definitions(openttd_lib PUBLIC WITH_VULKAN)
    target_link_libraries(openttd_lib Vulkan::Vulkan)
    add_files(vulkan_backend.cpp)
    find_program(GLSLANG_VALIDATOR glslangValidator)
    set(VULKAN_SHADER_HEADER "${CMAKE_BINARY_DIR}/generated/renderer3d_vulkan_shaders.hpp")
    if(GLSLANG_VALIDATOR)
        add_custom_command(OUTPUT "${VULKAN_SHADER_HEADER}"
            COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/tools/assets/compile_shaders.py"
                --compiler "${GLSLANG_VALIDATOR}" --output "${VULKAN_SHADER_HEADER}"
            DEPENDS "${CMAKE_SOURCE_DIR}/tools/assets/compile_shaders.py"
                shaders/vk_world.vert shaders/vk_world.frag shaders/vk_voxel.frag shaders/vk_voxel_slice.frag shaders/vk_composite.vert shaders/vk_composite.frag
                shaders/vk_voxel_shared.glsl
            VERBATIM
        )
        add_custom_target(renderer3d_shaders DEPENDS "${VULKAN_SHADER_HEADER}")
        add_dependencies(openttd_lib renderer3d_shaders)
    else()
        configure_file(shaders/embedded.hpp "${VULKAN_SHADER_HEADER}" COPYONLY)
    endif()
endif()
configure_file("${CMAKE_SOURCE_DIR}/assets/branding/opentt3d.icns" "${CMAKE_BINARY_DIR}/baseset/opentt3d.icns" COPYONLY)
add_files(reference_export.cpp)
add_files(world_capture.h world_capture.cpp)
add_files(bridge_geometry.hpp bridge_capture.h bridge_capture.cpp)
add_files(terrain_geometry.hpp)
add_files(tree_geometry.hpp)
add_files(clear_surface_geometry.hpp)
add_files(tunnel_geometry.hpp tunnel_capture.h tunnel_capture.cpp)
add_files(rail_geometry.hpp rail_capture.h rail_capture.cpp)
add_files(rail_detail_geometry.hpp rail_detail_capture.h rail_detail_capture.cpp)
add_files(depot_geometry.hpp depot_capture.h depot_capture.cpp)
add_files(crossing_geometry.hpp crossing_capture.h crossing_capture.cpp)
add_files(road_stop_geometry.hpp road_stop_capture.h road_stop_capture.cpp)
add_files(station_geometry.hpp station_capture.h station_capture.cpp)
add_files(ground_detail_geometry.hpp ground_detail_capture.h ground_detail_capture.cpp)
add_files(authored_geometry.h authored_geometry.cpp)
set(RENDERER3D_DATA_FILES)
foreach(PACK houses trees industries)
    set(OUTPUT_FILE "${CMAKE_BINARY_DIR}/baseset/opentt3d-${PACK}.json")
    add_custom_command(
        OUTPUT "${OUTPUT_FILE}"
        COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_BINARY_DIR}/baseset"
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/tools/assets/validate_models.py"
            "${CMAKE_SOURCE_DIR}/assets/3d/${PACK}.json"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${CMAKE_SOURCE_DIR}/assets/3d/${PACK}.json" "${OUTPUT_FILE}"
        COMMAND ${CMAKE_COMMAND} -E touch "${OUTPUT_FILE}"
        DEPENDS "${CMAKE_SOURCE_DIR}/assets/3d/${PACK}.json" "${CMAKE_SOURCE_DIR}/tools/assets/validate_models.py"
        VERBATIM
    )
    list(APPEND RENDERER3D_DATA_FILES "${OUTPUT_FILE}")
endforeach()
set(VEHICLE_CATALOGUE "${CMAKE_BINARY_DIR}/baseset/opentt3d-vehicles.json")
add_custom_command(OUTPUT "${VEHICLE_CATALOGUE}"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/tools/assets/compile_vehicles.py"
        "${CMAKE_SOURCE_DIR}/assets/3d/vehicles.json" --output "${VEHICLE_CATALOGUE}"
    DEPENDS "${CMAKE_SOURCE_DIR}/tools/assets/compile_vehicles.py"
        "${CMAKE_SOURCE_DIR}/assets/3d/vehicles.json"
        "${CMAKE_SOURCE_DIR}/src/table/engines.h" "${CMAKE_SOURCE_DIR}/src/table/train_sprites.h"
        "${CMAKE_SOURCE_DIR}/src/roadveh_cmd.cpp" "${CMAKE_SOURCE_DIR}/src/ship_cmd.cpp" "${CMAKE_SOURCE_DIR}/src/aircraft_cmd.cpp"
    VERBATIM
)
list(APPEND RENDERER3D_DATA_FILES "${VEHICLE_CATALOGUE}")
set(VOXEL_CATALOGUE "${CMAKE_BINARY_DIR}/baseset/opentt3d-voxels.json")
add_custom_command(OUTPUT "${VOXEL_CATALOGUE}"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/tools/assets/compile_voxels.py"
        "${CMAKE_SOURCE_DIR}/assets/3d/voxels.json" --output "${VOXEL_CATALOGUE}"
    DEPENDS "${CMAKE_SOURCE_DIR}/assets/3d/voxels.json" "${CMAKE_SOURCE_DIR}/tools/assets/compile_voxels.py"
    VERBATIM
)
list(APPEND RENDERER3D_DATA_FILES "${VOXEL_CATALOGUE}")
add_custom_target(renderer3d_asset_files ALL DEPENDS ${RENDERER3D_DATA_FILES})
add_dependencies(openttd renderer3d_asset_files)
add_test_files(renderer3d_camera.cpp)
add_test_files(renderer3d_transport.cpp)
add_test_files(renderer3d_vegetation.cpp)
add_test_files(renderer3d_voxels.cpp)
