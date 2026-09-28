/* SPDX-License-Identifier: GPL-2.0-only */
/* Road work starts through the ordinary town action. Effect creation, RNG,
 * movement, sprite selection and deletion remain the original simulation. */
class Roadworks extends AIController {
	built = false;
	function Save() { return { built = this.built }; }
	function Load(version, data) { if (data != null && "built" in data) this.built = data.built; }
	function Start() {
		if (!this.built) {
			try {
				AIController.SetCommandDelay(1);
				if (!AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount())) throw AIError.GetLastErrorString();
				AICompany.SetName("OpenTT3D Roadworks Review");
				local towns = AITownList();
				towns.Valuate(AITown.GetPopulation);
				towns.Sort(AIList.SORT_BY_VALUE, false);
				foreach (town, population in towns) {
					if (!AITown.PerformTownAction(town, AITown.TOWN_ACTION_ROAD_REBUILD)) continue;
					local tile = AITown.GetLocation(town);
					this.built = true;
					AILog.Info("ROADWORKS_READY {\"town\":" + town + ",\"x\":" + AIMap.GetTileX(tile) + ",\"y\":" + AIMap.GetTileY(tile) + ",\"population\":" + population + "}");
					break;
				}
				if (!this.built) throw "No original town accepted road rebuilding";
			} catch (error) { AILog.Error("ROADWORKS_FAILED " + error); }
		}
		while (true) this.Sleep(1000);
	}
}
