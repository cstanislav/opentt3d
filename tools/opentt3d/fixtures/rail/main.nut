/* SPDX-License-Identifier: GPL-2.0-only */
/* Presentation fixtures must use ordinary game commands, never edit map bytes or
 * vehicle state. The resulting save can also be opened by unmodified OpenTTD. */
class RailFixture extends AIController {
	x = 0;
	y = 0;
	built = false;
	function Save() { return { built = this.built }; }
	function Load(version, data) { if (data != null && "built" in data) this.built = data.built; }
	function Tile(dx, dy) { return AIMap.GetTileIndex(this.x + dx, this.y + dy); }
	function Require(ok, operation) {
		if (!ok) throw operation + ": " + AIError.GetLastErrorString();
	}
	function Start();
}

function RailFixture::Start()
{
	if (this.built) while (true) this.Sleep(1000);
	try {
		AIController.SetCommandDelay(1);
		this.Require(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()), "fund review company");
		AICompany.SetName("OpenTT3D Rail Review");
		this.Require(AIRail.IsRailTypeAvailable(1), "vanilla electric rail is available");
		AIRail.SetCurrentRailType(1);
		local airport_types = [AIAirport.AT_COMMUTER, AIAirport.AT_LARGE, AIAirport.AT_METROPOLITAN, AIAirport.AT_INTERNATIONAL, AIAirport.AT_INTERCON];
		local airport_type = airport_types[AIController.GetSetting("review_airport")];
		local review_height = airport_type == AIAirport.AT_INTERCON ? 48 : 34;
		local airport_y = review_height - 2 - AIAirport.GetAirportHeight(airport_type);
		if (review_height == 34 && airport_y > 26) airport_y = 26;

		local found = false;
		for (local ty = 8; ty < AIMap.GetMapSizeY() - review_height - 8 && !found; ty += 4) {
			for (local tx = 8; tx < AIMap.GetMapSizeX() - 54; tx += 4) {
				local tile = AIMap.GetTileIndex(tx, ty);
				if (AITile.GetMinHeight(tile) < 2 || !AITile.IsBuildableRectangle(tile, 46, review_height)) continue;
				this.x = tx;
				this.y = ty;
				found = true;
				break;
			}
		}
		if (!found) throw "no unobstructed review site";
		AILog.Info("RAIL_FIXTURE_SITE " + this.x + " " + this.y);
		local level = AITile.GetCornerHeight(this.Tile(0, 0), AITile.CORNER_N);
		/* LevelTiles may report already-level; inspect the actual resulting terrain. */
		AITile.LevelTiles(this.Tile(0, 0), this.Tile(45, review_height-1));
		for (local dy = 1; dy < review_height-2; ++dy) for (local dx = 1; dx < 44; ++dx) {
			if (AITile.GetSlope(this.Tile(dx, dy)) != AITile.SLOPE_FLAT || AITile.GetMinHeight(this.Tile(dx, dy)) != level) {
				throw "review plateau was not fully levelled: " + AIError.GetLastErrorString();
			}
		}

		/* A real raised hill gives both actual portals and hidden moving trains. */
		for (local pass = 0; pass < 2; ++pass) {
			for (local dy = 4; dy <= 13; ++dy) for (local dx = 25; dx <= 30; ++dx) {
				this.Require(AITile.RaiseTile(this.Tile(dx, dy), AITile.SLOPE_N), "raise tunnel hill");
			}
		}
		local tunnel_first = -1, tunnel_last = -1;
		for (local dx = 21; dx < 27; ++dx) {
			local end = AITunnel.GetOtherTunnelEnd(this.Tile(dx, 8));
			if (AIMap.IsValidTile(end) && AIMap.GetTileY(end) == this.y + 8 && AIMap.GetTileX(end) > this.x + dx) {
				this.Require(AITunnel.BuildTunnel(AIVehicle.VT_RAIL, this.Tile(dx, 8)), "build electric tunnel");
				tunnel_first = dx;
				tunnel_last = AIMap.GetTileX(end) - this.x;
				break;
			}
		}
		if (tunnel_first < 0) throw "no tunnel through the authored hill";
		local bridges = AIBridgeList_Length(8);
		if (bridges.IsEmpty()) throw "no eight-tile bridge available";
		this.Require(AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), this.Tile(12, 8), this.Tile(19, 8)), "build electric bridge");

		this.Require(AIRail.BuildRailStation(this.Tile(7, 8), AIRail.RAILTRACK_NE_SW, 4, 4, AIStation.STATION_NEW), "build four-platform hall");
		this.Require(AIRail.BuildRailStation(this.Tile(36, 8), AIRail.RAILTRACK_NE_SW, 1, 3, AIStation.STATION_NEW), "build east terminus");
		this.Require(AIRail.BuildRailDepot(this.Tile(1, 8), this.Tile(2, 8)), "build main depot");
		for (local dx = 2; dx <= 42; ++dx) {
			if ((dx >= 12 && dx <= 19) || (dx >= tunnel_first && dx <= tunnel_last) || (dx >= 7 && dx <= 10) || (dx >= 36 && dx <= 38)) continue;
			this.Require(AIRail.BuildRailTrack(this.Tile(dx, 8), AIRail.RAILTRACK_NE_SW), "connect main line");
		}
		this.Require(AIRail.BuildSignal(this.Tile(5, 8), this.Tile(6, 8), AIRail.SIGNALTYPE_NORMAL_TWOWAY), "build west block signals");
		this.Require(AIRail.BuildSignal(this.Tile(34, 8), this.Tile(35, 8), AIRail.SIGNALTYPE_NORMAL_TWOWAY), "build east block signals");
		AIRoad.SetCurrentRoadType(0);
		this.Require(AIRoad.BuildRoad(this.Tile(4, 5), this.Tile(4, 13)), "build level crossing");
		this.Require(AIRoad.BuildRoad(this.Tile(15, 5), this.Tile(15, 13)), "build road under electric bridge");
		/* Put bus traffic between the two rail stations: the crossing then
		 * changes state on every train journey, not just on its depot departure. */
		local crossing_x = 33;
		this.Require(AIRoad.BuildRoadDepot(this.Tile(crossing_x-1, 13), this.Tile(crossing_x, 13)), "build road depot");
		this.Require(AIRoad.BuildRoad(this.Tile(crossing_x-1, 13), this.Tile(crossing_x, 13)), "connect road depot");
		this.Require(AIRoad.BuildRoad(this.Tile(crossing_x, 4), this.Tile(crossing_x, 14)), "build active crossing review road");
		this.Require(AIRoad.BuildDriveThroughRoadStation(this.Tile(crossing_x, 5), this.Tile(crossing_x, 6), AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW), "build north bus stop");
		this.Require(AIRoad.BuildDriveThroughRoadStation(this.Tile(crossing_x, 12), this.Tile(crossing_x, 11), AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW), "build south bus stop");

		/* Disconnected review tracks cover every curve and all six real signal types. */
		local tracks = [AIRail.RAILTRACK_NE_SW, AIRail.RAILTRACK_NW_SE, AIRail.RAILTRACK_NW_NE,
			AIRail.RAILTRACK_SW_SE, AIRail.RAILTRACK_NW_SW, AIRail.RAILTRACK_NE_SE];
		for (local i = 0; i < 6; ++i) {
			this.Require(AIRail.BuildRailTrack(this.Tile(4 + i * 3, 17), tracks[i]), "build curve review");
			for (local dx = 0; dx < 3; ++dx) this.Require(AIRail.BuildRailTrack(this.Tile(3 + i * 4 + dx, 23), AIRail.RAILTRACK_NE_SW), "build signal review track");
			this.Require(AIRail.BuildSignal(this.Tile(4 + i * 4, 23), this.Tile(5 + i * 4, 23), i), "build signal review aspect");
		}
		this.Require(AIRail.BuildRailDepot(this.Tile(35, 22), this.Tile(35, 23)), "build perpendicular depot");
		this.Require(AIRail.BuildRailTrack(this.Tile(35, 23), AIRail.RAILTRACK_NW_SE), "connect perpendicular depot");
		this.Require(AIRail.BuildRailStation(this.Tile(35, 24), AIRail.RAILTRACK_NW_SE, 3, 4, AIStation.STATION_NEW), "build perpendicular station");
		this.Require(AIRoad.BuildRoad(this.Tile(31, 21), this.Tile(31, 30)), "build road-stop review street");
		this.Require(AIRoad.BuildRoadStation(this.Tile(28, 22), this.Tile(29, 22), AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW), "build bay bus station");
		this.Require(AIRoad.BuildRoad(this.Tile(28, 22), this.Tile(31, 22)), "connect bay bus station");
		this.Require(AIRoad.BuildRoadStation(this.Tile(28, 27), this.Tile(29, 27), AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW), "build bay truck station");
		this.Require(AIRoad.BuildRoad(this.Tile(28, 27), this.Tile(31, 27)), "connect bay truck station");
		this.Require(AIRoad.BuildDriveThroughRoadStation(this.Tile(31, 25), this.Tile(31, 26), AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW), "build drive-through truck station");
		this.Require(AIAirport.BuildAirport(this.Tile(13, airport_y), airport_type, AIStation.STATION_NEW), "build voxel airport review site");
		this.Require(AIAirport.GetNumHangars(this.Tile(13, airport_y)) > 0 && AIAirport.IsHangarTile(AIAirport.GetHangarOfAirport(this.Tile(13, airport_y))), "verify real airport hangar tile");
		this.Require(AIAirport.BuildAirport(this.Tile(23, 26), AIAirport.AT_SMALL, AIStation.STATION_NEW), "build country-airport review site");
		this.Require(AIAirport.IsHangarTile(this.Tile(26, 26)), "verify real small hangar tile");

		local engine = -1;
		local requested_engine = AIController.GetSetting("review_train_engine") - 1;
		local engines = AIEngineList(AIVehicle.VT_RAIL);
		for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
			if (requested_engine >= 0 && e != requested_engine) continue;
			if (!AIEngine.IsWagon(e) && AIEngine.GetRailType(e) == 1) { engine = e; break; }
		}
		if (engine < 0) throw "requested electric locomotive is unavailable: " + requested_engine;
		local train = AIVehicle.BuildVehicle(this.Tile(1, 8), engine);
		this.Require(AIVehicle.IsValidVehicle(train), "build electric locomotive");
		AILog.Info("RAIL_FIXTURE_ENGINE " + engine + " vehicle=" + train);
		this.Require(AIOrder.AppendOrder(train, this.Tile(36, 8), AIOrder.OF_NONE), "order east terminus");
		this.Require(AIOrder.AppendOrder(train, this.Tile(7, 8), AIOrder.OF_NONE), "order west station");
		this.Require(AIVehicle.StartStopVehicle(train), "start review train");
		local bus_engine = -1, buses = AIEngineList(AIVehicle.VT_ROAD);
		for (local e = buses.Begin(); !buses.IsEnd(); e = buses.Next()) {
			if (AIEngine.GetCargoType(e) == 0) { bus_engine = e; break; }
		}
		if (bus_engine < 0) throw "no passenger bus available";
		local bus = AIVehicle.BuildVehicle(this.Tile(crossing_x-1, 13), bus_engine);
		this.Require(AIVehicle.IsValidVehicle(bus), "build crossing review bus");
		this.Require(AIOrder.AppendOrder(bus, this.Tile(crossing_x, 5), AIOrder.OF_NONE), "order north bus stop");
		this.Require(AIOrder.AppendOrder(bus, this.Tile(crossing_x, 12), AIOrder.OF_NONE), "order south bus stop");
		this.Require(AIVehicle.StartStopVehicle(bus), "start review bus");
		/* A second real bus runs below the minimum-height bridge, exercising
		 * the six-unit Cab eye against the actual overhead deck and pillars. */
		this.Require(AIRoad.BuildRoadDepot(this.Tile(14, 13), this.Tile(15, 13)), "build underpass depot");
		this.Require(AIRoad.BuildRoad(this.Tile(14, 13), this.Tile(15, 13)), "connect underpass depot");
		this.Require(AIRoad.BuildDriveThroughRoadStation(this.Tile(15, 5), this.Tile(15, 6), AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW), "build north underpass stop");
		this.Require(AIRoad.BuildDriveThroughRoadStation(this.Tile(15, 12), this.Tile(15, 11), AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW), "build south underpass stop");
		local underpass_bus = AIVehicle.BuildVehicle(this.Tile(14, 13), bus_engine);
		this.Require(AIVehicle.IsValidVehicle(underpass_bus), "build underpass bus");
		this.Require(AIOrder.AppendOrder(underpass_bus, this.Tile(15, 5), AIOrder.OF_NONE), "order north underpass stop");
		this.Require(AIOrder.AppendOrder(underpass_bus, this.Tile(15, 12), AIOrder.OF_NONE), "order south underpass stop");
		this.Require(AIVehicle.StartStopVehicle(underpass_bus), "start underpass bus");
		local aircraft = -1, aircraft_engine = -1;
		local main_airport = this.Tile(13, airport_y), small_airport = this.Tile(23, 26);
		if (AIController.GetSetting("review_aircraft") != 0) {
			local aircraft_engines = AIEngineList(AIVehicle.VT_AIR);
			for (local e = aircraft_engines.Begin(); !aircraft_engines.IsEnd(); e = aircraft_engines.Next()) {
				if (AIEngine.GetPlaneType(e) == AIAirport.PT_SMALL_PLANE && AIEngine.GetCargoType(e) == 0) { aircraft_engine = e; break; }
			}
			if (aircraft_engine < 0) throw "no small passenger aircraft available";
			aircraft = AIVehicle.BuildVehicle(AIAirport.GetHangarOfAirport(main_airport), aircraft_engine);
			this.Require(AIVehicle.IsValidVehicle(aircraft), "build airport review aircraft");
			/* Empty-airport loading can finish between AI polls. Ordinary full-load
			 * orders hold each real boarding stop until observed, then are released. */
			this.Require(AIOrder.AppendOrder(aircraft, small_airport, AIOrder.OF_FULL_LOAD_ANY), "order country airport");
			this.Require(AIOrder.AppendOrder(aircraft, main_airport, AIOrder.OF_FULL_LOAD_ANY), "order main airport");
			this.Require(AIVehicle.StartStopVehicle(aircraft), "start airport review aircraft");
			AILog.Info("AIRCRAFT_FIXTURE_STARTED " + aircraft + " engine=" + aircraft_engine + " stations=" + AIStation.GetStationID(main_airport) + "/" + AIStation.GetStationID(small_airport));
		}
		this.built = true;
		/* Observe an actual journey before accepting the layout. In particular,
		 * disconnected approaches and a wrong-way signal cannot silently pass. */
		local bridge_seen = false, east_seen = false, returned = false, bus_north = false, underpass_seen = false;
		local aircraft_departed = false, aircraft_small_seen = false, aircraft_returned = aircraft < 0, aircraft_peak_speed = 0;
		local journey_limit = aircraft >= 0 ? 4000 : 2000;
		for (local tick = 0; tick < journey_limit && !(returned && bus_north && underpass_seen && aircraft_returned); tick += 4) {
			local location = AIVehicle.GetLocation(train);
			local dx = AIMap.GetTileX(location) - this.x;
			bridge_seen = bridge_seen || (dx >= 12 && dx <= 19);
			east_seen = east_seen || dx >= 36;
			returned = returned || (bridge_seen && east_seen && dx < tunnel_first && dx > 19);
			bus_north = bus_north || AIMap.GetTileY(AIVehicle.GetLocation(bus)) <= this.y + 5;
			underpass_seen = underpass_seen || AIVehicle.GetLocation(underpass_bus) == this.Tile(15, 8);
			if (aircraft >= 0) {
				if (!AIVehicle.IsValidVehicle(aircraft) || AIVehicle.GetState(aircraft) == AIVehicle.VS_CRASHED) throw "review aircraft was lost before completing its route";
				aircraft_departed = aircraft_departed || !AIVehicle.IsInDepot(aircraft);
				local speed = AIVehicle.GetCurrentSpeed(aircraft);
				if (speed > aircraft_peak_speed) aircraft_peak_speed = speed;
				if (tick % 128 == 0) {
					local aircraft_tile = AIVehicle.GetLocation(aircraft);
					AILog.Info("AIRCRAFT_FIXTURE_STATUS tick=" + tick + " state=" + AIVehicle.GetState(aircraft) + " speed=" + speed + " tile=" + AIMap.GetTileX(aircraft_tile) + "," + AIMap.GetTileY(aircraft_tile) + " station=" + AIStation.GetStationID(aircraft_tile));
				}
				if (AIVehicle.GetState(aircraft) == AIVehicle.VS_AT_STATION) {
					local station = AIStation.GetStationID(AIVehicle.GetLocation(aircraft));
					if (aircraft_departed && station == AIStation.GetStationID(small_airport) && !aircraft_small_seen) {
						aircraft_small_seen = true;
						this.Require(AIOrder.SetOrderFlags(aircraft, 0, AIOrder.OF_NONE), "release observed country-airport boarding");
						AILog.Info("AIRCRAFT_FIXTURE_COUNTRY_SERVICE " + aircraft);
					}
					if (aircraft_small_seen && station == AIStation.GetStationID(main_airport) && !aircraft_returned) {
						aircraft_returned = true;
						if (AIController.GetSetting("review_aircraft") == 1) this.Require(AIOrder.SetOrderFlags(aircraft, 1, AIOrder.OF_NONE), "release observed main-airport boarding");
						AILog.Info("AIRCRAFT_FIXTURE_RETURN_SERVICE " + aircraft);
					}
				}
			}
			this.Sleep(4);
		}
		if (!returned) throw "electric locomotive did not cross the bridge/tunnel and return from the terminus";
		if (!bus_north) throw "bus did not leave its depot and traverse the rail crossing";
		if (!underpass_seen) throw "bus did not pass beneath the low bridge";
		if (!aircraft_returned) throw "aircraft did not serve the country airport and return to the main airport";
		if (AIController.GetSetting("review_train_hold") != 0) {
			local positioned = false;
			for (local tick = 0; tick < 2000; tick += 4) {
				local tile = AIVehicle.GetLocation(train);
				local dx = AIMap.GetTileX(tile) - this.x;
				if (dx >= 34 && dx <= 38 && AIMap.GetTileY(tile) == this.y+8) { positioned = true; break; }
				this.Sleep(4);
			}
			if (!positioned) throw "train did not reach the held review terminus";
			if (AIVehicle.GetState(train) != AIVehicle.VS_STOPPED) this.Require(AIVehicle.StartStopVehicle(train), "stop verified review locomotive");
			for (local tick = 0; tick < 160 && AIVehicle.GetCurrentSpeed(train) != 0; tick += 4) this.Sleep(4);
			if (AIVehicle.GetState(train) != AIVehicle.VS_STOPPED || AIVehicle.GetCurrentSpeed(train) != 0) throw "review locomotive did not finish stopping";
			AILog.Info("RAIL_FIXTURE_TRAIN_HELD " + train + " engine=" + engine);
		}
		local aircraft_held = aircraft >= 0 && AIController.GetSetting("review_aircraft") == 2 && AIVehicle.GetState(aircraft) == AIVehicle.VS_AT_STATION;
		AILog.Info("RAIL_FIXTURE_READY {\"x\":" + this.x + ",\"y\":" + this.y + ",\"height\":" + level + ",\"rail_type\":1,\"vehicle\":" + train + ",\"train_engine\":" + engine + ",\"bus\":" + bus + ",\"underpass_bus\":" + underpass_bus + ",\"underpass_verified\":true,\"airport_x\":" + (this.x+13) + ",\"airport_y\":" + (this.y+airport_y) + ",\"airport_type\":" + airport_type + ",\"airport_verified\":true,\"small_airport_x\":" + (this.x+23) + ",\"small_airport_y\":" + (this.y+26) + ",\"small_airport_verified\":true,\"crossing_x\":" + (this.x+crossing_x) + ",\"crossing_y\":" + (this.y+8) + ",\"tunnel_first\":" + tunnel_first + ",\"tunnel_last\":" + tunnel_last + ",\"journey_verified\":true,\"bus_crossing_verified\":true,\"aircraft\":" + aircraft + ",\"aircraft_engine\":" + aircraft_engine + ",\"aircraft_verified\":" + ((aircraft >= 0 && aircraft_returned) ? "true" : "false") + ",\"aircraft_held\":" + (aircraft_held ? "true" : "false") + ",\"aircraft_peak_speed\":" + aircraft_peak_speed + "}");
		while (true) this.Sleep(1000);
	} catch (error) {
		AILog.Error("RAIL_FIXTURE_FAILED " + error);
		while (true) this.Sleep(1000);
	}
}
