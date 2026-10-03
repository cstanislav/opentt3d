/* SPDX-License-Identifier: GPL-2.0-only */
class OriginalRiverSurveyInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Original River Survey"; }
	function GetShortName()   { return "3DRV"; }
	function GetDescription() { return "Read naturally generated river tiles through public NoAI queries; never build, terraform or force graphics."; }
	function GetVersion()     { return 1; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-10-03"; }
	function CreateInstance(){ return "OriginalRiverSurvey"; }
	function UseAsRandomAI() { return false; }
}
RegisterAI(OriginalRiverSurveyInfo());
