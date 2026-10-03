/* SPDX-License-Identifier: GPL-2.0-only */
class OriginalLockFixtureInfo extends AIInfo {
	function GetAuthor()      { return "OpenTT3D contributors"; }
	function GetName()        { return "OpenTT3D Original Lock Fixture"; }
	function GetShortName()   { return "3DLK"; }
	function GetDescription() { return "Build original locks at naturally existing sea-level/elevated slopes through public NoAI commands; never terraform or force graphics."; }
	function GetVersion()     { return 1; }
	function GetAPIVersion()  { return "15"; }
	function GetDate()        { return "2026-10-03"; }
	function CreateInstance(){ return "OriginalLockFixture"; }
	function UseAsRandomAI() { return false; }
}
RegisterAI(OriginalLockFixtureInfo());
