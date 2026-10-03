/* Resume the retained costed freight service; add genuine passenger/mail service
 * on existing connected town roads through public NoAI construction and orders.
 * No score, HQ stage, calendar, terrain, industry production, funding or RNG edit. */
class TrainCatalogue extends AIController {
	built = false;
	grown = false;
	train = 0;
	town_service = false;
	function Save() { return {built=this.built,grown=this.grown,train=this.train,town_service=this.town_service}; }
	function Load(version,data) {
		if (data != null && "built" in data) this.built=data.built;
		if (data != null && "grown" in data) this.grown=data.grown;
		if (data != null && "train" in data) this.train=data.train;
		if (data != null && "town_service" in data) this.town_service=data.town_service;
	}
	function Require(ok,label) { if (!ok) throw label+": "+AIError.GetLastErrorString(); }
	function Start();
	function TownService();
}

function TrainCatalogue::TownService()
{
	AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);
	local step=AIMap.GetMapSizeX(), towns=AITownList();
	for (local town=towns.Begin(); !towns.IsEnd(); town=towns.Next()) {
		local centre=AITown.GetLocation(town), queue=[centre], seen={}, candidates=[], head=0;
		if (!AIRoad.IsRoadTile(centre)) continue;
		seen[centre] <- true;
		/* Walk only the existing, mutually connected public road component. */
		while (head<queue.len()) {
			local tile=queue[head++];
			if (!AIRoad.IsRoadStationTile(tile) && !AIRoad.IsRoadDepotTile(tile) &&
				AITile.GetSlope(tile)==AITile.SLOPE_FLAT && AIRoad.GetNeighbourRoadCount(tile)==2 &&
				AITile.GetCargoProduction(tile,0,1,1,3)>0 && AITile.GetCargoAcceptance(tile,0,1,1,3)>=8 &&
				AITile.GetCargoProduction(tile,2,1,1,3)>0 && AITile.GetCargoAcceptance(tile,2,1,1,3)>=8) {
				foreach (axis in [1,step]) {
					if (AIMap.IsValidTile(tile-axis) && AIMap.IsValidTile(tile+axis) &&
						AIRoad.AreRoadTilesConnected(tile,tile-axis) && AIRoad.AreRoadTilesConnected(tile,tile+axis))
						candidates.append({tile=tile,axis=axis});
				}
			}
			foreach (delta in [-1,1,-step,step]) {
				local next=tile+delta;
				if (!AIMap.IsValidTile(next) || next in seen || AIMap.DistanceManhattan(tile,next)!=1 ||
					AIMap.DistanceManhattan(centre,next)>24 || !AIRoad.AreRoadTilesConnected(tile,next)) continue;
				seen[next] <- true;queue.append(next);
			}
		}
		if (candidates.len()<4) continue;
		local first=null,second=null;
		foreach (a in candidates) {
			foreach (b in candidates) {
				if (AIMap.DistanceManhattan(a.tile,b.tile)<6) continue;
				local test=AITestMode();
				if (!AIRoad.BuildDriveThroughRoadStation(a.tile,a.tile+a.axis,AIRoad.ROADVEHTYPE_BUS,AIStation.STATION_NEW) ||
					!AIRoad.BuildDriveThroughRoadStation(b.tile,b.tile+b.axis,AIRoad.ROADVEHTYPE_BUS,AIStation.STATION_NEW)) continue;
				first=a;second=b;break;
			}
			if (first!=null) break;
		}
		if (first==null) continue;
		local depot=-1,front=-1;
		foreach (road in queue) {
			foreach (delta in [-1,1,-step,step]) {
				local tile=road+delta;
				if (!AIMap.IsValidTile(tile) || AIMap.DistanceManhattan(tile,road)!=1 ||
					!AITile.IsBuildable(tile) || AITile.GetSlope(tile)!=AITile.SLOPE_FLAT) continue;
				local test=AITestMode();
				if (!AIRoad.BuildRoadDepot(tile,road) || !AIRoad.BuildRoad(tile,road)) continue;
				depot=tile;front=road;break;
			}
			if (depot>=0) break;
		}
		if (depot<0) continue;
		this.Require(AIRoad.BuildRoadDepot(depot,front),"legal town road depot");
		this.Require(AIRoad.BuildRoad(depot,front),"normal depot connection");
		this.Require(AIRoad.BuildDriveThroughRoadStation(first.tile,first.tile+first.axis,AIRoad.ROADVEHTYPE_BUS,AIStation.STATION_NEW),"first passenger stop");
		this.Require(AIRoad.BuildDriveThroughRoadStation(second.tile,second.tile+second.axis,AIRoad.ROADVEHTYPE_BUS,AIStation.STATION_NEW),"second passenger stop");
		local stops=[first.tile,second.tile], mail=[];
		foreach (entry in [first,second]) {
			local station=AIStation.GetStationID(entry.tile), stop=-1;
			foreach (candidate in candidates) {
				if (AIMap.DistanceManhattan(candidate.tile,entry.tile)>3 || AIRoad.IsRoadStationTile(candidate.tile)) continue;
				if (AIRoad.BuildDriveThroughRoadStation(candidate.tile,candidate.tile+candidate.axis,AIRoad.ROADVEHTYPE_TRUCK,station)) {stop=candidate.tile;break;}
			}
			this.Require(stop>=0,"legal joined mail stop");mail.append(stop);
		}
		local engines=AIEngineList(AIVehicle.VT_ROAD);
		foreach (cargo in [0,2]) {
			local engine=-1,cost=0;
			for (local candidate=engines.Begin(); !engines.IsEnd(); candidate=engines.Next()) {
				if (!AIEngine.IsBuildable(candidate) || AIEngine.GetCargoType(candidate)!=cargo ||
					!AIEngine.CanRunOnRoad(candidate,AIRoad.ROADTYPE_ROAD)) continue;
				local running=AIEngine.GetRunningCost(candidate);
				if (engine<0 || running<cost) {engine=candidate;cost=running;}
			}
			this.Require(engine>=0,"original passenger/mail road engine");
			local vehicle=AIVehicle.BuildVehicle(depot,engine), route=cargo==0 ? stops : mail;
			this.Require(AIVehicle.IsValidVehicle(vehicle),"purchase normal town-service vehicle");
			foreach (stop in route) this.Require(AIOrder.AppendOrder(vehicle,stop,AIOrder.OF_NONE),"ordinary two-way town-service order");
			this.Require(AIVehicle.StartStopVehicle(vehicle),"start ordinary town service");
			AILog.Info("HQ_NATURAL_TOWN_SERVICE {\"town\":"+town+",\"cargo\":"+cargo+",\"vehicle\":"+vehicle+",\"engine\":"+engine+
				",\"running_cost\":"+cost+",\"first\":"+route[0]+",\"second\":"+route[1]+",\"existing_connected_roads\":true}");
		}
		this.town_service=true;return;
	}
	throw "no legal existing-road town-service site";
}

function TrainCatalogue::Start()
{
	try {
		this.Require(this.built && this.grown && AIVehicle.IsValidVehicle(this.train),"retained operating costed-service save");
		if (!this.town_service) this.TownService();
		local hq=AICompany.GetCompanyHQ(AICompany.COMPANY_SELF);
		this.Require(AIMap.IsValidTile(hq),"existing legal HQ");
		AILog.Info("HQ_NATURAL_READY {\"hq_x\":"+AIMap.GetTileX(hq)+",\"hq_y\":"+AIMap.GetTileY(hq)+"}");
		local previous=-1;
		while (true) {
			local date=AIDate.GetCurrentDate(), rating=AICompany.GetQuarterlyPerformanceRating(AICompany.COMPANY_SELF,1);
			if (date!=previous) {
				AILog.Info("HQ_NATURAL_ECONOMY {\"date\":"+date+",\"year\":"+AIDate.GetYear(date)+",\"month\":"+AIDate.GetMonth(date)+
					",\"rating\":"+rating+",\"income\":"+AICompany.GetQuarterlyIncome(AICompany.COMPANY_SELF,1)+
					",\"delivered\":"+AICompany.GetQuarterlyCargoDelivered(AICompany.COMPANY_SELF,1)+",\"cash\":"+AICompany.GetBankBalance(AICompany.COMPANY_SELF)+
					",\"loan\":"+AICompany.GetLoanAmount()+",\"profit_last_year\":"+AIVehicle.GetProfitLastYear(this.train)+"}");
				previous=date;
			}
			if (rating>=170) {
				AILog.Info("HQ_NATURAL_UPGRADE_READY {\"rating\":"+rating+",\"hq_x\":"+AIMap.GetTileX(hq)+",\"hq_y\":"+AIMap.GetTileY(hq)+"}");
				while (true) this.Sleep(1000);
			}
			this.Sleep(32);
		}
	} catch (error) {AILog.Error("HQ_NATURAL_FAILED "+error);}
	while (true) this.Sleep(1000);
}
