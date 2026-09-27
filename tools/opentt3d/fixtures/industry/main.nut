/* SPDX-License-Identifier: GPL-2.0-only */
/* Use ordinary public commands and calendar dates. Construction stages, map
 * bytes and random state are never set by this presentation fixture. */
class IndustryFixture extends AIController {
	built = false;
	x = 0;
	y = 0;
	function Save() { return { built = this.built }; }
	function Load(version, data) { if (data != null && "built" in data) this.built = data.built; }
	function Require(ok, operation) {
		if (!ok) throw operation + ": " + AIError.GetLastErrorString();
	}
	function Start();
	function Tile(dx, dy) { return AIMap.GetTileIndex(this.x + dx, this.y + dy); }
	function CargoService(industry);
	function SupplyService(industry, delivery, depot, delivery_row);
	function FundTownDestination(type);
	function ConnectRoad(start, finish);
	function TownDeliveryStop(destination, cargo);
	function SouthRoadRow(industry, dx) {
		local south = -1;
		for (local y = 2; y < 10; ++y) for (local x = dx; x < dx + 8; ++x) {
			if (AIIndustry.GetIndustryID(this.Tile(x,y)) == industry) south = y;
		}
		if (south < 0) throw "funded industry's actual tiles were not found";
		return south + 1;
	}
}

function IndustryFixture::Start()
{
	if (this.built) while (true) this.Sleep(1000);
	try {
		AIController.SetCommandDelay(1);
		this.Require(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()), "fund review company");
		AICompany.SetName("OpenTT3D Industry Review");
		local type = AIController.GetSetting("review_industry");
		local coal_service = AIController.GetSetting("review_coal_service") != 0;
		local service = coal_service || AIController.GetSetting("review_cargo_service") != 0;
		if (coal_service && type != 0) throw "the coal-service fixture requires original industry type0";
		this.Require(AIIndustryType.IsValidIndustryType(type) && AIIndustryType.CanBuildIndustry(type), "industry can be funded at a chosen site");
		local industry = -1;
		local water = AIIndustryType.IsBuiltOnWater(type);
		local town_site = AIController.GetSetting("review_town_site") != 0;
		if (town_site && service) throw "town-site source review does not have an open producer road site";
		if (town_site) {
			for (local y = 2; y < AIMap.GetMapSizeY() - 3 && industry < 0; ++y) for (local x = 2; x < AIMap.GetMapSizeX() - 3; ++x) {
				local tile = AIMap.GetTileIndex(x,y);
				if (!AITile.IsHouseTile(tile) || !AIIndustryType.BuildIndustry(type,tile)) continue;
				industry = AIIndustry.GetIndustryID(tile);
				if (!AIIndustry.IsValidIndustry(industry)) throw "funded town industry did not occupy its chosen house site";
				this.x = x - 2; this.y = y - 2;
				break;
			}
		}
		local width = service ? 32 : 8, height = service ? 12 : 8;
		if (service && AIController.GetSetting("review_supply_industry") >= 0 && AIController.GetSetting("review_destination_town_site") == 0) width = 52;
		for (local y = water ? 8 : 32; !town_site && y < AIMap.GetMapSizeY() - height - 8 && industry < 0; y += 8) {
			for (local x = water ? 8 : 32; x < AIMap.GetMapSizeX() - width - 8; x += 8) {
				local tile = AIMap.GetTileIndex(x, y);
				if (water) {
					if (!AITile.IsWaterTile(tile)) continue;
				} else {
					if (AITile.GetMinHeight(tile) < 2 || !AITile.IsBuildableRectangle(tile, width, height)) continue;
					AITile.LevelTiles(tile, AIMap.GetTileIndex(x + width - 1, y + height - 1));
				}
				if (service && AIController.GetSetting("review_depot_directions") != 0) {
					for (local dy = 0; dy < height; ++dy) for (local dx = 0; dx < width; ++dx) {
						local ground = AIMap.GetTileIndex(x + dx, y + dy);
						if (AITile.HasTreeOnTile(ground)) this.Require(AITile.DemolishTile(ground), "clear a tree from the ordinary depot review site");
					}
				}
				if (!AIIndustryType.BuildIndustry(type, AIMap.GetTileIndex(x + 2, y + 2))) continue;
				this.x = x;
				this.y = y;
				local list = AIIndustryList();
				for (local candidate = list.Begin(); !list.IsEnd(); candidate = list.Next()) {
					if (AIIndustry.GetIndustryType(candidate) == type) { industry = candidate; break; }
				}
				break;
			}
		}
		if (!AIIndustry.IsValidIndustry(industry)) throw "no funded industry at a buildable review site";
		this.built = true;
		local location = AIIndustry.GetLocation(industry);
		local start = AIDate.GetCurrentDate();
		/* Four complete tile-loop passes advance a construction stage. These
		 * elapsed-date checkpoints straddle the normal stages; the renderer
		 * separately verifies the actual state in each resulting saved world. */
		foreach (day in [0, 16, 30, 44]) {
			while (AIDate.GetCurrentDate() - start < day) this.Sleep(1);
			if (!AIIndustry.IsValidIndustry(industry)) throw "funded industry disappeared during review";
			AILog.Info("INDUSTRY_FIXTURE_SNAPSHOT {\"industry\":" + industry + ",\"type\":" + type +
				",\"x\":" + AIMap.GetTileX(location) + ",\"y\":" + AIMap.GetTileY(location) +
				",\"day\":" + day + ",\"elapsed_days\":" + (AIDate.GetCurrentDate() - start) +
				",\"script_tick\":" + AIController.GetTick() + "}");
		}
		if (service) {
			/* Give the external harness time to pause/save the last ordinary
			 * construction checkpoint before issuing more public commands. */
			this.Sleep(10);
			this.CargoService(industry);
		}
	} catch (error) {
		AILog.Error("INDUSTRY_FIXTURE_FAILED " + error);
	}
	while (true) this.Sleep(1000);
}

function IndustryFixture::FundTownDestination(type)
{
	local sites = AITileList();
	for (local tile = 0; tile < AIMap.GetMapSize(); ++tile) if (AITile.IsHouseTile(tile)) sites.AddItem(tile, AIMap.DistanceManhattan(tile,this.Tile(2,2)));
	sites.Sort(AIList.SORT_BY_VALUE, true);
	for (local tile = sites.Begin(); !sites.IsEnd(); tile = sites.Next()) {
		if (!AIIndustryType.BuildIndustry(type,tile)) continue;
		local destination = AIIndustry.GetIndustryID(tile);
		if (!AIIndustry.IsValidIndustry(destination)) throw "funded town destination did not occupy its house site";
		AILog.Info("INDUSTRY_TOWN_DESTINATION type="+type+" tile="+AIMap.GetTileX(tile)+","+AIMap.GetTileY(tile));
		return destination;
	}
	throw "no legal existing-house site for the accepting industry";
}

function IndustryFixture::ConnectRoad(start, finish)
{
	/* Public test commands search buildable edges; actual construction then uses
	 * those same ordinary commands. No map bytes, ownership or RNG are edited. */
	local previous = {}, queue = [start];
	previous[start] <- start;
	for (local cursor = 0; cursor < queue.len() && !(finish in previous); ++cursor) {
		local tile = queue[cursor], x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile);
		foreach (step in [[1,0],[-1,0],[0,1],[0,-1]]) {
			local nx = x+step[0], ny = y+step[1];
			if (nx < 1 || ny < 1 || nx >= AIMap.GetMapSizeX()-1 || ny >= AIMap.GetMapSizeY()-1) continue;
			local next = AIMap.GetTileIndex(nx,ny);
			if (next in previous || AITile.IsWaterTile(next) || AITile.IsHouseTile(next) || AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(next))) continue;
			local allowed = AIRoad.AreRoadTilesConnected(tile,next);
			if (!allowed) { local test = AITestMode(); allowed = AIRoad.BuildRoad(tile,next); }
			if (!allowed) continue;
			previous[next] <- tile;
			queue.append(next);
		}
	}
	if (!(finish in previous)) throw "no public-command road route to the town destination";
	local path = [finish];
	while (path.top() != start) path.append(previous[path.top()]);
	for (local i = path.len()-1; i > 0; --i) if (!AIRoad.AreRoadTilesConnected(path[i],path[i-1])) {
		this.Require(AIRoad.BuildRoad(path[i],path[i-1]), "connect a town-service road edge");
	}
	AILog.Info("INDUSTRY_TOWN_ROAD edges="+(path.len()-1));
}

function IndustryFixture::TownDeliveryStop(destination, cargo)
{
	local centre = AIIndustry.GetLocation(destination), radius = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
	local x = AIMap.GetTileX(centre), y = AIMap.GetTileY(centre);
	/* Let the newly funded bank complete through the normal calendar/tile loop. */
	local start = AIDate.GetCurrentDate();
	while (AIDate.GetCurrentDate()-start < 44) this.Sleep(2);
	for (local dy = -radius; dy <= radius+1; ++dy) for (local dx = -radius; dx <= radius+1; ++dx) {
		if (x+dx < 1 || y+dy < 1 || x+dx >= AIMap.GetMapSizeX()-1 || y+dy >= AIMap.GetMapSizeY()-1) continue;
		local tile = AIMap.GetTileIndex(x+dx,y+dy);
		if (!AIRoad.IsRoadTile(tile) || AITile.GetCargoAcceptance(tile,cargo,1,1,radius) < 8) continue;
		foreach (front in [tile+1,tile+AIMap.GetMapSizeX()]) {
			local allowed;
			{ local test = AITestMode(); allowed = AIRoad.BuildDriveThroughRoadStation(tile,front,AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW); }
			if (!allowed) continue;
			this.Require(AIRoad.BuildDriveThroughRoadStation(tile,front,AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW), "build the bank's actual accepting road stop");
			return tile;
		}
	}
	throw "no accepting public-road stop beside the town destination";
}

function IndustryFixture::CargoService(industry)
{
	local source_type = AIIndustry.GetIndustryType(industry), destination_type = AIController.GetSetting("review_destination");
	this.Require(AIIndustryType.CanBuildIndustry(destination_type), "cargo destination can be funded");
	local town_destination = AIController.GetSetting("review_destination_town_site") != 0;
	if (town_destination) this.FundTownDestination(destination_type);
	else this.Require(AIIndustryType.BuildIndustry(destination_type, this.Tile(22,2)), "fund cargo destination");
	local destination = -1, industries = AIIndustryList();
	for (local candidate = industries.Begin(); !industries.IsEnd(); candidate = industries.Next()) {
		if (AIIndustry.GetIndustryType(candidate) == destination_type) { destination = candidate; break; }
	}
	if (!AIIndustry.IsValidIndustry(destination)) throw "funded cargo destination was not found";
	local produced = AIIndustryType.GetProducedCargo(source_type);
	if (produced.IsEmpty()) throw "source industry has no produced cargo";
	local cargo = produced.Begin();
	local requested = AIController.GetSetting("review_truck_engine");
	if (requested >= 0) {
		this.Require(AIEngine.IsValidEngine(requested), "requested original cargo truck is available");
		cargo = AIEngine.GetCargoType(requested);
		if (!produced.HasItem(cargo)) throw "requested truck does not carry the source industry's real cargo";
	}
	this.Require(AIIndustry.IsCargoAccepted(destination, cargo) == AIIndustry.CAS_ACCEPTED, "destination accepts the source industry's cargo");
	local pickup_row = this.SouthRoadRow(industry,2);
	AIRoad.SetCurrentRoadType(0);
	this.Require(AIRoad.BuildRoad(this.Tile(1,pickup_row), this.Tile(17,pickup_row)), "build producer-side service road");
	local delivery_row = town_destination ? pickup_row : this.SouthRoadRow(destination,22);
	local pickup = this.Tile(4,pickup_row), delivery = town_destination ? this.TownDeliveryStop(destination,cargo) : this.Tile(23,delivery_row), depot = this.Tile(3,pickup_row+1);
	if (town_destination) this.ConnectRoad(this.Tile(17,pickup_row),delivery);
	else {
		if (pickup_row != delivery_row) this.Require(AIRoad.BuildRoad(this.Tile(17,pickup_row), this.Tile(17,delivery_row)), "turn toward the accepting industry tiles");
		this.Require(AIRoad.BuildRoad(this.Tile(17,delivery_row), this.Tile(29,delivery_row)), "build destination approach");
		this.Require(AIRoad.BuildDriveThroughRoadStation(delivery, this.Tile(24,delivery_row), AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW), "build cargo delivery stop");
	}
	this.Require(AIRoad.BuildDriveThroughRoadStation(pickup, this.Tile(5,pickup_row), AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW), "build cargo loading stop");
	this.Require(AIRoad.BuildRoadDepot(depot, this.Tile(3,pickup_row)), "build cargo-truck depot");
	this.Require(AIRoad.BuildRoad(depot, this.Tile(3,pickup_row)), "connect cargo-truck depot");
	if (AIController.GetSetting("review_depot_directions") != 0) {
		local exits = [[9,9,10,9],[14,9,14,10],[19,9,18,9]];
		foreach (exit in exits) {
			local site = this.Tile(exit[0],exit[1]), front = this.Tile(exit[2],exit[3]);
			this.Require(AIRoad.BuildRoadDepot(site,front), "build another original road-depot exit");
			this.Require(AIRoad.GetRoadDepotFrontTile(site) == front, "verify actual road-depot orientation");
			this.Require(AIRoad.BuildRoad(site,front), "connect review depot mouth");
		}
		this.Require(AIRoad.BuildRoad(this.Tile(10,9),this.Tile(10,pickup_row)), "connect +X depot approach");
		this.Require(AIRoad.BuildRoad(this.Tile(14,10),this.Tile(16,10)), "connect +Y depot approach");
		this.Require(AIRoad.BuildRoad(this.Tile(16,10),this.Tile(16,pickup_row)), "join +Y approach to service road");
		this.Require(AIRoad.BuildRoad(this.Tile(18,9),this.Tile(18,delivery_row)), "connect -X depot approach");
		this.Require(AIRoad.GetRoadDepotFrontTile(depot) == this.Tile(3,pickup_row), "verify original -Y depot orientation");
		AILog.Info("INDUSTRY_DEPOT_DIRECTIONS_READY {\"directions\":[0,1,2,3],\"site_x\":" + this.x + ",\"site_y\":" + this.y + "}");
	}
	local radius = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
	this.Require(AITile.GetCargoProduction(pickup, cargo, 1, 1, radius) > 0, "loading stop covers actual producing industry tiles");
	for (local tick = 0; tick < 1200 && AITile.GetCargoAcceptance(delivery, cargo, 1, 1, radius) < 8; tick += 2) this.Sleep(2);
	local acceptance = AITile.GetCargoAcceptance(delivery, cargo, 1, 1, radius);
	if (acceptance < 8) throw "delivery stop does not cover enough actual accepting industry tiles: " + acceptance;
	AILog.Info("INDUSTRY_SERVICE_ACCEPTANCE " + acceptance + " radius=" + radius);
	local engine = -1, engines = AIEngineList(AIVehicle.VT_ROAD);
	for (local candidate = engines.Begin(); !engines.IsEnd(); candidate = engines.Next()) {
		if (AIEngine.GetCargoType(candidate) == cargo && (requested < 0 || candidate == requested)) { engine = candidate; break; }
	}
	if (engine < 0) throw "no available matching vanilla cargo truck (requested="+requested+")";
	local truck = AIVehicle.BuildVehicle(depot, engine);
	this.Require(AIVehicle.IsValidVehicle(truck), "build cargo truck");
	this.Require(AIOrder.AppendOrder(truck, pickup, AIOrder.OF_FULL_LOAD_ANY), "order ordinary full-load pickup");
	this.Require(AIOrder.AppendOrder(truck, delivery, AIOrder.OF_NONE), "order normal accepted-cargo delivery");
	if (AIController.GetSetting("review_depot_directions") != 0) {
		this.Require(AIOrder.AppendOrder(truck, depot, AIOrder.OF_NONE), "order ordinary depot maintenance on each delivery loop");
	}
	this.Require(AIVehicle.StartStopVehicle(truck), "start cargo truck");
	local supply = AIController.GetSetting("review_supply_industry") >= 0 ? this.SupplyService(industry,pickup,depot,pickup_row) : null;
	local loaded = false, delivered = false, returned = false, peak_load = 0, peak_speed = 0;
	local full_reported = false, empty_reported = false;
	local pickup_station = AIStation.GetStationID(pickup), delivery_station = AIStation.GetStationID(delivery);
	local observed_ticks = 0, service_ticks = AIController.GetSetting("review_service_ticks");
	for (local tick = 0; tick < service_ticks && (!returned || (supply != null && !supply.returned)); tick += 2) {
		observed_ticks = tick;
		if (supply != null && !supply.returned) {
			if (!AIVehicle.IsValidVehicle(supply.truck) || AIVehicle.GetState(supply.truck) == AIVehicle.VS_CRASHED) throw "input truck was lost during its route";
			local input_load = AIVehicle.GetCargoLoad(supply.truck,supply.cargo), input_speed = AIVehicle.GetCurrentSpeed(supply.truck);
			if (input_load > supply.peak_load) supply.peak_load = input_load;
			if (input_speed > supply.peak_speed) supply.peak_speed = input_speed;
			if (AIVehicle.GetState(supply.truck) == AIVehicle.VS_AT_STATION) {
				local station = AIStation.GetStationID(AIVehicle.GetLocation(supply.truck));
				if (station == supply.pickup_station && input_load > 0) supply.loaded = true;
				if (station == supply.delivery_station && supply.loaded && input_load == 0) supply.delivered = true;
				if (station == supply.pickup_station && supply.delivered) supply.returned = true;
			}
			if (tick % 128 == 0) AILog.Info("INDUSTRY_SUPPLY_STATUS tick="+tick+" load="+input_load+" speed="+input_speed);
			if (supply.returned) {
				if (supply.peak_load != supply.capacity || supply.peak_speed == 0) throw "input truck did not complete an ordinary full-load service";
				AILog.Info("INDUSTRY_SUPPLY_READY {\"industry\":"+supply.industry+",\"destination\":"+industry+
					",\"source_type\":"+supply.type+",\"truck\":"+supply.truck+",\"engine\":"+supply.engine+",\"cargo\":"+supply.cargo+
					",\"acceptance\":"+supply.acceptance+",\"capacity\":"+supply.capacity+",\"peak_load\":"+supply.peak_load+
					",\"peak_speed\":"+supply.peak_speed+",\"observed_ticks\":"+tick+",\"returned\":true}");
			}
		}
		if (!AIVehicle.IsValidVehicle(truck) || AIVehicle.GetState(truck) == AIVehicle.VS_CRASHED) throw "cargo truck was lost during its route";
		local load = AIVehicle.GetCargoLoad(truck, cargo), speed = AIVehicle.GetCurrentSpeed(truck);
		if (load > peak_load) peak_load = load;
		if (speed > peak_speed) peak_speed = speed;
		if (tick % 128 == 0) AILog.Info("INDUSTRY_SERVICE_STATUS tick=" + tick + " state=" + AIVehicle.GetState(truck) + " load=" + load + " speed=" + speed + " station=" + AIStation.GetStationID(AIVehicle.GetLocation(truck)));
		if (AIVehicle.GetState(truck) == AIVehicle.VS_AT_STATION) {
			local station = AIStation.GetStationID(AIVehicle.GetLocation(truck));
			if (station == pickup_station && load > 0 && !loaded) {
				loaded = true;
				AILog.Info("INDUSTRY_SERVICE_LOADED " + truck);
			}
			if (station == delivery_station && loaded && load == 0 && !delivered) {
				delivered = true;
				AILog.Info("INDUSTRY_SERVICE_DELIVERED " + truck);
			}
			if (station == pickup_station && delivered) returned = true;
		}
		local capacity = AIVehicle.GetCapacity(truck, cargo);
		local state = null;
		if (!full_reported && capacity > 0 && load == capacity) { full_reported = true; state = "full"; }
		if (!empty_reported && delivered && load == 0) { empty_reported = true; state = "empty"; }
		if (state != null) AILog.Info("INDUSTRY_CARGO_SNAPSHOT {\"state\":\"" + state + "\",\"vehicle\":" + truck +
			",\"engine\":" + engine + ",\"cargo\":" + cargo + ",\"amount\":" + load + ",\"capacity\":" + capacity + "}");
		this.Sleep(2);
	}
	if (!loaded || !delivered || !returned || peak_speed == 0) throw "cargo truck did not load, deliver and return";
	if (supply != null && !supply.returned) throw "input truck did not load, deliver and return";
	if (AIController.GetSetting("review_depot_directions") != 0) {
		this.Require(AIVehicle.SendVehicleToDepot(truck), "send the working cargo truck to its actual depot");
		for (local tick = 0; tick < 600 && !AIVehicle.IsStoppedInDepot(truck); tick += 2) this.Sleep(2);
		if (!AIVehicle.IsStoppedInDepot(truck)) throw "cargo truck did not enter and stop inside its depot";
		local actual_depot = AIVehicle.GetLocation(truck);
		this.Require(AIRoad.IsRoadDepotTile(actual_depot), "truck stopped in an actual road depot");
		this.Require(AIVehicle.StartStopVehicle(truck), "resume the original cargo-service orders");
		for (local tick = 0; tick < 160 && AIVehicle.IsInDepot(truck); tick += 2) this.Sleep(2);
		if (AIVehicle.IsInDepot(truck)) throw "cargo truck did not leave its depot again";
		AILog.Info("INDUSTRY_DEPOT_SERVICE_VERIFIED vehicle=" + truck + " depot=" + AIMap.GetTileX(actual_depot) + "," + AIMap.GetTileY(actual_depot));
	}
	AILog.Info("INDUSTRY_SERVICE_READY {\"industry\":" + industry + ",\"destination\":" + destination +
		",\"source_type\":" + source_type + ",\"destination_type\":" + destination_type +
		",\"truck\":" + truck + ",\"engine\":" + engine + ",\"cargo\":" + cargo +
		",\"pickup_station\":" + pickup_station + ",\"delivery_station\":" + delivery_station +
		",\"acceptance\":" + acceptance + ",\"peak_load\":" + peak_load + ",\"peak_speed\":" + peak_speed + ",\"observed_ticks\":" + observed_ticks + ",\"returned\":true}");
}

/** Fund a real input producer and deliver its accepted cargo through ordinary orders. */
function IndustryFixture::SupplyService(industry, delivery, depot, delivery_row)
{
	local type = AIController.GetSetting("review_supply_industry");
	if (type == AIIndustry.GetIndustryType(industry) || type == AIController.GetSetting("review_destination")) throw "input industry must be a distinct third type";
	this.Require(AIIndustryType.CanBuildIndustry(type), "input industry can be funded");
	/* Original conflicting industry types must be more than14 tiles apart. */
	local dx = AIController.GetSetting("review_destination_town_site") != 0 ? 22 : 42;
	this.Require(AIIndustryType.BuildIndustry(type,this.Tile(dx,2)), "fund input industry on the ordinary review site");
	local supplier = -1, industries = AIIndustryList();
	for (local candidate = industries.Begin(); !industries.IsEnd(); candidate = industries.Next()) {
		if (AIIndustry.GetIndustryType(candidate) == type) { supplier = candidate; break; }
	}
	if (!AIIndustry.IsValidIndustry(supplier)) throw "funded input industry was not found";
	local cargo = -1, produced = AIIndustryType.GetProducedCargo(type);
	for (local candidate = produced.Begin(); !produced.IsEnd(); candidate = produced.Next()) {
		if (AIIndustry.IsCargoAccepted(industry,candidate) == AIIndustry.CAS_ACCEPTED) { cargo = candidate; break; }
	}
	if (cargo < 0) throw "input industry supplies no accepted cargo to the reviewed producer";
	local row = this.SouthRoadRow(supplier,dx), pickup = this.Tile(dx+2,row);
	this.Require(AIRoad.BuildRoad(this.Tile(17,row),this.Tile(dx+7,row)), "build input loading approach");
	if (row != delivery_row) {
		this.Require(AIRoad.BuildRoad(this.Tile(17,row),this.Tile(17,delivery_row)), "join input road to producer route");
	}
	this.Require(AIRoad.BuildDriveThroughRoadStation(pickup,this.Tile(dx+3,row),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW), "build actual input loading stop");
	local radius = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
	for (local tick = 0; tick < 1200 && AITile.GetCargoProduction(pickup,cargo,1,1,radius) == 0; tick += 2) this.Sleep(2);
	this.Require(AITile.GetCargoProduction(pickup,cargo,1,1,radius) > 0, "input loading stop covers real production");
	local acceptance = AITile.GetCargoAcceptance(delivery,cargo,1,1,radius);
	if (acceptance < 8) throw "producer stop does not cover enough actual input acceptance";
	local engine = -1, engines = AIEngineList(AIVehicle.VT_ROAD);
	for (local candidate = engines.Begin(); !engines.IsEnd(); candidate = engines.Next()) {
		if (AIEngine.GetCargoType(candidate) == cargo) { engine = candidate; break; }
	}
	if (engine < 0) throw "no available original truck for input cargo";
	local truck = AIVehicle.BuildVehicle(depot,engine);
	this.Require(AIVehicle.IsValidVehicle(truck), "build real input truck");
	this.Require(AIOrder.AppendOrder(truck,pickup,AIOrder.OF_FULL_LOAD_ANY), "order ordinary input full-load pickup");
	this.Require(AIOrder.AppendOrder(truck,delivery,AIOrder.OF_NONE), "order normal accepted-input delivery");
	this.Require(AIVehicle.StartStopVehicle(truck), "start input truck");
	return {industry=supplier,type=type,cargo=cargo,engine=engine,truck=truck,acceptance=acceptance,
		capacity=AIVehicle.GetCapacity(truck,cargo),pickup_station=AIStation.GetStationID(pickup),delivery_station=AIStation.GetStationID(delivery),
		loaded=false,delivered=false,returned=false,peak_load=0,peak_speed=0};
}
