/* SPDX-License-Identifier: GPL-2.0-only */
class RoadworksInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Roadworks"; }
	function GetShortName()   { return "3DRW"; }
	function GetDescription() { return "Fund ordinary town roadworks for original bulldozer effect review."; }
	function GetVersion()     { return 1; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-09-27"; }
	function CreateInstance(){ return "Roadworks"; }
	function UseAsRandomAI() { return false; }
}
RegisterAI(RoadworksInfo());
