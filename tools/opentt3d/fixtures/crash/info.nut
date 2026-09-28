/* SPDX-License-Identifier: GPL-2.0-only */
class CrashReviewInfo extends AIInfo {
	function GetAuthor() { return "OpenTT3D"; }
	function GetName() { return "OpenTT3D Crash Review"; }
	function GetDescription() { return "Ordinary opposing trains for source crash/effect observation."; }
	function GetVersion() { return 1; }
	function GetDate() { return "2026-09-28"; }
	function CreateInstance() { return "CrashReview"; }
	function GetShortName() { return "T3CR"; }
	function GetAPIVersion() { return "15"; }
	function UseAsRandomAI() { return false; }
	function GetSettings() {
		AddSetting({name="review_engine",description="Original locomotive",min_value=0,max_value=115,default_value=13,flags=CONFIG_NONE});
	}
}
RegisterAI(CrashReviewInfo());
