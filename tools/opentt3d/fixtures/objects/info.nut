/* SPDX-License-Identifier: GPL-2.0-only */
class OriginalObjectFixtureInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Original Object Fixture"; }
	function GetShortName()   { return "3DOF"; }
	function GetDescription() { return "Build an ordinary company HQ, town-action statue and flat/sloped owned land through the unmodified public NoAI API."; }
	function GetVersion()     { return 2; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-10-03"; }
	function CreateInstance(){ return "OriginalObjectFixture"; }
	function UseAsRandomAI() { return false; }
}
RegisterAI(OriginalObjectFixtureInfo());
