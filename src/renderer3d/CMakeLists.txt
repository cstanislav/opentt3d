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
add_test_files(renderer3d_camera.cpp)
