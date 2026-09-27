/* SPDX-License-Identifier: GPL-2.0-only */
class IndustryFixtureInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Industry Fixture"; }
	function GetShortName()   { return "3DIF"; }
	function GetDescription() { return "Fund an industry and observe ordinary construction using the public NoAI API."; }
	function GetVersion()     { return 5; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-09-24"; }
	function CreateInstance() { return "IndustryFixture"; }
	function UseAsRandomAI()  { return false; }
	function GetSettings() {
		AddSetting({name = "review_industry", description = "Original industry type to fund", min_value = 0, max_value = 36, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_town_site", description = "Find a legal existing-house site for a town-only industry", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_coal_service", description = "After construction, operate a real coal truck to a funded power station", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_cargo_service", description = "Operate a real cargo route between the selected industries", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_destination", description = "Original accepting industry to fund", min_value = 0, max_value = 36, default_value = 1, flags = CONFIG_NONE});
		AddSetting({name = "review_destination_town_site", description = "Fund the destination on an actual town house and connect the public roads", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_depot_directions", description = "Build all four actual road-depot exits on the service site", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_truck_engine", description = "Requested original cargo truck, or automatic selection", min_value = -1, max_value = 255, default_value = -1, flags = CONFIG_NONE});
	}
}
RegisterAI(IndustryFixtureInfo());
