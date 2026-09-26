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
	function CargoService(train, wagon, engine, manifest, west, east, tunnel_first, tunnel_last);
	function FeedProcessor(processor);
}

function TrainCatalogue::Start()
{
	if (this.built) while (true) this.Sleep(1000);
	try {
		AIController.SetCommandDelay(1);
		this.Require(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"fund catalogue company");
		AICompany.SetName("OpenTT3D Train Review");
		local rail_type = AIController.GetSetting("review_rail_type"), requested = AIController.GetSetting("review_engine");
		local service = AIController.GetSetting("review_source") >= 0;
		local clearance = AIController.GetSetting("review_clearance") != 0;
		local curves = AIController.GetSetting("review_curves") != 0;
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
		if (service && wagons.len() != 1) throw "cargo review requires one selected wagon family";
		local height = service ? 20 : clearance ? 14 : 10;
		local found = false;
		for (local y = 8; y < AIMap.GetMapSizeY()-20 && !found; y += 8) {
			for (local x = 8; x < AIMap.GetMapSizeX()-80; x += 8) {
				local tile = AIMap.GetTileIndex(x,y);
				if (AITile.GetMinHeight(tile) < 2 || !AITile.IsBuildableRectangle(tile,72,height)) continue;
				AITile.LevelTiles(tile,AIMap.GetTileIndex(x+71,y+height-1));
				this.x = x; this.y = y; found = true; break;
			}
		}
		if (!found) throw "no buildable train review plateau";
		local tunnel_first = -1, tunnel_last = -1;
		if (clearance) {
			for (local pass = 0; pass < 2; ++pass) {
				for (local dy = 2; dy <= 8; ++dy) for (local dx = 42; dx <= 47; ++dx) {
					this.Require(AITile.RaiseTile(this.Tile(dx,dy),AITile.SLOPE_N),"raise real tunnel hill");
				}
			}
			for (local dx = 38; dx < 44; ++dx) {
				local end = AITunnel.GetOtherTunnelEnd(this.Tile(dx,4));
				if (AIMap.IsValidTile(end) && AIMap.GetTileY(end) == this.y+4 && AIMap.GetTileX(end) > this.x+dx) {
					this.Require(AITunnel.BuildTunnel(AIVehicle.VT_RAIL,this.Tile(dx,4)),"build original railtype tunnel");
					tunnel_first = dx; tunnel_last = AIMap.GetTileX(end)-this.x; break;
				}
			}
			if (tunnel_first < 0) throw "no real tunnel route through the raised hill";
			local bridges = AIBridgeList_Length(8);
			if (bridges.IsEmpty()) throw "no eight-tile bridge available";
			this.Require(AIBridge.BuildBridge(AIVehicle.VT_RAIL,bridges.Begin(),this.Tile(20,4),this.Tile(27,4)),"build original railtype bridge and ramps");
		}
		local depot = this.Tile(1,4), west = this.Tile(5,4), east = this.Tile(57,4);
		this.Require(AIRail.BuildRailDepot(depot,this.Tile(2,4)),"build original rail depot");
		this.Require(AIRail.BuildRailStation(west,AIRail.RAILTRACK_NE_SW,1,8,AIStation.STATION_NEW),"build west terminus");
		local delivery_platforms = service && AIController.GetSetting("review_destination") < 0 ? 5 : 1;
		this.Require(AIRail.BuildRailStation(east,AIRail.RAILTRACK_NE_SW,delivery_platforms,8,AIStation.STATION_NEW),"build east terminus");
		for (local x = 2; x <= 69; ++x) {
			if ((x >= 5 && x < 13) || (x >= 57 && x < 65)) continue;
			if (curves && x >= 29 && x <= 35) continue;
			if (clearance && ((x >= 20 && x <= 27) || (x >= tunnel_first && x <= tunnel_last))) continue;
			this.Require(AIRail.BuildRailTrack(this.Tile(x,4),AIRail.RAILTRACK_NE_SW),"connect review line");
		}
		if (curves) {
			local path = [[28,4],[29,4],[29,5],[29,6],[29,7],[29,8],[30,8],[31,8],[32,8],[33,8],[34,8],[35,8],[35,7],[35,6],[35,5],[35,4],[36,4]];
			for (local i = 1; i < path.len()-1; ++i) {
				this.Require(AIRail.BuildRail(this.Tile(path[i-1][0],path[i-1][1]),this.Tile(path[i][0],path[i][1]),this.Tile(path[i+1][0],path[i+1][1])),"build real connecting curve detour");
			}
		}
		local train = AIVehicle.BuildVehicle(depot,locomotive);
		this.Require(AIVehicle.IsValidVehicle(train),"build selected locomotive");
		local manifest = "", service_wagon = -1;
		foreach (engine in wagons) {
			local count = AIVehicle.GetNumWagons(train);
			local wagon = AIVehicle.BuildVehicle(depot,engine);
			this.Require(AIVehicle.IsValidVehicle(wagon),"build original free wagon");
			service_wagon = wagon;
			this.Require(AIVehicle.MoveWagon(wagon,0,train,count-1),"attach wagon with the ordinary command");
			if (AIVehicle.GetNumWagons(train) != count+1) throw "attachment did not add one original wagon";
			local position = -1;
			for (local i = 0; i <= count; ++i) if (AIVehicle.GetWagonEngineType(train,i) == engine) position = i;
			if (position < 0) throw "attached consist does not contain the requested wagon";
			manifest += (manifest.len() == 0 ? "" : ",")+"{\"engine\":"+engine+",\"vehicle\":"+wagon+",\"position\":"+position+"}";
		}
		if (service) {
			this.built = true;
			this.CargoService(train,service_wagon,wagons[0],manifest,west,east,tunnel_first,tunnel_last);
			while (true) this.Sleep(1000);
		}
		this.Require(AIOrder.AppendOrder(train,east,AIOrder.OF_NONE),"order east station");
		this.Require(AIOrder.AppendOrder(train,west,AIOrder.OF_NONE),"order west station");
		this.Require(AIVehicle.StartStopVehicle(train),"start original consist");
		this.built = true;
		local east_seen = false, returned = false, peak_speed = 0, bridge_seen = false, tunnel_seen = false, curve_seen = false;
		for (local tick = 0; tick < 3200 && !returned; tick += 4) {
			if (!AIVehicle.IsValidVehicle(train) || AIVehicle.GetState(train) == AIVehicle.VS_CRASHED) throw "review train was lost";
			local dx = AIMap.GetTileX(AIVehicle.GetLocation(train))-this.x;
			curve_seen = curve_seen || (curves && dx >= 29 && dx <= 35 && AIMap.GetTileY(AIVehicle.GetLocation(train)) > this.y+4);
			local speed = AIVehicle.GetCurrentSpeed(train);
			if (speed > peak_speed) peak_speed = speed;
			bridge_seen = bridge_seen || (dx >= 20 && dx <= 27);
			tunnel_seen = tunnel_seen || (clearance && dx >= tunnel_first && dx <= tunnel_last);
			east_seen = east_seen || dx >= 57;
			returned = east_seen && dx <= 12;
			this.Sleep(4);
		}
		if (!returned || peak_speed <= 0) throw "the attached consist did not complete both terminus journeys";
		if (clearance && !(bridge_seen && tunnel_seen)) throw "the consist did not traverse the actual bridge and tunnel";
		if (curves && !curve_seen) throw "the consist did not traverse the actual curve detour";
		local held = AIController.GetSetting("review_hold") != 0;
		if (held) {
			this.Require(AIVehicle.StartStopVehicle(train),"hold the verified returning consist");
			for (local tick = 0; tick < 160 && AIVehicle.GetCurrentSpeed(train) != 0; tick += 2) this.Sleep(2);
			if (AIVehicle.GetCurrentSpeed(train) != 0 || AIVehicle.GetState(train) != AIVehicle.VS_STOPPED) throw "review train did not finish its ordinary stop";
		}
		AILog.Info("TRAIN_CATALOGUE_READY {\"x\":"+this.x+",\"y\":"+this.y+",\"rail_type\":"+rail_type+
			",\"locomotive\":"+locomotive+",\"train\":"+train+",\"wagons\":["+manifest+"],\"peak_speed\":"+peak_speed+
			",\"returned\":true,\"held\":"+(held ? "true" : "false")+",\"clearance_route\":"+(clearance ? "true" : "false")+
			",\"curve_route\":"+(curves ? "true" : "false")+",\"curve_seen\":"+(curve_seen ? "true" : "false")+
			",\"bridge_seen\":"+(clearance && bridge_seen ? "true" : "false")+",\"tunnel_seen\":"+(tunnel_seen ? "true" : "false")+
			",\"tunnel_first\":"+tunnel_first+",\"tunnel_last\":"+tunnel_last+"}");
	} catch (error) {
		AILog.Error("TRAIN_CATALOGUE_FAILED "+error);
	}
	while (true) this.Sleep(1000);
}

function TrainCatalogue::CargoService(train, wagon, engine, manifest, west, east, tunnel_first, tunnel_last)
{
	local source = AIController.GetSetting("review_source"), destination = AIController.GetSetting("review_destination");
	local cargo = AIEngine.GetCargoType(engine), produced = AIIndustryType.GetProducedCargo(source);
	this.Require(produced.HasItem(cargo),"wagon carries the original producer's cargo");
	local sites = [[source,6]];
	if (destination >= 0) sites.append([destination,58]);
	foreach (entry in sites) {
		this.Require(AIIndustryType.CanBuildIndustry(entry[0]),"cargo industry can be funded");
		this.Require(AIIndustryType.BuildIndustry(entry[0],this.Tile(entry[1],7)),"fund original cargo industry by the actual rail station");
	}
	if (destination < 0) {
		this.Require(AITown.FoundTown(this.Tile(61,11),AITown.TOWN_SIZE_MEDIUM,true,AITown.ROAD_LAYOUT_3x3,null),"fund an ordinary accepting town by the rail terminus");
	}
	local radius = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
	this.Require(AITile.GetCargoProduction(west,cargo,8,1,radius) > 0,"loading station covers real producing tiles");
	local delivery_platforms = destination < 0 ? 5 : 1;
	for (local tick = 0; tick < 1800 && AITile.GetCargoAcceptance(east,cargo,8,delivery_platforms,radius) < 8; tick += 2) this.Sleep(2);
	local acceptance = AITile.GetCargoAcceptance(east,cargo,8,delivery_platforms,radius);
	if (acceptance < 8) throw "receiving station lacks actual cargo acceptance: "+acceptance;
	local feeder_type = AIController.GetSetting("review_feeder"), feeder = null;
	if (feeder_type >= 0) feeder = this.FeedProcessor(AIIndustry.GetIndustryID(this.Tile(6,7)));
	this.Require(AIOrder.AppendOrder(train,west,AIOrder.OF_FULL_LOAD_ANY),"order original full-load rail pickup");
	this.Require(AIOrder.AppendOrder(train,east,AIOrder.OF_NONE),"order original accepted rail delivery");
	this.Require(AIVehicle.StartStopVehicle(train),"start the original cargo train");
	local full = false, delivered = false, returned = false, peak_speed = 0;
	local clearance = AIController.GetSetting("review_clearance") != 0, bridge_states = 0, tunnel_states = 0;
	local curves = AIController.GetSetting("review_curves") != 0, curve_states = 0;
	local pickup_station = AIStation.GetStationID(west), delivery_station = AIStation.GetStationID(east);
	local capacity = AIVehicle.GetCapacity(train,cargo);
	if (capacity <= 0) throw "attached train has no cargo capacity";
	for (local tick = 0; tick < 6000 && !returned; tick += 2) {
		if (!AIVehicle.IsValidVehicle(train) || AIVehicle.GetState(train) == AIVehicle.VS_CRASHED) throw "cargo train was lost";
		local amount = AIVehicle.GetCargoLoad(train,cargo), speed = AIVehicle.GetCurrentSpeed(train);
		if (curves) {
			local location = AIVehicle.GetLocation(train), dx = AIMap.GetTileX(location)-this.x;
			if (dx >= 29 && dx <= 35 && AIMap.GetTileY(location) > this.y+4) curve_states = curve_states | (amount == capacity ? 1 : delivered && amount == 0 ? 2 : 0);
		}
		if (clearance) {
			local dx = AIMap.GetTileX(AIVehicle.GetLocation(train))-this.x;
			local cargo_state = amount == capacity ? 1 : delivered && amount == 0 ? 2 : 0;
			if (dx >= 20 && dx <= 27) bridge_states = bridge_states | cargo_state;
			if (dx >= tunnel_first && dx <= tunnel_last) tunnel_states = tunnel_states | cargo_state;
		}
		if (feeder != null) {
			local load = AIVehicle.GetCargoLoad(feeder.truck,feeder.cargo);
			if (load > 0) feeder.loaded = true;
			if (feeder.loaded && load == 0 && AIVehicle.GetState(feeder.truck) == AIVehicle.VS_AT_STATION &&
				AIStation.GetStationID(AIVehicle.GetLocation(feeder.truck)) == feeder.station) feeder.delivered = true;
		}
		if (speed > peak_speed) peak_speed = speed;
		local station = AIStation.GetStationID(AIVehicle.GetLocation(train));
		local state = null;
		if (amount == capacity && !full) { full = true; state = "full"; }
		if (full && !delivered && amount == 0 && station == delivery_station && AIVehicle.GetState(train) == AIVehicle.VS_AT_STATION) {
			delivered = true; state = "empty";
		}
		if (delivered && station == pickup_station) returned = true;
		if (state != null) {
			AILog.Info("TRAIN_CARGO_SNAPSHOT {\"state\":\""+state+"\",\"vehicle\":"+wagon+",\"train\":"+train+
				",\"engine\":"+engine+",\"cargo\":"+cargo+",\"amount\":"+amount+",\"capacity\":"+capacity+"}");
			/* Give the external harness a normal-script interval to pause/save. */
			this.Sleep(10);
		}
		if (tick % 256 == 0) AILog.Info("TRAIN_CARGO_STATUS tick="+tick+" load="+amount+" speed="+speed+" station="+station+
			" acceptance="+AITile.GetCargoAcceptance(east,cargo,8,delivery_platforms,radius)+
			" feeder_delivered="+(feeder != null && feeder.delivered ? "true" : "false"));
		this.Sleep(2);
	}
	if (!full || !delivered || !returned || peak_speed <= 0) throw "cargo train did not fully load, deliver and return";
	if (clearance && (bridge_states != 3 || tunnel_states != 3)) throw "cargo train did not cross the actual bridge and tunnel both full and empty";
	if (curves && curve_states != 3) throw "cargo train did not traverse the actual curves both full and empty";
	if (feeder != null && !feeder.delivered) throw "processing input was not observed loading and unloading at its accepting industry";
	local held = AIController.GetSetting("review_hold") != 0;
	if (held) {
		this.Require(AIVehicle.StartStopVehicle(train),"hold returned cargo train");
		for (local tick = 0; tick < 160 && AIVehicle.GetCurrentSpeed(train) != 0; tick += 2) this.Sleep(2);
		if (AIVehicle.GetCurrentSpeed(train) != 0) throw "cargo train did not stop";
	}
	AILog.Info("TRAIN_CATALOGUE_READY {\"x\":"+this.x+",\"y\":"+this.y+",\"rail_type\":"+AIController.GetSetting("review_rail_type")+
		",\"locomotive\":"+AIVehicle.GetEngineType(train)+",\"train\":"+train+",\"wagons\":["+manifest+"],\"peak_speed\":"+peak_speed+
		",\"returned\":true,\"held\":"+(held ? "true" : "false")+",\"cargo\":"+cargo+",\"capacity\":"+capacity+",\"acceptance\":"+acceptance+
		",\"source_type\":"+source+",\"destination_type\":"+destination+",\"feeder_type\":"+feeder_type+
		",\"feeder_delivered\":"+(feeder != null && feeder.delivered ? "true" : "false")+",\"full\":true,\"delivered\":true"+
		",\"clearance_route\":"+(clearance ? "true" : "false")+",\"bridge_seen\":"+(bridge_states == 3 ? "true" : "false")+
		",\"curve_route\":"+(curves ? "true" : "false")+",\"curve_seen\":"+(curve_states == 3 ? "true" : "false")+",\"curve_cargo_states\":"+curve_states+
		",\"tunnel_seen\":"+(tunnel_states == 3 ? "true" : "false")+",\"bridge_cargo_states\":"+bridge_states+",\"tunnel_cargo_states\":"+tunnel_states+
		",\"tunnel_first\":"+tunnel_first+",\"tunnel_last\":"+tunnel_last+"}");
}

function TrainCatalogue::FeedProcessor(processor)
{
	local type = AIController.GetSetting("review_feeder");
	this.Require(AIIndustry.IsValidIndustry(processor),"find the real processing industry");
	this.Require(AIIndustryType.CanBuildIndustry(type),"input producer can be funded");
	this.Require(AIIndustryType.BuildIndustry(type,this.Tile(30,7)),"fund actual processing-input producer");
	local producer = AIIndustry.GetIndustryID(this.Tile(30,7)), cargo = -1;
	local produced = AIIndustryType.GetProducedCargo(type);
	for (local candidate = produced.Begin(); !produced.IsEnd(); candidate = produced.Next()) {
		if (AIIndustry.IsCargoAccepted(processor,candidate) == AIIndustry.CAS_ACCEPTED) { cargo = candidate; break; }
	}
	if (cargo < 0) throw "processor does not accept this producer's original cargo";
	local rows = [];
	foreach (site in [[processor,6],[producer,30]]) {
		local south = -1;
		for (local y = 7; y < 17; ++y) for (local x = site[1]; x < site[1]+8; ++x) {
			if (AIIndustry.GetIndustryID(this.Tile(x,y)) == site[0]) south = y;
		}
		if (south < 0) throw "input-route industry's actual tiles were not found";
		rows.append(south+1);
	}
	AIRoad.SetCurrentRoadType(0);
	local delivery = this.Tile(7,rows[0]), pickup = this.Tile(31,rows[1]);
	this.Require(AIRoad.BuildRoad(this.Tile(5,rows[0]),this.Tile(22,rows[0])),"build processor-side input road");
	if (rows[0] != rows[1]) this.Require(AIRoad.BuildRoad(this.Tile(22,rows[0]),this.Tile(22,rows[1])),"turn toward input producer");
	this.Require(AIRoad.BuildRoad(this.Tile(22,rows[1]),this.Tile(35,rows[1])),"build input producer approach");
	this.Require(AIRoad.BuildDriveThroughRoadStation(delivery,this.Tile(8,rows[0]),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"build processor input stop");
	this.Require(AIRoad.BuildDriveThroughRoadStation(pickup,this.Tile(32,rows[1]),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"build input loading stop");
	local depot = this.Tile(24,rows[1]+1);
	this.Require(AIRoad.BuildRoadDepot(depot,this.Tile(24,rows[1])),"build input-truck depot");
	this.Require(AIRoad.BuildRoad(depot,this.Tile(24,rows[1])),"connect input-truck depot");
	local radius = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
	this.Require(AITile.GetCargoProduction(pickup,cargo,1,1,radius) > 0,"input stop covers original production");
	for (local tick = 0; tick < 1800 && AITile.GetCargoAcceptance(delivery,cargo,1,1,radius) < 8; tick += 2) this.Sleep(2);
	this.Require(AITile.GetCargoAcceptance(delivery,cargo,1,1,radius) >= 8,"processor stop actually accepts the input cargo");
	local engine = -1, engines = AIEngineList(AIVehicle.VT_ROAD);
	for (local candidate = engines.Begin(); !engines.IsEnd(); candidate = engines.Next()) {
		if (AIEngine.GetCargoType(candidate) == cargo) { engine = candidate; break; }
	}
	if (engine < 0) throw "no original input-cargo truck is available";
	local truck = AIVehicle.BuildVehicle(depot,engine);
	this.Require(AIVehicle.IsValidVehicle(truck),"build the processing-input truck");
	this.Require(AIOrder.AppendOrder(truck,pickup,AIOrder.OF_FULL_LOAD_ANY),"order real input loading");
	this.Require(AIOrder.AppendOrder(truck,delivery,AIOrder.OF_NONE),"order accepted processing input");
	this.Require(AIVehicle.StartStopVehicle(truck),"start real processing-input service");
	AILog.Info("TRAIN_FEEDER_READY truck="+truck+" engine="+engine+" cargo="+cargo+" producer="+producer+" processor="+processor);
	return {truck = truck,cargo = cargo,station = AIStation.GetStationID(delivery),loaded = false,delivered = false};
}
