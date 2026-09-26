/* SPDX-License-Identifier: GPL-2.0-only */
class RoadCatalogue extends AIController {
	built = false;
	x = 0;
	y = 0;
	function Save() { return {built=this.built}; }
	function Load(version,data) { if (data != null && "built" in data) this.built=data.built; }
	function Tile(dx,dy) { return AIMap.GetTileIndex(this.x+dx,this.y+dy); }
	function Require(ok,label) { if (!ok) throw label+": "+AIError.GetLastErrorString(); }
	function Start();
}

function RoadCatalogue::Start()
{
	if (this.built) while (true) this.Sleep(1000);
	try {
		AILog.Info("ROAD_CATALOGUE_STARTED");
		AIController.SetCommandDelay(1);
		this.Require(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"fund catalogue company");
		AICompany.SetName("OpenTT3D Road Review");
		local found = false;
		for (local y=24; y<AIMap.GetMapSizeY()-24 && !found; y+=8) {
			for (local x=24; x<AIMap.GetMapSizeX()-40; x+=8) {
				local tile=AIMap.GetTileIndex(x,y);
				if (AITile.GetMinHeight(tile)<2 || !AITile.IsBuildableRectangle(tile,34,14)) continue;
				if (!AITile.LevelTiles(tile,AIMap.GetTileIndex(x+33,y+13))) continue;
				this.x=x; this.y=y; found=true; break;
			}
		}
		if (!found) throw "no ordinary buildable road review site";
		AILog.Info("ROAD_CATALOGUE_SITE "+this.x+","+this.y);
		AIRoad.SetCurrentRoadType(0);
		this.Require(AIRoad.BuildRoad(this.Tile(3,3),this.Tile(29,3)),"north road");
		this.Require(AIRoad.BuildRoad(this.Tile(29,3),this.Tile(29,9)),"east road");
		this.Require(AIRoad.BuildRoad(this.Tile(29,9),this.Tile(3,9)),"south road");
		this.Require(AIRoad.BuildRoad(this.Tile(3,9),this.Tile(3,3)),"west road");
		this.Require(AIRoad.BuildRoadDepot(this.Tile(1,6),this.Tile(2,6)),"review depot");
		this.Require(AIRoad.BuildRoad(this.Tile(1,6),this.Tile(3,6)),"depot connection");
		this.Require(AIRoad.BuildDriveThroughRoadStation(this.Tile(9,3),this.Tile(10,3),AIRoad.ROADVEHTYPE_BUS,AIStation.STATION_NEW),"north bus stop");
		this.Require(AIRoad.BuildDriveThroughRoadStation(this.Tile(23,9),this.Tile(22,9),AIRoad.ROADVEHTYPE_BUS,AIStation.STATION_NEW),"south bus stop");
		this.Require(AIRoad.BuildDriveThroughRoadStation(this.Tile(12,3),this.Tile(13,3),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"north truck stop");
		this.Require(AIRoad.BuildDriveThroughRoadStation(this.Tile(20,9),this.Tile(19,9),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"south truck stop");
		local first=AIController.GetSetting("review_first"), last=AIController.GetSetting("review_last");
		local engines=AIEngineList(AIVehicle.VT_ROAD), vehicles=[];
		for (local engine=engines.Begin(); !engines.IsEnd(); engine=engines.Next()) {
			if (engine<first || engine>last) continue;
			local vehicle=AIVehicle.BuildVehicle(this.Tile(1,6),engine);
			this.Require(AIVehicle.IsValidVehicle(vehicle),"build engine "+engine);
			local passenger=AIEngine.GetCargoType(engine)==0;
			this.Require(AIOrder.AppendOrder(vehicle,passenger ? this.Tile(9,3) : this.Tile(12,3),AIOrder.OF_NONE),"north order");
			this.Require(AIOrder.AppendOrder(vehicle,passenger ? this.Tile(23,9) : this.Tile(20,9),AIOrder.OF_NONE),"south order");
			this.Require(AIVehicle.StartStopVehicle(vehicle),"start engine "+engine);
			vehicles.append({engine=engine,vehicle=vehicle,moved=false,peak=0});
			AILog.Info("ROAD_CATALOGUE_VEHICLE engine="+engine+" vehicle="+vehicle);
		}
		if (vehicles.len()==0) throw "no selected road engines available in this climate";
		this.built=true;
		local ready=false;
		for (local tick=0; tick<4000 && !ready; tick+=4) {
			ready=true;
			foreach (entry in vehicles) {
				this.Require(AIVehicle.IsValidVehicle(entry.vehicle),"vehicle remains valid");
				local speed=AIVehicle.GetCurrentSpeed(entry.vehicle);
				if (speed>entry.peak) entry.peak=speed;
				if (!entry.moved && speed>0 && AIMap.DistanceManhattan(AIVehicle.GetLocation(entry.vehicle),this.Tile(1,6))>=4) {
					entry.moved=true;
					AILog.Info("ROAD_CATALOGUE_MOVED engine="+entry.engine+" vehicle="+entry.vehicle);
				}
				ready=ready && entry.moved;
			}
			if (!ready) this.Sleep(4);
		}
		if (!ready) throw "not every selected vehicle left the depot and moved on its route";
		local result="{\"x\":"+this.x+",\"y\":"+this.y+",\"vehicles\":[";
		foreach (index,entry in vehicles) {
			if (index!=0) result+=",";
			result+="{\"engine\":"+entry.engine+",\"vehicle\":"+entry.vehicle+",\"peak_speed\":"+entry.peak+"}";
		}
		AILog.Info("ROAD_CATALOGUE_READY "+result+"]}");
	} catch (error) {
		AILog.Error("ROAD_CATALOGUE_FAILED "+error);
	}
	while (true) this.Sleep(1000);
}
