add_subdirectory(baseset)

add_library(media INTERFACE)
add_library(openttd::media ALIAS media)

if(NOT UNIX OR APPLE)
    return()
endif()

set(MEDIA_BINARY_FILES)
foreach(SIZE 16 32 48 64 128 256 512)
    set(SOURCE_FILE "${CMAKE_SOURCE_DIR}/assets/branding/opentt3d-${SIZE}.png")
    set(ICON_DIR "${CMAKE_CURRENT_BINARY_DIR}/icons/hicolor/${SIZE}x${SIZE}/apps")
    set(ICON_FILE "${ICON_DIR}/${BINARY_NAME}.png")
    add_custom_command(OUTPUT "${ICON_FILE}"
        COMMAND ${CMAKE_COMMAND} -E make_directory "${ICON_DIR}"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${SOURCE_FILE}" "${ICON_FILE}"
        MAIN_DEPENDENCY "${SOURCE_FILE}"
        VERBATIM
    )
    list(APPEND MEDIA_BINARY_FILES "${ICON_FILE}")
endforeach()

set(PIXMAP_FILE "${CMAKE_CURRENT_BINARY_DIR}/pixmaps/${BINARY_NAME}.png")
add_custom_command(OUTPUT "${PIXMAP_FILE}"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/pixmaps"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${CMAKE_SOURCE_DIR}/assets/branding/opentt3d-48.png" "${PIXMAP_FILE}"
    MAIN_DEPENDENCY "${CMAKE_SOURCE_DIR}/assets/branding/opentt3d-48.png"
    VERBATIM
)
list(APPEND MEDIA_BINARY_FILES "${PIXMAP_FILE}")
add_custom_target(media_files DEPENDS ${MEDIA_BINARY_FILES})
add_dependencies(media media_files)

get_target_property(LANG_SOURCE_FILES language_files LANG_SOURCE_FILES)
set(DESKTOP_BINARY_NAME ${BINARY_NAME}.desktop)
add_custom_command_timestamp(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${DESKTOP_BINARY_NAME}
    COMMAND ${CMAKE_COMMAND}
            -DDESKTOP_SOURCE_FILE=${CMAKE_CURRENT_SOURCE_DIR}/openttd.desktop
            -DDESKTOP_BINARY_FILE=${CMAKE_CURRENT_BINARY_DIR}/${DESKTOP_BINARY_NAME}
            -DBINARY_NAME=${BINARY_NAME}
            -P ${CMAKE_SOURCE_DIR}/cmake/scripts/Desktop.cmake
            -- ${LANG_SOURCE_FILES}
    MAIN_DEPENDENCY ${CMAKE_CURRENT_SOURCE_DIR}/openttd.desktop
    DEPENDS ${LANG_SOURCE_FILES} ${CMAKE_SOURCE_DIR}/cmake/scripts/Desktop.cmake
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Generating OpenTT3D desktop file"
)
add_custom_target_timestamp(desktop_file DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/${DESKTOP_BINARY_NAME})
add_dependencies(media desktop_file)
