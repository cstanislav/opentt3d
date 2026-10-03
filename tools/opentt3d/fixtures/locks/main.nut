/* SPDX-License-Identifier: GPL-2.0-only */
class OriginalLockFixture extends AIController {
	function Fail(message) {
		AILog.Error("LOCK_FIXTURE_FAILED " + message + " error=" + AIError.GetLastErrorString());
		while (true) this.Sleep(1000);
	}
	function CanBuild(tile) {
		local test = AITestMode();
		return AIMarine.BuildLock(tile);
	}
	function Start() {
		AICompany.SetName("Original Lock Review");
		if (!AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount())) this.Fail("ordinary loan");
		local slopes = [AITile.SLOPE_NE,AITile.SLOPE_SE,AITile.SLOPE_SW,AITile.SLOPE_NW];
		local dx = [-1,0,1,0], dy = [0,1,0,-1];
		local locks = [];
		for (local elevation = 0; elevation < 2; elevation++) {
			for (local direction = 0; direction < 4; direction++) {
				local chosen = AIMap.TILE_INVALID;
				for (local y = 4; y < AIMap.GetMapSizeY()-4 && chosen == AIMap.TILE_INVALID; y++) {
					for (local x = 4; x < AIMap.GetMapSizeX()-4; x++) {
						local tile = AIMap.GetTileIndex(x,y);
						if (AITile.GetSlope(tile) != slopes[direction] || AIMarine.IsLockTile(tile)) continue;
						local height = AITile.GetMinHeight(tile);
						if ((elevation == 0 && height != 0) || (elevation == 1 && height == 0)) continue;
						local lower = AIMap.GetTileIndex(x-dx[direction],y-dy[direction]);
						local upper = AIMap.GetTileIndex(x+dx[direction],y+dy[direction]);
						if (AITile.GetSlope(lower) != AITile.SLOPE_FLAT || AITile.GetSlope(upper) != AITile.SLOPE_FLAT) continue;
						if (AITile.GetMinHeight(lower) != height || AITile.GetMinHeight(upper) != height+1) continue;
						if (!this.CanBuild(tile) || !AIMarine.BuildLock(tile)) continue;
						if (!AIMarine.IsLockTile(lower) || !AIMarine.IsLockTile(tile) || !AIMarine.IsLockTile(upper)) this.Fail("original three-tile lock absent");
						if (!AIMarine.AreWaterTilesConnected(lower,tile) || !AIMarine.AreWaterTilesConnected(tile,upper) ||
							!AIMarine.AreWaterTilesConnected(upper,tile) || !AIMarine.AreWaterTilesConnected(tile,lower)) this.Fail("original lock connectivity");
						local record = "{\"tile\":" + tile + ",\"x\":" + x + ",\"y\":" + y +
							",\"direction\":" + direction + ",\"elevation\":" + elevation + ",\"height\":" + height +
							",\"lower\":" + lower + ",\"upper\":" + upper + ",\"connected_both_ways\":true}";
						locks.append(record);
						AILog.Info("LOCK_FIXTURE_BUILT " + record);
						chosen = tile;
						break;
					}
				}
				if (chosen == AIMap.TILE_INVALID) this.Fail("no legal natural site elevation=" + elevation + " direction=" + direction);
			}
		}
		local records = "";
		foreach (index, record in locks) records += (index == 0 ? "" : ",") + record;
		AILog.Info("LOCK_FIXTURE_READY {\"company\":" + AICompany.ResolveCompanyID(AICompany.COMPANY_SELF) +
			",\"map_width\":" + AIMap.GetMapSizeX() + ",\"map_height\":" + AIMap.GetMapSizeY() + ",\"locks\":[" + records + "]}");
		while (true) this.Sleep(1000);
	}
}
