/* SPDX-License-Identifier: GPL-2.0-only */
class AircraftCatalogue extends AIController {
	built = false;
	release = null;
	function Save() { return {built = this.built, release = this.release}; }
	function Load(version, data) {
		if (data != null && "built" in data) this.built = data.built;
		if (data != null && "release" in data) this.release = data.release;
	}
	function Require(ok, operation) { if (!ok) throw operation + ": " + AIError.GetLastErrorString(); }
	function Start();
}

function AircraftCatalogue::Start()
{
	try {
		if (this.built) {
			if (this.release != null) {
				/* Ordinary full-load service lets the original rotor reach its stopped
				 * pose; release after reload lets the renderer observe its restart. */
				this.Sleep(AIController.GetSetting("review_hold_ticks"));
				foreach (vehicle in this.release) this.Require(AIOrder.SetOrderFlags(vehicle,0,AIOrder.OF_NONE), "release held destination service");
				this.release = null;
				AILog.Info("AIRCRAFT_CATALOGUE_HELD_SERVICE_RELEASED");
			}
			while (true) this.Sleep(1000);
		}
		AIController.SetCommandDelay(1);
		this.Require(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()), "fund aircraft catalogue company");
		AICompany.SetName("OpenTT3D Aircraft Review");
		local oilrig = AIController.GetSetting("review_oilrig") != 0;
		local type = oilrig ? AIAirport.AT_HELIDEPOT : AIAirport.AT_INTERCON, airports = [], aircraft = [];
		this.Require(AIAirport.IsValidAirportType(type), "review airport is available");
		local width = AIAirport.GetAirportWidth(type), height = AIAirport.GetAirportHeight(type);
		foreach (begin_x in [8, 88]) {
			if (oilrig && airports.len() == 1) break;
			local found = -1;
			for (local y = 8; y < AIMap.GetMapSizeY()-height-8 && found < 0; y += 10) {
				for (local x = begin_x; x < (oilrig ? AIMap.GetMapSizeX()-width-8 : begin_x+24); x += oilrig ? 4 : 10) {
					local tile = AIMap.GetTileIndex(x,y);
					if (AITile.GetMinHeight(tile) < (oilrig ? 1 : 2) || !AITile.IsBuildableRectangle(tile,width+1,height+1)) continue;
					if (!AITile.LevelTiles(tile,AIMap.GetTileIndex(x+width,y+height))) continue;
					if (AIAirport.BuildAirport(tile,type,AIStation.STATION_NEW)) { found = tile; break; }
				}
			}
			if (found < 0) throw "no buildable review airport site: " + begin_x;
			airports.append(found);
		}
		if (oilrig) {
			this.Require(AIIndustryType.CanBuildIndustry(5), "original oil rig can be funded");
			local site = -1;
			for (local y = 8; y < AIMap.GetMapSizeY()-16 && site < 0; y += 8) {
				for (local x = 8; x < AIMap.GetMapSizeX()-16; x += 8) {
					local tile = AIMap.GetTileIndex(x,y);
					if (AITile.IsWaterTile(tile) && AIIndustryType.BuildIndustry(5,tile)) { site = tile; break; }
				}
			}
			if (site < 0) throw "no fundable oil-rig water site";
			local station = -1;
			for (local tick = 0; tick < 4096 && station < 0; tick += 10) {
				for (local y = 0; y < 8 && station < 0; ++y) for (local x = 0; x < 8; ++x) {
					local tile = AIMap.GetTileIndex(AIMap.GetTileX(site)+x,AIMap.GetTileY(site)+y);
					local candidate = AIStation.GetStationID(tile);
					if (AIStation.IsValidStation(candidate) && AIStation.HasStationType(candidate,AIStation.STATION_AIRPORT)) { station = tile; break; }
				}
				if (station < 0) this.Sleep(10);
			}
			if (station < 0) throw "completed oil rig did not create its neutral airport";
			airports.append(station);
			AILog.Info("AIRCRAFT_CATALOGUE_OILRIG tile=" + station);
		}
		local available = AIEngineList(AIVehicle.VT_AIR);
		for (local engine = available.Begin(); !available.IsEnd(); engine = available.Next()) {
			if (engine < AIController.GetSetting("review_first") || engine > AIController.GetSetting("review_last")) continue;
			local vehicle = AIVehicle.BuildVehicle(AIAirport.GetHangarOfAirport(airports[0]),engine);
			this.Require(AIVehicle.IsValidVehicle(vehicle), "build original aircraft " + engine);
			/* Hold the first actual destination stop until the AI observes it. */
			this.Require(AIOrder.AppendOrder(vehicle,airports[1],AIOrder.OF_FULL_LOAD_ANY), "order destination airport");
			this.Require(AIOrder.AppendOrder(vehicle,airports[0],AIOrder.OF_NONE), "order origin airport");
			this.Require(AIVehicle.StartStopVehicle(vehicle), "start original aircraft");
			aircraft.append({engine = engine, vehicle = vehicle, serviced = false, peak_speed = 0});
		}
		if (aircraft.len() == 0) throw "no selected aircraft available in this climate";
		this.built = true;
		for (local tick = 0; tick < 36000; tick += 5) {
			local ready = 0;
			foreach (plane in aircraft) {
				local vehicle = plane.vehicle, speed = AIVehicle.GetCurrentSpeed(vehicle);
				if (AIVehicle.GetState(vehicle) == AIVehicle.VS_CRASHED) throw "review aircraft crashed: " + plane.engine;
				if (speed > plane.peak_speed) plane.peak_speed = speed;
				local at_destination = oilrig ? AIOrder.ResolveOrderPosition(vehicle,AIOrder.ORDER_CURRENT) == 0 &&
					AIMap.DistanceMax(AIVehicle.GetLocation(vehicle),airports[1]) <= 3 :
					AIStation.GetStationID(AIVehicle.GetLocation(vehicle)) == AIStation.GetStationID(airports[1]);
				if (!plane.serviced && AIVehicle.GetState(vehicle) == AIVehicle.VS_AT_STATION && at_destination) {
					plane.serviced = true;
					if (AIController.GetSetting("review_hold_ticks") == 0) this.Require(AIOrder.SetOrderFlags(vehicle,0,AIOrder.OF_NONE), "release observed airport service");
					AILog.Info("AIRCRAFT_CATALOGUE_SERVICE engine=" + plane.engine + " vehicle=" + vehicle);
				}
				if (plane.serviced && plane.peak_speed > 0 && !AIVehicle.IsInDepot(vehicle)) ++ready;
			}
			if (ready == aircraft.len()) {
				if (AIController.GetSetting("review_hold_ticks") > 0) {
					this.release = [];
					foreach (plane in aircraft) this.release.append(plane.vehicle);
				}
				local manifest = "";
				foreach (plane in aircraft) {
					manifest += (manifest.len() == 0 ? "" : ",") + "{\"engine\":" + plane.engine + ",\"vehicle\":" + plane.vehicle + ",\"serviced\":true,\"peak_speed\":" + plane.peak_speed + "}";
				}
				AILog.Info("AIRCRAFT_CATALOGUE_READY {\"airports\":[" + airports[0] + "," + airports[1] + "],\"aircraft\":[" + manifest + "]}");
				while (true) this.Sleep(1000);
			}
			this.Sleep(5);
		}
		throw "selected aircraft did not all reach actual destination service";
	} catch (error) {
		AILog.Error("AIRCRAFT_CATALOGUE_FAILED " + error);
		while (true) this.Sleep(1000);
	}
}
