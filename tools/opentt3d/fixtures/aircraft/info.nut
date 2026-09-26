/* SPDX-License-Identifier: GPL-2.0-only */
class AircraftCatalogueInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Aircraft Catalogue"; }
	function GetShortName()   { return "3DAC"; }
	function GetDescription() { return "Operate original aircraft through public NoAI construction and orders."; }
	function GetVersion()     { return 1; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-09-26"; }
	function CreateInstance() { return "AircraftCatalogue"; }
	function UseAsRandomAI()  { return false; }
	function GetSettings() {
		AddSetting({name = "review_first", description = "First original aircraft engine ID", min_value = 215, max_value = 255, default_value = 215, flags = CONFIG_NONE});
		AddSetting({name = "review_last", description = "Last original aircraft engine ID", min_value = 215, max_value = 255, default_value = 238, flags = CONFIG_NONE});
		AddSetting({name = "review_hold_ticks", description = "Hold destination service until this many ticks after reloading", min_value = 0, max_value = 4096, default_value = 0, flags = CONFIG_NONE});
	}
}
RegisterAI(AircraftCatalogueInfo());
