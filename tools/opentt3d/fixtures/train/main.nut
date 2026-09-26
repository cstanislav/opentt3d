/* SPDX-License-Identifier: GPL-2.0-only */
/* Ordinary construction, attachment, orders and observation only. */
class TrainCatalogue extends AIController {
	built = false;
	x = 0;
	y = 0;
	function Save() { return {built = this.built}; }
	function Load(version, data) { if (data != null && "built" in data) this.built = data.built; }
	function Tile(dx,dy) { return AIMap.GetTileIndex(this.x+dx,this.y+dy); }
	function Require(ok,operation) { if (!ok) throw operation+": "+AIError.GetLastErrorString(); }
	function Start();
}

function TrainCatalogue::Start()
{
	if (this.built) while (true) this.Sleep(1000);
	try {
		AIController.SetCommandDelay(1);
		this.Require(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"fund catalogue company");
		AICompany.SetName("OpenTT3D Train Review");
		local rail_type = AIController.GetSetting("review_rail_type"), requested = AIController.GetSetting("review_engine");
		this.Require(AIRail.IsRailTypeAvailable(rail_type),"selected railtype is available");
		AIRail.SetCurrentRailType(rail_type);
		local engines = AIEngineList(AIVehicle.VT_RAIL), locomotive = -1, power = -1, wagons = [];
		for (local engine = engines.Begin(); !engines.IsEnd(); engine = engines.Next()) {
			if (AIEngine.IsWagon(engine)) {
				if (engine >= AIController.GetSetting("review_first") && engine <= AIController.GetSetting("review_last") && AIEngine.CanRunOnRail(engine,rail_type)) wagons.append(engine);
			} else if (AIEngine.GetRailType(engine) == rail_type && (requested < 0 || engine == requested) && AIEngine.GetPower(engine) > power) {
				locomotive = engine; power = AIEngine.GetPower(engine);
			}
		}
		if (locomotive < 0 || wagons.len() == 0) throw "no selected original locomotive/wagons available for this climate and railtype";
		local found = false;
		for (local y = 8; y < AIMap.GetMapSizeY()-20 && !found; y += 8) {
			for (local x = 8; x < AIMap.GetMapSizeX()-80; x += 8) {
				local tile = AIMap.GetTileIndex(x,y);
				if (AITile.GetMinHeight(tile) < 2 || !AITile.IsBuildableRectangle(tile,72,10)) continue;
				AITile.LevelTiles(tile,AIMap.GetTileIndex(x+71,y+9));
				this.x = x; this.y = y; found = true; break;
			}
		}
		if (!found) throw "no buildable train review plateau";
		local depot = this.Tile(1,4), west = this.Tile(5,4), east = this.Tile(57,4);
		this.Require(AIRail.BuildRailDepot(depot,this.Tile(2,4)),"build original rail depot");
		this.Require(AIRail.BuildRailStation(west,AIRail.RAILTRACK_NE_SW,1,8,AIStation.STATION_NEW),"build west terminus");
		this.Require(AIRail.BuildRailStation(east,AIRail.RAILTRACK_NE_SW,1,8,AIStation.STATION_NEW),"build east terminus");
		for (local x = 2; x <= 69; ++x) {
			if ((x >= 5 && x < 13) || (x >= 57 && x < 65)) continue;
			this.Require(AIRail.BuildRailTrack(this.Tile(x,4),AIRail.RAILTRACK_NE_SW),"connect review line");
		}
		local train = AIVehicle.BuildVehicle(depot,locomotive);
		this.Require(AIVehicle.IsValidVehicle(train),"build selected locomotive");
		local manifest = "";
		foreach (engine in wagons) {
			local count = AIVehicle.GetNumWagons(train);
			local wagon = AIVehicle.BuildVehicle(depot,engine);
			this.Require(AIVehicle.IsValidVehicle(wagon),"build original free wagon");
			this.Require(AIVehicle.MoveWagon(wagon,0,train,count-1),"attach wagon with the ordinary command");
			if (AIVehicle.GetNumWagons(train) != count+1) throw "attachment did not add one original wagon";
			local position = -1;
			for (local i = 0; i <= count; ++i) if (AIVehicle.GetWagonEngineType(train,i) == engine) position = i;
			if (position < 0) throw "attached consist does not contain the requested wagon";
			manifest += (manifest.len() == 0 ? "" : ",")+"{\"engine\":"+engine+",\"vehicle\":"+wagon+",\"position\":"+position+"}";
		}
		this.Require(AIOrder.AppendOrder(train,east,AIOrder.OF_NONE),"order east station");
		this.Require(AIOrder.AppendOrder(train,west,AIOrder.OF_NONE),"order west station");
		this.Require(AIVehicle.StartStopVehicle(train),"start original consist");
		this.built = true;
		local east_seen = false, returned = false, peak_speed = 0;
		for (local tick = 0; tick < 3200 && !returned; tick += 4) {
			if (!AIVehicle.IsValidVehicle(train) || AIVehicle.GetState(train) == AIVehicle.VS_CRASHED) throw "review train was lost";
			local dx = AIMap.GetTileX(AIVehicle.GetLocation(train))-this.x;
			local speed = AIVehicle.GetCurrentSpeed(train);
			if (speed > peak_speed) peak_speed = speed;
			east_seen = east_seen || dx >= 57;
			returned = east_seen && dx <= 12;
			this.Sleep(4);
		}
		if (!returned || peak_speed <= 0) throw "the attached consist did not complete both terminus journeys";
		local held = AIController.GetSetting("review_hold") != 0;
		if (held) {
			this.Require(AIVehicle.StartStopVehicle(train),"hold the verified returning consist");
			for (local tick = 0; tick < 160 && AIVehicle.GetCurrentSpeed(train) != 0; tick += 2) this.Sleep(2);
			if (AIVehicle.GetCurrentSpeed(train) != 0 || AIVehicle.GetState(train) != AIVehicle.VS_STOPPED) throw "review train did not finish its ordinary stop";
		}
		AILog.Info("TRAIN_CATALOGUE_READY {\"x\":"+this.x+",\"y\":"+this.y+",\"rail_type\":"+rail_type+
			",\"locomotive\":"+locomotive+",\"train\":"+train+",\"wagons\":["+manifest+"],\"peak_speed\":"+peak_speed+
			",\"returned\":true,\"held\":"+(held ? "true" : "false")+"}");
	} catch (error) {
		AILog.Error("TRAIN_CATALOGUE_FAILED "+error);
	}
	while (true) this.Sleep(1000);
}
