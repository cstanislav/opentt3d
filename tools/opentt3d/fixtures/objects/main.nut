/* SPDX-License-Identifier: GPL-2.0-only */
class OriginalObjectFixture extends AIController {
	function Fail(message) {
		AILog.Error("OBJECT_FIXTURE_FAILED " + message + " error=" + AIError.GetLastErrorString());
		while (true) this.Sleep(1000);
	}
	function Start() {
		AICompany.SetName("Original Object Review");
		if (!AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount())) this.Fail("ordinary loan");
		local headquarters = AIMap.TILE_INVALID;
		for (local y = 8; y < AIMap.GetMapSizeY()-8 && headquarters == AIMap.TILE_INVALID; y++) {
			for (local x = 8; x < AIMap.GetMapSizeX()-8; x++) {
				local tile = AIMap.GetTileIndex(x,y);
				if (!AITile.IsBuildableRectangle(tile,2,2)) continue;
				local flat = true;
				for (local dx = 0; dx < 2; dx++) for (local dy = 0; dy < 2; dy++) {
					if (AITile.GetSlope(AIMap.GetTileIndex(x+dx,y+dy)) != AITile.SLOPE_FLAT) flat = false;
				}
				if (flat && AICompany.BuildCompanyHQ(tile)) { headquarters = tile; break; }
			}
		}
		if (headquarters == AIMap.TILE_INVALID) this.Fail("no ordinary flat HQ site");
		local statue_town = -1;
		local towns = AITownList();
		for (local town = towns.Begin(); !towns.IsEnd(); town = towns.Next()) {
			if (AITown.PerformTownAction(town,AITown.TOWN_ACTION_BUILD_STATUE)) { statue_town = town; break; }
		}
		if (statue_town < 0) this.Fail("ordinary statue town action");
		if (!AIObjectType.IsValidObjectType(3)) this.Fail("original owned-land object type is unavailable");
		local owned_flat = AIMap.TILE_INVALID, owned_slope = AIMap.TILE_INVALID;
		local slope_code = 0;
		for (local y = 8; y < AIMap.GetMapSizeY()-8; y++) {
			for (local x = 8; x < AIMap.GetMapSizeX()-8; x++) {
				local tile = AIMap.GetTileIndex(x,y);
				if (!AITile.IsBuildable(tile)) continue;
				local slope = AITile.GetSlope(tile);
				if (slope == AITile.SLOPE_FLAT && owned_flat == AIMap.TILE_INVALID) {
					if (AIObjectType.BuildObject(3,0,tile)) owned_flat = tile;
				} else if (slope != AITile.SLOPE_FLAT && !AITile.IsSteepSlope(slope) && owned_slope == AIMap.TILE_INVALID) {
					if (AIObjectType.BuildObject(3,0,tile)) { owned_slope = tile; slope_code = slope; }
				}
				if (owned_flat != AIMap.TILE_INVALID && owned_slope != AIMap.TILE_INVALID) break;
			}
			if (owned_flat != AIMap.TILE_INVALID && owned_slope != AIMap.TILE_INVALID) break;
		}
		if (owned_flat == AIMap.TILE_INVALID || owned_slope == AIMap.TILE_INVALID) this.Fail("no ordinary flat/sloped owned-land sites");
		AILog.Info("OBJECT_FIXTURE_READY {\"company\":" + AICompany.ResolveCompanyID(AICompany.COMPANY_SELF) +
			",\"hq\":" + headquarters + ",\"hq_x\":" + AIMap.GetTileX(headquarters) + ",\"hq_y\":" + AIMap.GetTileY(headquarters) +
			",\"statue_town\":" + statue_town + ",\"owned_land_flat\":" + owned_flat + ",\"owned_land_flat_x\":" + AIMap.GetTileX(owned_flat) +
			",\"owned_land_flat_y\":" + AIMap.GetTileY(owned_flat) + ",\"owned_land_sloped\":" + owned_slope +
			",\"owned_land_sloped_x\":" + AIMap.GetTileX(owned_slope) + ",\"owned_land_sloped_y\":" + AIMap.GetTileY(owned_slope) +
			",\"owned_land_slope\":" + slope_code + "}");
		while (true) this.Sleep(1000);
	}
}
