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
		local type = AIAirport.AT_INTERCON, airports = [], aircraft = [];
		this.Require(AIAirport.IsValidAirportType(type), "intercontinental airport is available");
		local width = AIAirport.GetAirportWidth(type), height = AIAirport.GetAirportHeight(type);
		foreach (begin_x in [8, 88]) {
			local found = -1;
			for (local y = 8; y < AIMap.GetMapSizeY()-height-8 && found < 0; y += 10) {
				for (local x = begin_x; x < begin_x+24; x += 10) {
					local tile = AIMap.GetTileIndex(x,y);
					if (AITile.GetMinHeight(tile) < 2 || !AITile.IsBuildableRectangle(tile,width+1,height+1)) continue;
					if (!AITile.LevelTiles(tile,AIMap.GetTileIndex(x+width,y+height))) continue;
					if (AIAirport.BuildAirport(tile,type,AIStation.STATION_NEW)) { found = tile; break; }
				}
			}
			if (found < 0) throw "no buildable review airport site: " + begin_x;
			airports.append(found);
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
				if (!plane.serviced && AIVehicle.GetState(vehicle) == AIVehicle.VS_AT_STATION &&
						AIStation.GetStationID(AIVehicle.GetLocation(vehicle)) == AIStation.GetStationID(airports[1])) {
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
