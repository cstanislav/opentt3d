/* SPDX-License-Identifier: GPL-2.0-only */
class RailFixtureInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Rail Fixture"; }
	function GetShortName()   { return "3DRF"; }
	function GetDescription() { return "Build a reproducible renderer review layout using the public NoAI API."; }
	function GetVersion()     { return 1; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-09-23"; }
	function CreateInstance() { return "RailFixture"; }
	function UseAsRandomAI()  { return false; }
	function GetSettings() {
		AddSetting({name = "review_airport", description = "Main airport: commuter, city, metropolitan, international, intercontinental", min_value = 0, max_value = 4, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_aircraft", description = "Aircraft: disabled, operate, or hold after verified return", min_value = 0, max_value = 2, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_train_engine", description = "Electric locomotive engine ID plus one; zero selects the first available", min_value = 0, max_value = 116, default_value = 0, flags = CONFIG_NONE});
		AddSetting({name = "review_train_hold", description = "Stop the verified locomotive at its east review terminus", min_value = 0, max_value = 1, default_value = 0, flags = CONFIG_NONE});
	}
}
RegisterAI(RailFixtureInfo());
