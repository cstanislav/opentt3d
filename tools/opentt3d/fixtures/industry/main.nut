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
		local width = service ? 32 : 8, height = service ? 12 : 8;
		for (local y = water ? 8 : 32; y < AIMap.GetMapSizeY() - height - 8 && industry < 0; y += 8) {
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

function IndustryFixture::CargoService(industry)
{
	local source_type = AIIndustry.GetIndustryType(industry), destination_type = AIController.GetSetting("review_destination");
	this.Require(AIIndustryType.CanBuildIndustry(destination_type), "cargo destination can be funded");
	this.Require(AIIndustryType.BuildIndustry(destination_type, this.Tile(22,2)), "fund cargo destination");
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
	local pickup_row = this.SouthRoadRow(industry,2), delivery_row = this.SouthRoadRow(destination,22);
	AIRoad.SetCurrentRoadType(0);
	this.Require(AIRoad.BuildRoad(this.Tile(1,pickup_row), this.Tile(17,pickup_row)), "build producer-side service road");
	if (pickup_row != delivery_row) this.Require(AIRoad.BuildRoad(this.Tile(17,pickup_row), this.Tile(17,delivery_row)), "turn toward the accepting industry tiles");
	this.Require(AIRoad.BuildRoad(this.Tile(17,delivery_row), this.Tile(29,delivery_row)), "build destination approach");
	local pickup = this.Tile(4,pickup_row), delivery = this.Tile(23,delivery_row), depot = this.Tile(3,pickup_row+1);
	this.Require(AIRoad.BuildDriveThroughRoadStation(pickup, this.Tile(5,pickup_row), AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW), "build cargo loading stop");
	this.Require(AIRoad.BuildDriveThroughRoadStation(delivery, this.Tile(24,delivery_row), AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW), "build cargo delivery stop");
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
	local loaded = false, delivered = false, returned = false, peak_load = 0, peak_speed = 0;
	local full_reported = false, empty_reported = false;
	local pickup_station = AIStation.GetStationID(pickup), delivery_station = AIStation.GetStationID(delivery);
	for (local tick = 0; tick < 2400 && !returned; tick += 2) {
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
		",\"acceptance\":" + acceptance + ",\"peak_load\":" + peak_load + ",\"peak_speed\":" + peak_speed + ",\"returned\":true}");
}
