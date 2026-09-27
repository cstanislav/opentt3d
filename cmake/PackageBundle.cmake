string(TIMESTAMP CURRENT_YEAR "%Y")

set(CPACK_BUNDLE_NAME "OpenTT3D")
set(CPACK_BUNDLE_ICON "${CMAKE_SOURCE_DIR}/assets/branding/opentt3d.icns")
set(CPACK_BUNDLE_PLIST "${CMAKE_CURRENT_BINARY_DIR}/Info.plist")
set(CPACK_DMG_BACKGROUND_IMAGE "${CMAKE_SOURCE_DIR}/assets/branding/install-background.png")
set(CPACK_BUNDLE_APPLE_ENTITLEMENTS "${CMAKE_SOURCE_DIR}/os/macosx/openttd.entitlements")
set(CPACK_DMG_FORMAT "UDBZ")

set(OPENTT3D_MINIMUM_MACOS "10.13.0")
if(CMAKE_OSX_DEPLOYMENT_TARGET)
    set(OPENTT3D_MINIMUM_MACOS "${CMAKE_OSX_DEPLOYMENT_TARGET}")
endif()

# Create a temporary Info.plist.in, where we will fill in the version via
# CPackProperties.cmake.in. This because at this point in time the version
# is not yet known.
configure_file("${CMAKE_SOURCE_DIR}/os/macosx/Info.plist.in" "${CMAKE_CURRENT_BINARY_DIR}/Info.plist.in")
set(CPACK_BUNDLE_PLIST_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/Info.plist.in")

# Delay fixup_bundle() till the install step; this makes sure all executables
# exists and it can do its job.
if(Vulkan_FOUND)
    # The install step removes the build RPATH before BundleUtilities resolves
    # @rpath/libMoltenVK.dylib, so provide its pinned location explicitly.
    get_filename_component(OPENTT3D_BUNDLE_LIBRARY_DIRS "${Vulkan_LIBRARY}" DIRECTORY)
endif()
install(
    CODE
    "
        include(BundleUtilities)
        set(BU_CHMOD_BUNDLE_ITEMS TRUE)
        fixup_bundle(\"\${CMAKE_INSTALL_PREFIX}/../MacOS/${BINARY_NAME}\"  \"\" \"${OPENTT3D_BUNDLE_LIBRARY_DIRS}\")
    "
    DESTINATION .
    COMPONENT Runtime)
