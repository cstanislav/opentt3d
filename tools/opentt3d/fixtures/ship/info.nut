/* SPDX-License-Identifier: GPL-2.0-only */
class ShipCatalogueInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Ship Catalogue"; }
	function GetShortName()   { return "3DSC"; }
	function GetDescription() { return "Build an ordinary canal harbour and operate selected original ships between docks."; }
	function GetVersion()     { return 6; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-09-24"; }
	function CreateInstance(){ return "ShipCatalogue"; }
	function UseAsRandomAI() { return false; }
	function GetSettings() {
		AddSetting({name="review_first",description="First vanilla ship engine",min_value=204,max_value=214,default_value=204,flags=CONFIG_NONE});
		AddSetting({name="review_last",description="Last vanilla ship engine",min_value=204,max_value=214,default_value=214,flags=CONFIG_NONE});
		AddSetting({name="depot_axis",description="Ship depot axis",min_value=0,max_value=1,default_value=0,flags=CONFIG_NONE});
		AddSetting({name="depot_service",description="Recurring ordinary depot service",min_value=0,max_value=1,default_value=0,flags=CONFIG_NONE});
		AddSetting({name="depot_hold_ticks",description="Ordinary depot-stop wait before public restart",min_value=0,max_value=256,default_value=0,flags=CONFIG_NONE});
		AddSetting({name="all_docks",description="Build both additional dock-bank orientations",min_value=0,max_value=1,default_value=0,flags=CONFIG_NONE});
		AddSetting({name="dock_hold",description="Retain the final ordinary full-load dock call for review",min_value=0,max_value=1,default_value=0,flags=CONFIG_NONE});
		AddSetting({name="buoy_waypoint",description="Build and visit an original buoy waypoint",min_value=0,max_value=1,default_value=0,flags=CONFIG_NONE});
	}
}
RegisterAI(ShipCatalogueInfo());
