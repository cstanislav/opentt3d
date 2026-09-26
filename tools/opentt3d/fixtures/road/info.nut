/* SPDX-License-Identifier: GPL-2.0-only */
class RoadCatalogueInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Road Catalogue"; }
	function GetShortName()   { return "3DRC"; }
	function GetDescription() { return "Operate selected vanilla road families with ordinary public commands."; }
	function GetVersion()     { return 1; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-09-24"; }
	function CreateInstance(){ return "RoadCatalogue"; }
	function UseAsRandomAI() { return false; }
	function GetSettings() {
		AddSetting({name="review_first",description="First vanilla road engine",min_value=116,max_value=203,default_value=116,flags=CONFIG_NONE});
		AddSetting({name="review_last",description="Last vanilla road engine",min_value=116,max_value=203,default_value=203,flags=CONFIG_NONE});
	}
}
RegisterAI(RoadCatalogueInfo());
