/* SPDX-License-Identifier: GPL-2.0-only */
class ShipShortInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Short Bridge Ship"; }
	function GetShortName()   { return "3DSS"; }
	function GetDescription() { return "Build a narrow canal and a short vanilla bridge, then operate ordinary ships beneath it."; }
	function GetVersion()     { return 1; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-11-09"; }
	function CreateInstance(){ return "ShipShort"; }
	function UseAsRandomAI() { return false; }
	function GetSettings() {
		AddSetting({name="review_engine",description="Vanilla ship engine to operate",min_value=204,max_value=214,default_value=204,flags=CONFIG_NONE});
		AddSetting({name="canal_width",description="Narrow canal width in tiles",min_value=2,max_value=3,default_value=2,flags=CONFIG_NONE});
		AddSetting({name="bridge_type",description="Exact vanilla road bridge type",min_value=0,max_value=12,default_value=1,flags=CONFIG_NONE});
		AddSetting({name="bridge_hold",description="Stop the selected ship under the short bridge span",min_value=0,max_value=1,default_value=0,flags=CONFIG_NONE});
	}
}
RegisterAI(ShipShortInfo());
