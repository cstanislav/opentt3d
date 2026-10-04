/* SPDX-License-Identifier: GPL-2.0-only */
class OriginalRiverSurvey extends AIController {
	function Start() {
		local width = AIMap.GetMapSizeX(), height = AIMap.GetMapSizeY();
		local token = this.GetSetting("survey_token");
		local total = 0;
		for (local y = 0; y < height; y++) {
			for (local x = 0; x < width; x++) {
				local tile = AIMap.GetTileIndex(x,y);
				if (!AITile.IsRiverTile(tile)) continue;
				AILog.Info("RIVER_SURVEY_TILE {\"tile\":" + tile + ",\"x\":" + x + ",\"y\":" + y +
					",\"slope\":" + AITile.GetSlope(tile) + ",\"min_height_levels\":" + AITile.GetMinHeight(tile) +
					",\"public_terrain_type\":" + AITile.GetTerrainType(tile) + ",\"survey_token\":" + token + "}");
				total++;
			}
		}
		AILog.Info("RIVER_SURVEY_READY {\"map_width\":" + width + ",\"map_height\":" + height +
			",\"river_tiles\":" + total + ",\"survey_token\":" + token +
			",\"read_only_tile_queries\":true,\"public_terrain_type_queries\":true}");
		while (true) this.Sleep(1000);
	}
}
