/* SPDX-License-Identifier: GPL-2.0-only */
class TrainCatalogueInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Train Catalogue"; }
	function GetShortName()   { return "3DTC"; }
	function GetDescription() { return "Build and operate original wagon families through public NoAI commands."; }
	function GetVersion()     { return 1; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-09-24"; }
	function CreateInstance() { return "TrainCatalogue"; }
	function UseAsRandomAI()  { return false; }
	function GetSettings() {
		AddSetting({name = "review_curves", description = "Add a four-corner review detour", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_rail_type", description = "Original railtype", min_value = 0, max_value = 3, default_value = 1, flags = CONFIG_NONE});
		AddSetting({name = "review_engine", description = "Requested original locomotive, or automatic selection", min_value = -1, max_value = 115, default_value = -1, flags = CONFIG_NONE});
		AddSetting({name = "review_first", description = "First original wagon engine ID", min_value = 0, max_value = 115, default_value = 27, flags = CONFIG_NONE});
		AddSetting({name = "review_last", description = "Last original wagon engine ID", min_value = 0, max_value = 115, default_value = 53, flags = CONFIG_NONE});
		AddSetting({name = "review_hold", description = "Stop the verified consist for review", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_low_effect_id", description = "Build and sell a spare locomotive before the operating train for original effect pool-order review", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_departing", description = "Restart the returning train through public commands and save its ordinary acceleration", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_clearance", description = "Build a bridge and real tunnel on the review route", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_source", description = "Fund an original cargo producer, or movement-only review", min_value = -1, max_value = 36, default_value = -1, flags = CONFIG_NONE});
		AddSetting({name = "review_destination", description = "Fund an original accepting industry, or -1 for a town", min_value = -1, max_value = 36, default_value = 1, flags = CONFIG_NONE});
		AddSetting({name = "review_feeder", description = "Original input producer for a real processing-industry truck route", min_value = -1, max_value = 36, default_value = -1, flags = CONFIG_NONE});
	}
}
RegisterAI(TrainCatalogueInfo());
