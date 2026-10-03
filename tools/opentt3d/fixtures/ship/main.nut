/* SPDX-License-Identifier: GPL-2.0-only */
class ShipCatalogue extends AIController {
	built = false;
	x = 0;
	y = 0;
	function Save() { return {built=this.built}; }
	function Load(version,data) { if (data != null && "built" in data) this.built=data.built; }
	function Tile(dx,dy) { return AIMap.GetTileIndex(this.x+dx,this.y+dy); }
	function Require(ok,label) { if (!ok) throw label+": "+AIError.GetLastErrorString(); }
	function MaintainDepotStops();
	function Start();
}

function ShipCatalogue::MaintainDepotStops()
{
	local hold=AIController.GetSetting("depot_hold_ticks");
	if (hold==0) while (true) this.Sleep(1000);
	while (true) {
		local vehicles=AIVehicleList();
		for (local vehicle=vehicles.Begin(); !vehicles.IsEnd(); vehicle=vehicles.Next()) {
			if (AIVehicle.GetVehicleType(vehicle)!=AIVehicle.VT_WATER || !AIVehicle.IsStoppedInDepot(vehicle)) continue;
			AILog.Info("SHIP_DEPOT_STOPPED vehicle="+vehicle);
			this.Sleep(hold);
			if (AIVehicle.IsStoppedInDepot(vehicle)) this.Require(AIVehicle.StartStopVehicle(vehicle),"restart ship after ordinary depot stop");
			AILog.Info("SHIP_DEPOT_RESTARTED vehicle="+vehicle);
		}
		this.Sleep(1);
	}
}

function ShipCatalogue::Start()
{
	try {
		if (this.built) { this.MaintainDepotStops(); return; }
		AILog.Info("SHIP_CATALOGUE_STARTED");
		AIController.SetCommandDelay(1);
		this.Require(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"fund harbour company");
		AICompany.SetName("OpenTT3D Ship Review");
		local found=false, height=0;
		for (local y=24; y<AIMap.GetMapSizeY()-30 && !found; y+=8) {
			for (local x=24; x<AIMap.GetMapSizeX()-50; x+=8) {
				local tile=AIMap.GetTileIndex(x,y);
				if (AITile.GetMinHeight(tile)<2 || !AITile.IsBuildableRectangle(tile,44,18)) continue;
				AITile.LevelTiles(tile,AIMap.GetTileIndex(x+43,y+17));
				local flat=true, level=AITile.GetCornerHeight(tile,AITile.CORNER_N);
				for (local dy=0; dy<17 && flat; dy++) for (local dx=0; dx<43; dx++) {
					local sample=AIMap.GetTileIndex(x+dx,y+dy);
					if (AITile.GetSlope(sample)!=AITile.SLOPE_FLAT || AITile.GetMinHeight(sample)!=level) { flat=false; break; }
				}
				if (!flat || level<2) continue;
				this.x=x; this.y=y; height=level; found=true; break;
			}
		}
		if (!found) throw "no ordinary clear harbour site";
		AILog.Info("SHIP_CATALOGUE_SITE "+this.x+","+this.y+" height="+height);
		/* Lower the reference corner once, then use normal levelling to form
		 * a flat canal bed and the two genuine sloped dock banks. */
		this.Require(AITile.LowerTile(this.Tile(4,4),AITile.SLOPE_N),"lower harbour reference corner");
		this.Require(AITile.LevelTiles(this.Tile(4,4),this.Tile(38,12)),"level canal bed");
		local dike_island=AIController.GetSetting("dike_island")!=0 ? this.Tile(16,8) : -1;
		for (local dy=4; dy<12; dy++) for (local dx=4; dx<38; dx++) {
			local tile=this.Tile(dx,dy);
			this.Require(AITile.GetSlope(tile)==AITile.SLOPE_FLAT,"flat canal bed "+dx+","+dy);
			if (tile==dike_island) continue;
			this.Require(AIMarine.BuildCanal(tile),"build canal "+dx+","+dy);
		}
		if (dike_island>=0) this.Require(!AITile.IsWaterTile(dike_island),"original dry canal island remains land");
		local west=this.Tile(3,7), east=this.Tile(38,8), depot=this.Tile(20,7);
		AILog.Info("SHIP_CATALOGUE_BANKS west="+AITile.GetSlope(west)+" east="+AITile.GetSlope(east));
		this.Require(AIMarine.BuildDock(west,AIStation.STATION_NEW),"west dock");
		this.Require(AIMarine.BuildDock(east,AIStation.STATION_NEW),"east dock");
		local extra_docks=[];
		if (AIController.GetSetting("all_docks")!=0) {
			extra_docks=[this.Tile(12,3),this.Tile(28,12)];
			foreach (tile in extra_docks) this.Require(AIMarine.BuildDock(tile,AIStation.STATION_NEW),"additional original dock orientation");
		}
		local axis=AIController.GetSetting("depot_axis"), service=AIController.GetSetting("depot_service")!=0, hold=AIController.GetSetting("depot_hold_ticks");
		this.Require(AIMarine.BuildWaterDepot(depot,axis==0 ? this.Tile(21,7) : this.Tile(20,8)),"ship depot");
		local buoy=-1;
		if (AIController.GetSetting("buoy_waypoint")!=0) {
			buoy=this.Tile(14,9);
			this.Require(AIMarine.BuildBuoy(buoy),"build original navigation buoy");
		}
		local first=AIController.GetSetting("review_first"), last=AIController.GetSetting("review_last"), dock_hold=AIController.GetSetting("dock_hold")!=0;
		local engines=AIEngineList(AIVehicle.VT_WATER), fleet=[];
		for (local engine=engines.Begin(); !engines.IsEnd(); engine=engines.Next()) {
			if (engine<first || engine>last) continue;
			local vehicle=AIVehicle.BuildVehicle(depot,engine);
			this.Require(AIVehicle.IsValidVehicle(vehicle),"build ship "+engine);
			/* Hold each first call with an ordinary full-load order so a short
			 * empty-station visit cannot fall between observation ticks. */
			this.Require(AIOrder.AppendOrder(vehicle,west,AIOrder.OF_FULL_LOAD_ANY),"west dock order");
			this.Require(AIOrder.AppendOrder(vehicle,east,AIOrder.OF_FULL_LOAD_ANY),"east dock order");
			if (buoy>=0) this.Require(AIOrder.AppendOrder(vehicle,buoy,AIOrder.OF_NONE),"original buoy waypoint order");
			if (service) this.Require(AIOrder.AppendOrder(vehicle,depot,hold!=0 ? AIOrder.OF_STOP_IN_DEPOT : AIOrder.OF_NONE),"recurring depot-service order");
			this.Require(AIVehicle.StartStopVehicle(vehicle),"start ship "+engine);
			fleet.append({engine=engine,vehicle=vehicle,moved=false,peak=0,visits=0,buoy_order_seen=false,buoy_seen=false});
			AILog.Info("SHIP_CATALOGUE_VEHICLE engine="+engine+" vehicle="+vehicle);
		}
		if (fleet.len()==0) throw "no selected ships available in this climate";
		this.built=true;
		local ready=false;
		for (local tick=0; tick<16000 && !ready; tick+=2) {
			ready=true;
			foreach (entry in fleet) {
				this.Require(AIVehicle.IsValidVehicle(entry.vehicle),"ship remains valid");
				local speed=AIVehicle.GetCurrentSpeed(entry.vehicle), location=AIVehicle.GetLocation(entry.vehicle);
				if (speed>entry.peak) entry.peak=speed;
				if (speed>0 && AIMap.DistanceManhattan(location,depot)>=8) entry.moved=true;
				if (buoy>=0) {
					if (AIOrder.ResolveOrderPosition(entry.vehicle,AIOrder.ORDER_CURRENT)==2) entry.buoy_order_seen=true;
					if (entry.buoy_order_seen && location==buoy && speed>0) entry.buoy_seen=true;
				}
				local visits=entry.visits;
				if (AIVehicle.GetState(entry.vehicle)==AIVehicle.VS_AT_STATION) {
					if (AIMap.DistanceManhattan(location,west)<=4) entry.visits=entry.visits|1;
					if (AIMap.DistanceManhattan(location,east)<=4) entry.visits=entry.visits|2;
				}
				if (entry.visits!=visits) {
					if ((entry.visits&1)!=0 && (visits&1)==0) this.Require(AIOrder.SetOrderFlags(entry.vehicle,0,AIOrder.OF_NONE),"release observed west call");
					if ((entry.visits&2)!=0 && (visits&2)==0 && !dock_hold) this.Require(AIOrder.SetOrderFlags(entry.vehicle,1,AIOrder.OF_NONE),"release observed east call");
					AILog.Info("SHIP_CATALOGUE_DOCK engine="+entry.engine+" vehicle="+entry.vehicle+" visited="+entry.visits);
				}
				if (tick%512==0) AILog.Info("SHIP_CATALOGUE_PROGRESS engine="+entry.engine+" tile="+AIMap.GetTileX(location)+","+AIMap.GetTileY(location)+" speed="+speed+" state="+AIVehicle.GetState(entry.vehicle)+" order="+AIOrder.ResolveOrderPosition(entry.vehicle,AIOrder.ORDER_CURRENT)+" visited="+entry.visits);
				ready=ready && entry.moved && entry.visits==3 && (buoy<0 || entry.buoy_seen);
			}
			if (!ready) this.Sleep(2);
		}
		if (!ready) throw "not every ship moved and entered loading state at both docks";
		local extras=extra_docks.len()==0 ? "[]" : "["+extra_docks[0]+","+extra_docks[1]+"]";
		local result="{\"x\":"+this.x+",\"y\":"+this.y+",\"water_height\":"+(height-1)+",\"depot\":"+depot+",\"depot_axis\":"+axis+",\"depot_service\":"+(service ? "true" : "false")+",\"depot_hold_ticks\":"+hold+",\"dock_hold\":"+(dock_hold ? "true" : "false")+",\"buoy\":"+buoy+",\"dike_island\":"+dike_island+",\"docks\":["+west+","+east+"],\"extra_docks\":"+extras+",\"vehicles\":[";
		foreach (index,entry in fleet) {
			if (index!=0) result+=",";
			result+="{\"engine\":"+entry.engine+",\"vehicle\":"+entry.vehicle+",\"peak_speed\":"+entry.peak+",\"docks_visited\":"+entry.visits+",\"buoy_visited\":"+(entry.buoy_seen ? "true" : "false")+"}";
		}
		AILog.Info("SHIP_CATALOGUE_READY "+result+"]}");
		this.MaintainDepotStops();
	} catch (error) {
		AILog.Error("SHIP_CATALOGUE_FAILED "+error);
	}
	while (true) this.Sleep(1000);
}
