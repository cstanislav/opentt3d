/* SPDX-License-Identifier: GPL-2.0-only */
class ShipShort extends AIController {
	built = false;
	x = 0;
	y = 0;
	function Save() { return {built=this.built, x=this.x, y=this.y}; }
	function Load(version,data) { if (data != null) { if ("built" in data) this.built=data.built; if ("x" in data) this.x=data.x; if ("y" in data) this.y=data.y; } }
	function Tile(dx,dy) { return AIMap.GetTileIndex(this.x+dx,this.y+dy); }
	function Require(ok,label) { if (!ok) throw label+": "+AIError.GetLastErrorString(); }
	function Start();
}

function ShipShort::Start()
{
	if (this.built) { while (true) this.Sleep(1000); }
	try {
		AIController.SetCommandDelay(1);
		this.Require(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"fund short-bridge company");
		AICompany.SetName("OpenTT3D Short Bridge Review");
		local found=false, height=0;
		for (local y=24; y<AIMap.GetMapSizeY()-30 && !found; y+=8) {
			for (local x=24; x<AIMap.GetMapSizeX()-40; x+=8) {
				local tile=AIMap.GetTileIndex(x,y);
				if (AITile.GetMinHeight(tile)<2 || !AITile.IsBuildableRectangle(tile,30,20)) continue;
				AITile.LevelTiles(tile,AIMap.GetTileIndex(x+29,y+19));
				local level=AITile.GetCornerHeight(tile,AITile.CORNER_N), flat=true;
				for (local dy=0; dy<20 && flat; dy++) for (local dx=0; dx<30; dx++) {
					local sample=AIMap.GetTileIndex(x+dx,y+dy);
					if (AITile.GetSlope(sample)!=AITile.SLOPE_FLAT || AITile.GetMinHeight(sample)!=level) { flat=false; break; }
				}
				if (!flat || level<2) continue;
				this.x=x; this.y=y; height=level; found=true; break;
			}
		}
		if (!found) throw "no flat short-bridge plateau";
		AILog.Info("SHIP_SHORT_SITE "+this.x+","+this.y+" height="+height);
		local width=AIController.GetSetting("canal_width"), bridge_type=AIController.GetSetting("bridge_type");
		local bridge_start=this.Tile(14,7), bridge_end=this.Tile(14,8+width);
		AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);
		/* Build the short bridge on the initial flat plateau, then lower the
		 * narrow canal beneath its already-complete span. */
		this.Require(AIBridge.BuildBridge(AIVehicle.VT_ROAD,bridge_type,bridge_start,bridge_end),"build short vanilla road bridge");
		this.Require(AIBridge.IsBridgeTile(bridge_start),"short bridge head is a real bridge tile");
		for (local dx=4; dx<21; ++dx) for (local dy=8; dy<8+width; ++dy) {
			this.Require(AIMarine.BuildCanal(this.Tile(dx,dy)),"dig short canal "+dx+","+dy);
		}
		local west=this.Tile(3,8), east=this.Tile(21,8), depot=this.Tile(5,8), bridge_buoy=this.Tile(14,8);
		/* Docks need the ordinary inclined bank, not a flat quay. Use the
		 * same NE/SW bank orientations as the retained wide-harbour fixture. */
		this.Require(AITile.RaiseTile(west,AITile.SLOPE_NE),"slope short west dock bank");
		this.Require(AITile.RaiseTile(east,AITile.SLOPE_SW),"slope short east dock bank");
		AILog.Info("SHIP_SHORT_DOCK_SLOPES west="+AITile.GetSlope(west)+" east="+AITile.GetSlope(east));
		this.Require(AIMarine.BuildDock(west,AIStation.STATION_NEW),"short west dock");
		this.Require(AIMarine.BuildDock(east,AIStation.STATION_NEW),"short east dock");
		this.Require(AIMarine.BuildWaterDepot(depot,this.Tile(6,8)),"short ship depot");
		this.Require(AIMarine.BuildBuoy(bridge_buoy),"short under-bridge buoy");
		local engine=AIController.GetSetting("review_engine");
		local vehicle=AIVehicle.BuildVehicle(depot,engine);
		this.Require(AIVehicle.IsValidVehicle(vehicle),"build selected short-bridge ship");
		this.Require(AIOrder.AppendOrder(vehicle,west,AIOrder.OF_FULL_LOAD_ANY),"short west order");
		this.Require(AIOrder.AppendOrder(vehicle,east,AIOrder.OF_FULL_LOAD_ANY),"short east order");
		this.Require(AIOrder.AppendOrder(vehicle,bridge_buoy,AIOrder.OF_NONE),"short under-bridge waypoint");
		this.Require(AIVehicle.StartStopVehicle(vehicle),"start short-bridge ship");
		this.built=true;
		local visits=0, bridge_under=false, peak=0, moved=false;
		for (local tick=0; tick<16000; ++tick) {
			this.Require(AIVehicle.IsValidVehicle(vehicle),"short-bridge ship remains valid");
			local location=AIVehicle.GetLocation(vehicle), speed=AIVehicle.GetCurrentSpeed(vehicle);
			if (speed>peak) peak=speed;
			if (speed>0 && AIMap.DistanceManhattan(location,depot)>=6) moved=true;
			if (AIVehicle.GetState(vehicle)==AIVehicle.VS_AT_STATION) {
				local before=visits;
				if (AIMap.DistanceManhattan(location,west)<=4) visits=visits|1;
				if (AIMap.DistanceManhattan(location,east)<=4) visits=visits|2;
				if ((visits&1)!=(before&1)) this.Require(AIOrder.SetOrderFlags(vehicle,0,AIOrder.OF_NONE),"release short west call");
				if ((visits&2)!=(before&2)) this.Require(AIOrder.SetOrderFlags(vehicle,1,AIOrder.OF_NONE),"release short east call");
			}
			if (speed>0 && AIMap.GetTileX(location)==this.x+14 && AIMap.GetTileY(location)>=this.y+7 && AIMap.GetTileY(location)<=this.y+8+width) bridge_under=true;
			if (tick%512==0) AILog.Info("SHIP_SHORT_PROGRESS tick="+tick+" tile="+AIMap.GetTileX(location)+","+AIMap.GetTileY(location)+" speed="+speed+" visits="+visits+" bridge="+(bridge_under ? "true" : "false"));
			if (moved && visits==3 && bridge_under) break;
			this.Sleep(1);
		}
		if (!(moved && visits==3 && bridge_under)) throw "short-bridge ship did not visit both docks and pass under the span";
		local held=false;
		if (AIController.GetSetting("bridge_hold")!=0) {
			for (local tick=0; tick<4000 && !held; ++tick) {
				local location=AIVehicle.GetLocation(vehicle), speed=AIVehicle.GetCurrentSpeed(vehicle);
				if (speed>0 && AIMap.GetTileX(location)==this.x+14 && AIMap.GetTileY(location)>=this.y+7 && AIMap.GetTileY(location)<=this.y+8+width) {
					this.Require(AIVehicle.StartStopVehicle(vehicle),"stop short-bridge ship under span");
					held=true;
					AILog.Info("SHIP_SHORT_HELD tile="+AIMap.GetTileX(location)+","+AIMap.GetTileY(location));
					break;
				}
				this.Sleep(1);
			}
			if (!held) throw "short-bridge ship did not reach the span for hold";
		}
		local result="{\"x\":"+this.x+",\"y\":"+this.y+",\"height\":"+height+",\"canal_width\":"+width+",\"bridge_type\":"+bridge_type+",\"bridge_name\":\""+AIBridge.GetName(bridge_type,AIVehicle.VT_ROAD)+"\",\"engine\":"+engine+",\"vehicle\":"+vehicle+",\"peak_speed\":"+peak+",\"docks_visited\":"+visits+",\"bridge_under_span\":"+(bridge_under ? "true":"false")+",\"bridge_held\":"+(held ? "true":"false")+"}";
		AILog.Info("SHIP_SHORT_READY "+result);
	} catch (error) {
		AILog.Error("SHIP_SHORT_FAILED "+error);
	}
	while (true) this.Sleep(1000);
}
