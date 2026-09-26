/* SPDX-License-Identifier: GPL-2.0-only */
/** Confirm the pinned Vulkan runtime can enumerate a real graphics device. */
#include <vulkan/vulkan.h>
#include <cstdio>
#include <cstring>
#include <vector>

int main()
{
	VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
	app.pApplicationName = "OpenTT3D Vulkan probe";
	app.apiVersion = VK_API_VERSION_1_1;
	uint32_t extension_count = 0;
	vkEnumerateInstanceExtensionProperties(nullptr, &extension_count, nullptr);
	std::vector<VkExtensionProperties> available(extension_count);
	vkEnumerateInstanceExtensionProperties(nullptr, &extension_count, available.data());
	std::vector<const char *> extensions;
	bool portability = false;
	for (const auto &extension : available) {
		if (std::strcmp(extension.extensionName, VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME) == 0) {
			extensions.push_back(VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME);
			portability = true;
		}
	}
	VkInstanceCreateInfo create{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
	create.pApplicationInfo = &app;
	create.flags = portability ? VK_INSTANCE_CREATE_ENUMERATE_PORTABILITY_BIT_KHR : 0;
	create.enabledExtensionCount = static_cast<uint32_t>(extensions.size());
	create.ppEnabledExtensionNames = extensions.data();
	VkInstance instance = VK_NULL_HANDLE;
	VkResult result = vkCreateInstance(&create, nullptr, &instance);
	if (result != VK_SUCCESS) { std::fprintf(stderr, "vkCreateInstance failed: %d\n", result); return 1; }
	uint32_t count = 0;
	result = vkEnumeratePhysicalDevices(instance, &count, nullptr);
	if (result != VK_SUCCESS || count == 0) { vkDestroyInstance(instance, nullptr); return 2; }
	std::vector<VkPhysicalDevice> devices(count);
	vkEnumeratePhysicalDevices(instance, &count, devices.data());
	bool graphics = false;
	for (VkPhysicalDevice device : devices) {
		VkPhysicalDeviceProperties properties;
		vkGetPhysicalDeviceProperties(device, &properties);
		uint32_t families = 0;
		vkGetPhysicalDeviceQueueFamilyProperties(device, &families, nullptr);
		std::vector<VkQueueFamilyProperties> queues(families);
		vkGetPhysicalDeviceQueueFamilyProperties(device, &families, queues.data());
		bool has_graphics = false;
		for (const auto &queue : queues) has_graphics |= (queue.queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0;
		graphics |= has_graphics;
		std::printf("%s: Vulkan %u.%u.%u, graphics=%s, texture=%u, array layers=%u\n", properties.deviceName,
			VK_API_VERSION_MAJOR(properties.apiVersion), VK_API_VERSION_MINOR(properties.apiVersion), VK_API_VERSION_PATCH(properties.apiVersion),
			has_graphics ? "yes" : "no", properties.limits.maxImageDimension2D, properties.limits.maxImageArrayLayers);
	}
	vkDestroyInstance(instance, nullptr);
	return graphics ? 0 : 3;
}
